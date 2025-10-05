#!/usr/bin/env bash
set -euo pipefail

TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/token -H 'Content-Type: application/json' -d '{"client_id":"acme-svc","scopes":["flags:rw"]}' | jq -r .access_token)
echo "Token: $TOKEN"

curl -s -X POST http://localhost:8000/v1/flags -H "X-Tenant-ID: acme" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @- <<'JSON' | jq .
{
  "key": "exp_banner",
  "description": "Experimental banner",
  "state": "on",
  "variants": [{"key":"off","weight":50},{"key":"on","weight":50}],
  "rules": [{"id":"r1","order":1,"when":{"percentage":25},"rollout":{"distribution":[{"key":"off","weight":50},{"key":"on","weight":50}]}}]
}
JSON

curl -s -X POST http://localhost:8000/v1/evaluate -H "X-Tenant-ID: acme" -H "Content-Type: application/json" -d '{"flag_key":"exp_banner","user":{"id":"u-1","attributes":{"country":"CA"}}}' | jq .
