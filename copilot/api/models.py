"""Pydantic data models for Project Atlas API Service."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    client_id: str = Field(..., description="Unique client identifier (e.g., C-01, C-02)", min_length=2, max_length=50)
    query: str = Field(..., description="User market research question", min_length=2, max_length=2000)
    session_id: Optional[str] = Field(default="default-session", description="Session identifier for tracking")


class CitationItem(BaseModel):
    report_id: str
    page: int
    publisher: str
    quote: str


class ConflictItem(BaseModel):
    metric: str
    source_a: Dict[str, Any]
    source_b: Optional[Dict[str, Any]] = None
    scope_difference: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    derived_values: List[Dict[str, Any]] = Field(default_factory=list)
    escalated: bool
    escalation_ticket_id: Optional[str] = None
    cached: bool = False
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class IngestResponse(BaseModel):
    status: str
    message: str
    total_chunks: int


class EscalationTicket(BaseModel):
    ticket_id: str
    client_id: str
    query: str
    reason: str
    confidence: float
    status: str
    created_at: str


class FeedbackRequest(BaseModel):
    client_id: str
    session_id: str
    query: str
    response_text: str
    rating: str = Field(..., pattern="^(thumbs_up|thumbs_down)$")
