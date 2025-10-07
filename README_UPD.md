# Feature Flag Service

## Local Setup
1. Clone the repository:

git clone <repo-url>
cd feature-flag-service

#2. Create a virtual environment and activate it:

python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# or
source .venv/bin/activate      # Linux / macOS

#3. Install dependencies:

pip install -r requirements.txt
pip install -r requirements-dev.txt


#4. Configure environment variables: (.env)

#Example:

DB_DSN=sqlite+aiosqlite:///./dev.db
JWT_SECRET=dev-secret
LOG_LEVEL=INFO

#5. Running the App

uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

#6. Running Tests

pytest tests -v --disable-warnings --cov=app --cov-report=term

#Exmaple Requests: 

Refer requests_updated.http

## Local Setup - scripts
we can also use tasks.ps1

# Run FastAPI
.\tasks.ps1 -task run

# Seed database
.\tasks.ps1 -task seed

# Run tests
.\tasks.ps1 -task test

# Run CI tasks locally
.\tasks.ps1 -task ci



#What I Built / What I Cut / Next Steps

Built: Async FastAPI service with feature flags, CRUD, caching, auditing, auth, metrics dashboards, basic CI/CD improvements
Cut: Full frontend, complex rollout strategies
Next: Multi-tenant support, CI/CD improvements

#SQL DDL:

-- Flags table
CREATE TABLE flags (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    key VARCHAR(128) NOT NULL,
    description TEXT,
    state VARCHAR(8) NOT NULL DEFAULT 'off',
    variants JSON NOT NULL,
    rules JSON NOT NULL,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, key)
);

CREATE INDEX ix_flags_tenant_state ON flags(tenant_id, state);

-- Segments table
CREATE TABLE segments (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    key VARCHAR(128) NOT NULL,
    criteria JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, key)
);

CREATE INDEX ix_segments_tenant ON segments(tenant_id);

-- Audit table
CREATE TABLE audit (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    entity VARCHAR(32) NOT NULL,
    entity_key VARCHAR(128) NOT NULL,
    action VARCHAR(32) NOT NULL,
    before JSON,
    after JSON,
    ts TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_audit_tenant_ts ON audit(tenant_id, ts);


#Alembic migrations:

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_create_flags_segments_audit'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------
    # Flags table
    # -------------------------
    op.create_table(
        'flags',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, comment="Surrogate numeric identifier"),
        sa.Column('tenant_id', sa.String(64), nullable=False, comment="Tenant namespace identifier; all reads/writes scoped by this"),
        sa.Column('key', sa.String(128), nullable=False, comment="Flag key, unique per tenant"),
        sa.Column('description', sa.Text, nullable=True, comment="Human-readable description"),
        sa.Column('state', sa.String(8), nullable=False, server_default='off', comment="'on' or 'off'; gates rule evaluation"),
        sa.Column('variants', sa.JSON, nullable=False, comment="List of {key, weight}"),
        sa.Column('rules', sa.JSON, nullable=False, comment="Ordered rules"),
        sa.Column('deleted_at', sa.DateTime, nullable=True, index=True, comment="Soft-delete marker"),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now(), comment="Creation time (UTC)"),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), comment="Last update time (UTC)"),
        sa.UniqueConstraint('tenant_id', 'key', name='uq_flags_tenant_key'),
        sa.Index('ix_flags_tenant_state', 'tenant_id', 'state'),
        sa.CheckConstraint("state IN ('on','off')", name='ck_flags_state')
    )

    # -------------------------
    # Segments table
    # -------------------------
    op.create_table(
        'segments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, comment="Surrogate numeric identifier"),
        sa.Column('tenant_id', sa.String(64), nullable=False, comment="Tenant namespace identifier"),
        sa.Column('key', sa.String(128), nullable=False, comment="Segment key, unique per tenant"),
        sa.Column('criteria', sa.JSON, nullable=False, comment="Matcher tree"),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now(), comment="Creation time (UTC)"),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), comment="Last update time (UTC)"),
        sa.UniqueConstraint('tenant_id', 'key', name='uq_segments_tenant_key'),
        sa.Index('ix_segments_tenant', 'tenant_id')
    )

    # -------------------------
    # Audit table
    # -------------------------
    op.create_table(
        'audit',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True, comment="Surrogate numeric identifier"),
        sa.Column('tenant_id', sa.String(64), nullable=False, comment="Tenant namespace identifier"),
        sa.Column('actor', sa.String(128), nullable=False, comment="Who performed the change"),
        sa.Column('entity', sa.String(32), nullable=False, comment="Entity type: 'flag' or 'segment'"),
        sa.Column('entity_key', sa.String(128), nullable=False, comment="Stable key of the entity"),
        sa.Column('action', sa.String(32), nullable=False, comment="Action verb: 'create' | 'update' | 'delete'"),
        sa.Column('before', sa.JSON, nullable=True, comment="Selected fields before change"),
        sa.Column('after', sa.JSON, nullable=True, comment="Selected fields after change"),
        sa.Column('ts', sa.DateTime, nullable=False, server_default=sa.func.now(), comment="Event timestamp (UTC)"),
        sa.Index('ix_audit_tenant_ts', 'tenant_id', 'ts')
    )


def downgrade() -> None:
    op.drop_table('audit')
    op.drop_table('segments')
    op.drop_table('flags')


#Persistence Choice & Trade-offs

For this feature flag service, SQLite is currently used as the database. This choice was made primarily for development and testing purposes, as SQLite is lightweight, file-based, requires no additional setup, and allows for rapid prototyping. It enables developers to get the system running locally quickly, with minimal operational overhead.
However, for a production-grade deployment, PostgreSQL is recommended. PostgreSQL provides:
	• ACID compliance for strong consistency, ensuring that flag creation, updates, and deletions are reliably stored across concurrent operations.
	• Better support for multi-tenant isolation, with robust indexing and unique constraints (e.g., (tenant_id, key) for flags and segments).
	• Scalability and reliability, including replication, backups, and concurrency handling.
	• Advanced features like JSON support, complex queries, and audit indexing, which are essential for a growing multi-tenant system.
Trade-offs:
Aspect	SQLite	PostgreSQL
Setup	Minimal	Requires DB service
Concurrency	Single-writer	Handles many concurrent writes
Multi-tenant Isolation	Simple but limited	Full support via indexes & constraints
Production Readiness	Not recommended	Highly recommended
Advanced Queries	Limited	Full SQL + JSON support
Summary: SQLite is suitable for development and testing. PostgreSQL should be adopted for production to ensure scalability, consistency, and maintainability of the feature flag service.

#Change Log:

Please validate various git branches, the changes are introduced incrementally. 
