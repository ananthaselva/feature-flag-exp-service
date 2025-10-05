from fastapi.testclient import TestClient
from app.main import app
from app.schemas import FlagIn
from app.utils.security import issue_token

client = TestClient(app)

# Example payload
payload = {
    "key": "testfeature1",
    "description": "string",
    "state": "on",
    "variants": [{"key": "string", "weight": 100}],
    "rules": []
}

# Generate token for authentication
client_id = "ABC"
scopes = ["write"]
token = issue_token(client_id, scopes)

# Tenant header
TENANT_ID = "ABC"
headers = {
    "Authorization": f"Bearer {token}",
    "X-Tenant-ID": TENANT_ID
}

# Send POST request to create flag
response = client.post("/v1/flags", json=payload, headers=headers)

print("Status Code:", response.status_code)
print("Response Body:", response.json())
