# Feature Flag & Experimentation Service

## Starter Repo Contents (what’s provided)

* FastAPI service skeleton with routers for auth/health/flags/segments/evaluate/audit
* In‑memory TTL cache and deterministic bucketing utility
* SQLite by default; optional Postgres via `DB_DSN`
* JSON logging, Prometheus `/metrics`
* Seed script with example tenant `acme` + flags/segments
* Minimal tests (health, property‑based bucketing)
* Makefile, Dockerfile, docker-compose, CI (GitHub Actions), requests.http, curl script
* Docs: full brief, scoring guide, reviewer checklist, ADR/risk/readout templates, API samples

## Objective & Duration
**Objective:** Build a **multi‑tenant Feature Flag & Experimentation Service** in Python that supports:

* CRUD for flags and segments
* Evaluate a flag for a (user, context) tuple
* Percentage rollouts and targeting rules (attributes/cohorts)
* Tenant isolation, JWT auth, audit log
* Fast in‑memory evaluation path and idempotent writes
* Health & readiness endpoints, JSON logs, and Prometheus metrics

**Duration:** 2 days (~12–16 focused hours). Stretch items are optional.

**What we’re assessing:** architecture, code quality, testing strategy, reliability/observability, security & tenancy, performance/data choices, and leadership/communication.


**Stretch (optional):**
- Dry-run “preview” evaluation for hypothetical users
- Change events stream with simple retry for subscribers
- A minimal Python client SDK

---

## Candidate Deliverables & Submission

**Submit a Git repository** (public link or zipped) containing the following. Use the checkboxes to self‑verify:

* [ ] **API correctness**: All must‑have endpoints in §2 implemented **per acceptance criteria**, with correct status codes and error handling. Pagination and filtering are documented. Soft‑delete behavior (if used) is documented.

* [ ] **Security & Tenancy**:

  * Enforce **`Authorization: Bearer <JWT>`** on all protected routes (everything except `/healthz`, `/readyz`, `/metrics`, `/v1/auth/token`).
  * Verify **HS256** signature and **`exp`**; reject missing/expired tokens. If you implement **scopes**, document required scopes per endpoint (e.g., `flags:r`, `flags:rw`).
  * Require **`X-Tenant-ID`** on all reads/writes. No cross‑tenant leakage. Include **at least one negative test** that proves tenant isolation.

* [ ] **Data model & storage**:

  * SQLAlchemy models for **flags**, **segments**, **audit**.
  * Provide **Alembic migrations** *or* a concise **SQL DDL** notes file. Include unique `(tenant_id, key)` on flags/segments and an index for audit `(tenant_id, ts)`.
  * Document trade‑offs and chosen persistence (SQLite acceptable; Postgres optional via `DB_DSN`).

* [ ] **Evaluation engine**:

  * Deterministic **bucketing** over `(tenant, flag_key, user_id)` in `[0,1)`.
  * Rule matching supports: **on/off**, **attribute equals**, **percentage rollout**. Segment membership is encouraged; if omitted, **state the limitation**.
  * Response includes `variant`, `reason`, optional `rule_id`, and `details.bucket`.

* [ ] **Observability**:

  * `/healthz` and `/readyz` (plain‑text responses).
  * `/metrics` with **Prometheus** exposition and at least `http_requests_total{path,method,status}`. Bonus: evaluation outcomes and cache hit/miss metrics.
  * **Structured JSON logs** including `timestamp`, `level`, `message`, `path`, `method`, `status`, `tenant`, and `request_id` (if provided).

* [ ] **Testing**:

  * Unit tests for **bucketing determinism**, **rule matching**, and **idempotent create**.
  * Integration test covering **flags/segments CRUD + evaluate** end‑to‑end.
  * At least **one e2e happy path** starting from a clean DB.
  * Include how to run tests (`pytest -q`). Optionally include coverage (aim for **≥ 75%** of domain/evaluation code).

---

## Performance & Caching

- Use an in-memory cache of **compiled rules** keyed by `(tenant, flag_key)`.
- Cache invalidation on flag/segment change (push or TTL).
- Deterministic percentage bucketing via a stable hash → [0.0, 1.0).
- Consider hot paths: evaluation should be **sub-millisecond** in-memory.

---

## Delivery & Communication

- 1–3 **ADRs** capturing the key choices (data store, cache invalidation, rules format).
- **Risk log** with top risks and mitigations.
- **Stakeholder readout** (one pager): problem, outcomes, risks, next steps.
- Open a self-PR and write review comments as if reviewing a peer’s work.

---

## Stretch Ideas

- `/v1/evaluate/preview` to test a hypothetical context
- Event stream: `/v1/events` (SSE or webhook retrier) for changes
- Minimal Python SDK (`flag_client.evaluate(flag_key, user)`)

