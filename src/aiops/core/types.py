"""Shared pydantic models across agents."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class QueryCategory(str, Enum):
    QA = "qa"
    RESOURCE_ALERT = "resource"
    LOG_ERROR = "log"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class QARequest(BaseModel):
    session_id: str
    user_id: str
    query: str
    trace_id: str


class QAResponse(BaseModel):
    trace_id: str
    answer: str
    docs: list["RetrievedDoc"] = []


class RAGRequest(BaseModel):
    trace_id: str
    query: str
    category: QueryCategory = QueryCategory.QA
    top_k: int = 10


class RetrievedDoc(BaseModel):
    doc_id: str
    content: str
    score: float
    source: Literal["vector", "bm25", "fused", "rerank"] = "fused"
    metadata: dict = {}


class RAGResponse(BaseModel):
    trace_id: str
    docs: list[RetrievedDoc]
    from_cache: bool = False


class AlertEvent(BaseModel):
    alert_id: str
    service: str
    metric: str
    value: float
    threshold: float
    severity: Literal["P0", "P1", "P2", "P3"] = "P2"
    detected_by: Literal["3sigma", "ewma", "vote", "regex"] = "vote"
    ts: datetime = Field(default_factory=datetime.utcnow)
    raw: dict = {}


class RCAResult(BaseModel):
    alert_id: str
    root_cause_service: str
    reasoning: str
    evidence: list[RetrievedDoc] = []
    suggested_actions: list[str] = []


class HealRequest(BaseModel):
    alert_id: str
    runbook: str
    params: dict = {}


class HealResult(BaseModel):
    alert_id: str
    runbook: str
    success: bool
    logs: list[str] = []


class EvalTrace(BaseModel):
    trace_id: str
    stage: str
    input: dict
    output: dict
    latency_ms: float
    extra: dict = {}


QAResponse.model_rebuild()
