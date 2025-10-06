# flag_eval.py

import hashlib
from typing import Any, Dict, List, Optional


def stable_bucket(tenant: str, flag_key: str, user_id: str) -> float:
    """
    Create a stable, deterministic bucket value in [0,1)
    using SHA-256 hash of (tenant, flag_key, user_id).
    Used for percentage-based rollouts.
    """
    h = hashlib.sha256(f"{tenant}:{flag_key}:{user_id}".encode()).hexdigest()
    n = int(h[:15], 16)
    return (n % 10_000_000) / 10_000_000.0


def normalize_weights(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize variant weights so they always sum to 1.0
    even if input weights don't add up to 100.
    """
    total = sum(v.get("weight", 0) for v in variants)
    if total <= 0:
        return [{"key": "control", "weight": 1.0}]
    return [{"key": v["key"], "weight": v["weight"] / total} for v in variants]


def evaluate_flag(
    flag: dict, tenant: str, user: dict, segments: Optional[List[dict]] = None
) -> dict:
    """
    Evaluate a feature flag for a given user.
    
    Returns a dict with:
        - variant: selected variant key (or None if flag is off)
        - reason: why variant was selected
        - rule_id: optional, rule that matched
        - details.bucket: bucket value used for rollout
    """
    user_id = user.get("id") or "anonymous"
    bucket = stable_bucket(tenant, flag["key"], user_id)

    # Flag off → variant is None
    if flag.get("state") == "off":
        return {"variant": None, "reason": "flag_off", "details": {"bucket": bucket}}

    # Iterate over rules
    for rule in flag.get("rules", []):
        when = rule.get("when", {})
        rollout = rule.get("rollout", {})

        # Attribute matching
        attr_conditions = when.get("attr", {})
        if attr_conditions:
            if not all(user.get(k) == v for k, v in attr_conditions.items()):
                continue  # Skip if attributes don't match

        # Segment matching
        segment_ids = when.get("segment", [])
        if segment_ids:
            if segments is None:
                # Limitation: segments not provided
                continue
            user_segment_ids = [
                s["id"] for s in segments
                if all(user.get(k) == v for k, v in s.get("rules", [{}])[0].get("attributes", {}).items())
            ]
            if not any(seg_id in user_segment_ids for seg_id in segment_ids):
                continue  # Skip if no segments match

        # Percentage rollout
        percentage = rollout.get("percentage")
        if percentage is not None and bucket * 100 >= percentage:
            continue  # User not included in rollout

        # Variant selection via distribution
        distribution = normalize_weights(rollout.get("distribution", rule.get("variants", [])))
        cumulative = 0.0
        for variant in distribution:
            cumulative += variant["weight"]
            if bucket <= cumulative:
                return {
                    "variant": variant["key"],
                    "reason": "rule_match",
                    "rule_id": rule.get("id"),
                    "details": {"bucket": bucket},
                }

    # Default variant if no rule matched
    default_distribution = normalize_weights(flag.get("variants", []))
    cumulative = 0.0
    for variant in default_distribution:
        cumulative += variant["weight"]
        if bucket <= cumulative:
            return {
                "variant": variant["key"],
                "reason": "default_variant",
                "details": {"bucket": bucket},
            }

    # Fallback
    return {"variant": "control", "reason": "fallback", "details": {"bucket": bucket}}
