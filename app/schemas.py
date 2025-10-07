from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Variant(BaseModel):
    key: str
    weight: float = Field(ge=0, le=100)


class Rollout(BaseModel):
    variant: Optional[str] = None
    distribution: Optional[List[Variant]] = None
    weight: Optional[float] = None  # for simple % rollout


class Rule(BaseModel):
    id: str
    order: int = 0
    when: Dict[str, Any] = {}
    rollout: Rollout


class FlagIn(BaseModel):
    key: str
    description: Optional[str] = None
    state: str = Field(pattern="^(on|off)$")
    variants: List[Variant]
    rules: List[Rule] = []


class FlagOut(BaseModel):
    key: str
    description: Optional[str] = None
    state: str
    variants: List[Variant]
    rules: List[Rule] = []


class SegmentIn(BaseModel):
    key: str
    criteria: Dict[str, Any]


class SegmentOut(BaseModel):
    key: str
    criteria: Dict[str, Any]


class TokenRequest(BaseModel):
    client_id: str
    scopes: List[str] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EvaluateRequest(BaseModel):
    flag_key: str
    user: Dict[str, Any]


class EvaluateResponse(BaseModel):
    variant: str
    reason: str
    rule_id: Optional[str] = None
    details: Dict[str, Any] = {}


# --- Audit schema ---
class AuditOut(BaseModel):
    id: int
    tenant_id: str
    actor: str
    entity: str
    entity_key: str
    action: str
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    ts: datetime

    model_config = {
        "from_attributes": True  # <- this is the Pydantic v2 way
    }
