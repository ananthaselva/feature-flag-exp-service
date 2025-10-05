# Feature Flag & Experimentation Service — Take-Home (L7 Technical Manager)

Welcome! This is the starter kit for a 2-day take-home assignment aimed at a Level 7 Technical Manager. You’ll design and implement a **multi-tenant feature-flag & experimentation service** in Python.

You are expected to demonstrate **architecture & design**, **implementation excellence**, **testing strategy**, **reliability/observability**, **security & multi-tenancy**, **performance/data acumen**, and **delivery leadership & communication**.

> Timebox: ~2 working days. Must-haves are designed to be achievable within 12–16 hours. Stretch goals are optional.

---

## Quick Start

```bash
# a) Install Python version 3.11
brew install python@3.11
# 1) Local (no Docker) — requires Python 3.11+
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip wheel
pip install -r requirements.txt -r requirements-dev.txt
make run      # starts the API on http://localhost:8000
make seed     # loads sample data
open http://localhost:8000/docs

# 2) Docker (optional, includes Postgres)
docker compose up --build
# app: http://localhost:8000, pg: localhost:5432 (user=postgres, pass=postgres)
```

**Health:** `GET /healthz` and `GET /readyz`  
**Metrics:** `GET /metrics` (Prometheus format)  
**OpenAPI:** `GET /openapi.json` and Swagger at `/docs`

---

## The Assignment (high level)

You’ll build a service that lets tenants manage flags and segments, and **evaluate a flag** for a specific (user, context) with rules and percentage rollouts. Provide JWT/token auth, tenant isolation, auditing of changes, and a fast in-memory evaluation path with caching.

See the full brief in `docs/brief.md`.
See a use case example in `USECASE.md`.

---

## Candidate Deliverables Checklist

Use this list to self-verify your submission before sending it.

## API Correctness
- [ ] All **must-have endpoints** implemented per acceptance criteria (§2)
- [ ] Correct status codes & error handling (400/401/403/404/409/422 as applicable)
- [ ] Pagination documented for list endpoints (limit + offset or page_token)
- [ ] Filtering documented (e.g., `state`, `q`)
- [ ] Soft-delete behavior (if used) documented

## Security & Tenancy
- [ ] Protected routes require **Authorization: Bearer <JWT>**
- [ ] JWT (HS256) signature verified; **`exp`** enforced; invalid/missing → **401**
- [ ] (If implemented) **scopes** enforced per endpoint; insufficient → **403**
- [ ] **X-Tenant-ID** required on all reads/writes
- [ ] No cross-tenant leakage (include **≥1 negative test** proving isolation)

## Data Model & Storage
- [ ] SQLAlchemy models for **flags**, **segments**, **audit**
- [ ] Unique index: **(tenant_id, key)** on flags & segments
- [ ] Audit index: **(tenant_id, ts)**
- [ ] Alembic migrations **or** concise SQL DDL notes included
- [ ] Persistence choice & trade-offs documented (SQLite OK; Postgres optional via `DB_DSN`)

## Evaluation Engine
- [ ] Deterministic **bucketing** in `[0,1)` over `(tenant, flag_key, user_id)`
- [ ] Rule matching supports: **on/off**, **attribute equals**, **percentage rollout**
- [ ] (Encouraged) Segment membership; if omitted, **document limitation**
- [ ] Response includes: `variant`, `reason`, optional `rule_id`, `details.bucket`
- [ ] Weights normalized for variant distribution (need not sum to 100 in input)

## Observability & Reliability
- [ ] `/healthz` and `/readyz` present (plain-text)
- [ ] `/metrics` exposes Prometheus metrics (at least request counter by `path,method,status`)
- [ ] **Structured JSON logs** with: `timestamp`, `level`, `message`, `path`, `method`, `status`, `tenant`, `request_id` (if provided)

## Testing
- [ ] Unit tests: **bucketing determinism**, **rule matching**, **idempotent create**
- [ ] Integration test: **flags/segments CRUD + evaluate** happy path
- [ ] At least one **end-to-end** test from clean DB
- [ ] Clear test run instructions (`pytest -q`); (optional) coverage with goal **≥ 75%** for domain/eval code

## CI & DevEx
- [ ] GitHub Actions (or equivalent) running **ruff**, **mypy**, **pytest** on push/PR
- [ ] **Makefile** with `run`, `seed`, `test`, `ci` (Docker/compose optional but welcome)
- [ ] One-command local setup works (document any environment variables)

## Documentation
- [ ] `README.md` or `/docs/` with local setup, run steps, design overview
- [ ] Example requests (`requests.http` or `curl` script)
- [ ] **“What I built / what I cut / what I’d do next”** section
- [ ] **ADRs (1–3)** for key choices, **risk log**, **stakeholder readout** one-pager
- [ ] If no hosted PR, include a brief **CHANGELOG** summarizing notable changes

---

### Optional Stretch (counts as “exceeds”)
- [ ] `POST /v1/evaluate/preview` with rule-match explanation
- [ ] Change events stream (SSE or webhook retrier w/ backoff & delivery tracking)
- [ ] Minimal Python client SDK (evaluate + caching) with usage example & tests
- [ ] Segment engine enhancements (segment caching + richer matchers) documented

---

## Repo Layout

```
app/
  main.py
  config.py
  deps.py
  models.py
  schemas.py
  utils/
    logging.py
    security.py
  services/
    cache.py
    flag_eval.py
    audit.py
  routers/
    health.py
    auth.py
    flags.py
    segments.py
    evaluate.py
    audit.py
docs/
  brief.md
  scoring-guide.md
  reviewer-checklist.md
  adr/0000-template.md
  stakeholder-readout-template.md
  risks-template.md
  api-sample.md
scripts/
  seed.py
  curl-examples.sh
tests/
  conftest.py
  test_health.py
  test_bucket_deterministic.py
Dockerfile
docker-compose.yml
Makefile
requirements.txt
requirements-dev.txt
.github/workflows/ci.yml
requests.http
```

---

## Notes

- Starter implements only scaffolding + a minimal evaluation path to let you run smoke tests. You’ll complete the core logic to satisfy the brief.
- You can stay on SQLite (default) or switch to Postgres via `DB_DSN` env.
- Use `X-Tenant-ID` header for tenant scoping. Protected endpoints require `Authorization: Bearer <JWT>`.
- Seed data includes a tenant `acme` and example flags/segments to test evaluation.

Good luck & have fun!