---

## “Done” Criteria

- Must-have endpoints behave as specified
- Evaluation is deterministic, performant, and respects tenant scoping
- Meaningful tests pass in CI
- Clear documentation of trade-offs and next steps

---

## Must‑Have Endpoints & Acceptance Criteria

### Auth & Tenancy

* **`POST /v1/auth/token`** — Issues HS256 JWT with `sub`, `scopes`, `iat`, `exp` (≈6h). *Stub issuer acceptable.*

  * **200**: `{ "access_token": "...", "token_type": "bearer" }`.
* **Protected routes** require **`Authorization: Bearer <JWT>`** and **`X-Tenant-ID`**.

  * **401** if token missing/invalid/expired (include `WWW-Authenticate: Bearer`).
  * **403** if scopes insufficient (if you implement scopes like `flags:r`, `flags:rw`).

### Flags

* **`POST /v1/flags`** — **Idempotent upsert** by `(tenant, key)`.

  * **201** on first create; **200** on subsequent identical create or update.
  * **422** on invalid payload (e.g., weights < 0 or missing variants).
* **`GET /v1/flags`** — List flags for tenant.

  * Pagination: `limit` (1–100, default 50) and either `offset` or `page_token` (your choice; document it).
  * Filtering: support at least `state` and `q` (substring match on key/description) or document an alternative.
* **`GET /v1/flags/{key}`** — **404** if not found.
* **`PUT /v1/flags/{key}`** — Update description/state/variants/rules. **200** with updated entity.
* **`DELETE /v1/flags/{key}`** — Soft‑delete recommended (set `deleted_at`). **204**. Subsequent `GET` returns **404** by default.
* **Audit**: create/update/delete should record an entry with `before/after`.

### Segments

* Same semantics as Flags for create/list/get/update/delete.

  * `criteria` is JSON (e.g., `{ "attr": {"country": "CA"} }`), document your schema.

### Evaluation

* **`POST /v1/evaluate`** — Body: `{ "flag_key": "...", "user": { "id": "...", "attributes": { ... } } }`.

  * **Deterministic bucketing** in `[0,1)` using stable hash of `(tenant, flag_key, user_id)`.
  * Rule matching must support at minimum: **on/off gate**, **attribute equals**, and **percentage rollout**. Segment membership is encouraged; document if omitted.
  * **Response**: `{ "variant": "...", "reason": "rule_match|default_distribution|flag_off", "rule_id": "optional", "details": { "bucket": <float> } }`.
  * **404** if `flag_key` is unknown for the tenant.
  * Variants distribution: treat weights proportionally (need not sum to exactly 100; normalize).

### Audit & Ops

* **`GET /v1/audit`** — Query params: `entity` (`flag|segment`), `entity_key`, `actor`, `since`, `until`, `limit` (≤ 200). **200** returns newest‑first list with `before/after`.
* **`GET /healthz`**, **`GET /readyz`** — Plain‑text `ok` / `ready`.
* **`GET /metrics`** — Prometheus exposition. Provide at least request counter by `path, method, status`. Bonus: evaluation outcome metrics, cache hit/miss.

### Errors & Validation (baseline)

* **400**: missing `X-Tenant-ID` or malformed query params.
* **401/403**: auth failures as above.
* **404**: missing resources.
* **409**: only if you choose conflict semantics instead of upsert (document).
* **422**: body validation errors.

**Logging (minimum fields)**: `timestamp`, `level`, `message`, `path`, `method`, `status`, `tenant`, `request_id` (if provided).

---

## Stretch (Optional)

* `POST /v1/evaluate/preview` for hypothetical user/context with an explanation of which rule would match and why.
* Change event stream (SSE or webhook retrier) with simple backoff and delivery tracking.
* A tiny Python client SDK (evaluate + caching) with a short usage example and tests.
* Segment engine enhancements (segment caching + richer matchers) with clear docs.

## Data Model (suggested)

* **Flag**: id, tenant_id, key (unique per tenant), description, state (on/off), variants `[ {key, weight} ]`, rules `[ Rule ]`, timestamps
* **Rule**: id, order, when `{attr, segment, percentage}`, rollout `{variant | distribution}`
* **Segment**: id, tenant_id, key, criteria, timestamps
* **Audit**: id, tenant_id, actor, entity, entity_key, action, before, after, ts

Store rules/criteria as JSON to move faster. Index by `(tenant_id, key)`; audit by `(tenant_id, ts)`.

---

## Delivery & Communication

* 1–3 ADRs for key decisions (data store, cache invalidation, rules model)
* Risk log with top risks/mitigations
* One‑pager stakeholder readout (problem, outcomes, risks, next steps)
* Open a self‑PR and include your own review comments (what you’d ask a teammate)

