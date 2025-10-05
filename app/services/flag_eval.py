import hashlib
from typing import Any, Dict


def stable_bucket(tenant: str, flag_key: str, user_id: str) -> float:
    h = hashlib.sha256(f"{tenant}:{flag_key}:{user_id}".encode()).hexdigest()
    n = int(h[:15], 16)
    return (n % 10_000_000) / 10_000_000.0


def evaluate_flag(flag: dict, tenant: str, user: dict) -> dict:
    # TODO:
    # - respect flag on/off
    # - attribute & segment rule matching
    # - percentage rollout via stable_bucket
    # - default variant distribution
    return {"variant": "control", "reason": "not_implemented"}
