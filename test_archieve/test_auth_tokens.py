# tests/test_auth_tokens.py
import sys
import os

# Add the project root to Python path (so "app" can be imported)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.security import issue_token

client = TestClient(app)


def test_issue_and_verify_token():
    # Create and verify a test JWT token
    client_id = "ABC"
    scopes = ["read", "write"]
    token = issue_token(client_id, scopes)

    from app.utils.security import verify_token
    payload = verify_token(token)

    assert payload["sub"] == client_id
    assert payload["scopes"] == scopes


def test_access_protected_route_without_token():
    # Missing Authorization header but valid tenant should fail with 401
    headers = {"X-Tenant-ID": "ABC"}  # Add tenant to avoid 422
    response = client.get("/v1/flags", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header"


def test_access_protected_route_with_token():
    # Valid token and tenant should allow access (200 or 204)
    client_id = "ABC"
    scopes = ["read"]
    token = issue_token(client_id, scopes)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "ABC",  # replace with valid tenant in DB if needed
    }

    response = client.get("/v1/flags", headers=headers)

    assert response.status_code in (200, 204)


def test_access_with_invalid_tenant():
    # Invalid tenant should fail with 403
    client_id = "ABC"
    scopes = ["read"]
    token = issue_token(client_id, scopes)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": "INVALID",
    }

    response = client.get("/v1/flags", headers=headers)

    assert response.status_code == 403
    # Match the updated dynamic validation message
    assert "not recognized" in response.json()["detail"]