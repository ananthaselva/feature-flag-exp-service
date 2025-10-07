# Risk Log - Feature Flag Service

| ID  | Risk Description                                       | Likelihood | Impact | Mitigation / Action Plan                                | Owner       | Status      |
| --- | ------------------------------------------------------ | ---------- | ------ | ------------------------------------------------------ | ----------- | ----------- |
| R001 | DB schema mismatch between local dev and production   | Medium     | High   | Test locally using Postgres; apply Alembic migrations | Dev Team    | Open        |
| R002 | Cache inconsistency across multiple service instances | Medium     | High   | Invalidate cache on all CRUD; plan migration to Redis | Dev Team    | Open        |
| R003 | Serialization/Deserialization errors for rules JSON   | Low        | Medium | Validate with Pydantic models; add unit tests         | Dev Team    | Open        |
| R004 | JWT token misuse / expired tokens                     | Low        | High   | Implement token expiry, rotation, and validation      | Security    | Open        |
| R005 | Feature evaluation slow under high traffic            | Medium     | Medium | Use in-memory caching; performance test under load    | Dev Team    | Open        |
| R006 | Unauthorized access to tenant-specific flags          | Low        | High   | Enforce tenant isolation in DB queries; audit logs    | Dev Team    | Open        |
