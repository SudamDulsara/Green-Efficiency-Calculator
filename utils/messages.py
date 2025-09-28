from __future__ import annotations
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
import uuid
import time

Role = Literal["coordinator", "intake", "auditor", "recommender", "estimator", "tool"]
Intent = Literal[
    "plan", "normalize", "audit", "recommend", "estimate", "repair",
    "lookup_tariff", "parse_bill"
]
Status = Literal["ok", "error"]

class Message(BaseModel):
    role: Role
    intent: Intent
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: Status = "ok"
    notes: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = Field(default_factory=lambda: time.time())

class TraceEvent(BaseModel):
    trace_id: str
    step: str
    msg: Message
