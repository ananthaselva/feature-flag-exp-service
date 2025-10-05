from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    JSON, CheckConstraint, DateTime, Index, String, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.ext.declarative import DeclarativeMeta

Base: DeclarativeMeta = declarative_base()


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_flags_tenant_key"),
        Index("ix_flags_tenant_state", "tenant_id", "state"),
        CheckConstraint("state IN ('on','off')", name="ck_flags_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(8), default="off", nullable=False)
    variants: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rules: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_segments_tenant_key"),
        Index("ix_segments_tenant", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    criteria: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Audit(Base):
    __tablename__ = "audit"
    __table_args__ = (Index("ix_audit_tenant_ts", "tenant_id", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    entity: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    before: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
