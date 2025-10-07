# tests/test_unit_flags.py
import pytest
import copy
from fastapi.encoders import jsonable_encoder
from app.services.flag_eval import stable_bucket, evaluate_flag

# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def sample_flag():
    return copy.deepcopy({
        "key": "checkout_flow",
        "description": "New checkout flow",
        "state": "on",
        "variants": [
            {"key": "control", "weight": 50},
            {"key": "treatment", "weight": 50},
        ],
        "rules": []
    })

@pytest.fixture
def sample_user():
    return copy.deepcopy({"id": "user123", "role": "employee", "country": "CA"})

@pytest.fixture
def sample_segments():
    return copy.deepcopy([
        {"id": "seg1", "rules": [{"attributes": {"country": "CA"}}]},
        {"id": "seg2", "rules": [{"attributes": {"country": "US"}}]},
    ])

# -----------------------------
# Unit tests: flag evaluation
# -----------------------------

def test_flag_disabled(sample_flag, sample_user):
    sample_flag["state"] = "off"
    result = evaluate_flag(sample_flag, "tenantA", sample_user)
    assert result["reason"] == "flag_off"

def test_rule_match_by_attribute(sample_flag, sample_user):
    sample_flag["rules"] = [
        {"id": "r1", "when": {"attr": {"role": "employee"}}, "variants": [{"key": "beta", "weight": 100}]}
    ]
    result = evaluate_flag(sample_flag, "tenantA", sample_user)
    assert result["variant"] == "beta"
    assert result["reason"] == "rule_match"

def test_rule_mismatch_falls_back_to_default(sample_flag, sample_user):
    sample_flag["rules"] = [
        {"id": "r1", "when": {"attr": {"role": "manager"}}, "variants": [{"key": "beta", "weight": 100}]}
    ]
    result = evaluate_flag(sample_flag, "tenantA", sample_user)
    assert result["reason"] == "default_variant"
    assert result["variant"] in ["control", "treatment"]

def test_segment_rule_match(sample_flag, sample_user, sample_segments):
    sample_flag["rules"] = [
        {"id": "r1", "when": {"segment": ["seg1"]}, "variants": [{"key": "beta", "weight": 100}]}
    ]
    result = evaluate_flag(sample_flag, "tenantA", sample_user, segments=sample_segments)
    assert result["variant"] == "beta"
    assert result["reason"] == "rule_match"

def test_segment_rule_no_match(sample_flag, sample_user, sample_segments):
    sample_flag["rules"] = [
        {"id": "r1", "when": {"segment": ["seg2"]}, "variants": [{"key": "beta", "weight": 100}]}
    ]
    result = evaluate_flag(sample_flag, "tenantA", sample_user, segments=sample_segments)
    assert result["reason"] == "default_variant"
    assert result["variant"] in ["control", "treatment"]

def test_stable_bucket_is_deterministic():
    b1 = stable_bucket("tenantA", "checkout_flow", "user123")
    b2 = stable_bucket("tenantA", "checkout_flow", "user123")
    assert b1 == pytest.approx(b2)
    assert 0 <= b1 < 1

# -----------------------------
# Integration test: idempotent create
# -----------------------------

@pytest.mark.asyncio
async def test_idempotent_create_flag(authorized_client):
    flag_payload = {
        "key": "checkout_flow",
        "description": "New checkout flow",
        "state": "on",
        "variants": [
            {"key": "control", "weight": 50},
            {"key": "treatment", "weight": 50}
        ],
        "rules": [
            {
                "id": "r1",
                "order": 1,
                "when": {"percentage": 50},
                "rollout": {
                    "distribution": [
                        {"key": "control", "weight": 50},
                        {"key": "treatment", "weight": 50}
                    ]
                }
            }
        ]
    }

    # First create: should return 201
    resp1 = await authorized_client.post("/v1/flags", json=jsonable_encoder(flag_payload))
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["key"] == flag_payload["key"]

    # Second create with same key: should return 200
    resp2 = await authorized_client.post("/v1/flags", json=jsonable_encoder(flag_payload))
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data1["key"] == data2["key"]
    assert data1["id"] == data2["id"]
