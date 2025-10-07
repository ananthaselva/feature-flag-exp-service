# ADR-001: Data Store Choice
Status: Accepted
Date: 2025-10-06

**Context**: Feature flag service requires persistent storage for flags, rules, and audit logs.  
**Decision**: Use SQLite for local development and PostgreSQL for production with SQLAlchemy Async ORM.  
**Why**: Async support is needed for scalable operations; SQLite allows easy local dev setup.  
**Impact**: `app/models.py`, `app/config.py`, Alembic migrations, DB connections in tests.  
**Risks/Mitigations**:
- DB mismatch between dev and prod → test Postgres locally with Docker and migrations.
- SQLite concurrency limits → only use for local dev/testing.  
**Follow-ups**: Dev team → 2025-11-01

# ADR-002: Cache Invalidation Strategy
Status: Accepted
Date: 2025-10-06

**Context**: Feature evaluation needs to be fast while maintaining consistency with DB state.  
**Decision**: Use in-memory per-tenant cache with explicit invalidation on flag create/update/delete.  
**Why**: Reduces DB hits and improves performance for feature evaluation.  
**Impact**: `app/services/cache.py`, CRUD endpoints in `app/routers/flags.py`, tests.  
**Risks/Mitigations**:
- Multi-instance cache inconsistency → plan migration to Redis or Memcached.
- Cache not cleared → ensure invalidation called in all CRUD paths.  
**Follow-ups**: Dev team → 2025-12-01

# ADR-003: Rules Model
Status: Accepted
Date: 2025-10-06

**Context**: Feature flags have dynamic rules with nested rollouts and variant distributions.  
**Decision**: Store rules as JSON in DB and serialize/deserialize via Pydantic models.  
**Why**: Flexible schema without altering DB tables for every rule change; type validation via Pydantic.  
**Impact**: `app/schemas.py`, `app/models.py`, `app/routers/flags.py`, unit tests.  
**Risks/Mitigations**:
- Harder to query specific rule attributes → add query helpers or move to JSONB in Postgres.
- Serialization/deserialization errors → validate with Pydantic and test coverage.  
**Follow-ups**: Dev team → 2025-11-15
