# tests/test_flag_eval.py
import pytest
from app.services.flag_eval import stable_bucket, evaluate_flag

# --- Helper Fixtures --------------------------------------------------------


@pytest.fixture
def base_flag():
    return {
        "key": "checkout_new",
        "state": "on",
        "variants": [
            {"key": "control", "weight": 50},
            {"key": "treatment", "weight": 50},
        ],
        "rules": [],
    }


@pytest.fixture
def sample_user():
    return {"id": "user123", "country": "CA", "role": "employee"}


@pytest.fixture
def sample_segments():
    return [
        {
            "id": "seg1",
            "rules": [{"attributes": {"country": "CA"}}],
        },
        {
            "id": "seg2",
            "rules": [{"attributes": {"country": "US"}}],
        },
    ]


# --- Tests ------------------------------------------------------------------


def test_flag_off(base_flag, sample_user):
    base_flag["state"] = "off"
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["reason"] == "flag_off"
    assert result["variant"] is None


def test_attribute_match_rule(base_flag, sample_user):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"attr": {"role": "employee"}},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["variant"] == "beta"
    assert result["reason"] == "rule_match"
    assert result["rule_id"] == "r1"


def test_attribute_mismatch_rule(base_flag, sample_user):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"attr": {"role": "manager"}},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["reason"] == "default_variant"
    assert result["variant"] in ["control", "treatment"]


def test_segment_match_rule(base_flag, sample_user, sample_segments):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"segment": ["seg1"]},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user, segments=sample_segments)
    assert result["variant"] == "beta"
    assert result["reason"] == "rule_match"


def test_segment_mismatch_rule(base_flag, sample_user, sample_segments):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"segment": ["seg2"]},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user, segments=sample_segments)
    assert result["reason"] == "default_variant"


def test_percentage_rollout_allows(base_flag, sample_user):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"attr": {"role": "employee"}},
            "rollout": {"percentage": 100},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["variant"] == "beta"


def test_percentage_rollout_blocks(base_flag, sample_user):
    base_flag["rules"] = [
        {
            "id": "r1",
            "when": {"attr": {"role": "employee"}},
            "rollout": {"percentage": 0},
            "variants": [{"key": "beta", "weight": 100}],
        }
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["reason"] == "default_variant"


def test_weighted_variant_distribution(base_flag, sample_user):
    # Force 80/20 split
    base_flag["variants"] = [
        {"key": "control", "weight": 80},
        {"key": "treatment", "weight": 20},
    ]
    result = evaluate_flag(base_flag, "tenantA", sample_user)
    assert result["variant"] in ["control", "treatment"]
    assert result["reason"] == "default_variant"


def test_stable_bucket_determinism():
    b1 = stable_bucket("tenantA", "checkout_new", "user123")
    b2 = stable_bucket("tenantA", "checkout_new", "user123")
    assert b1 == pytest.approx(b2)
    assert 0 <= b1 < 1
