from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, ConfigDict

CorrelationStatus = Literal[
    "AGREEMENT", "CONFLICT", "PARTIAL_AGREEMENT", "INSUFFICIENT_EVIDENCE"
]
SupportLevel = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNKNOWN"]
ReviewAction = Literal["ACCEPT", "EDIT", "REJECT", "INVESTIGATE"]

STATUS_VALUES = ["AGREEMENT", "CONFLICT", "PARTIAL_AGREEMENT", "INSUFFICIENT_EVIDENCE"]
AI_SUPPORT_VALUES = ["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNKNOWN"]
REVIEW_ACTION_VALUES = ["ACCEPT", "EDIT", "REJECT", "INVESTIGATE"]


class CorrelationResult(BaseModel):
    """Structured result of comparing AI diagnosis, rule findings, and evidence."""

    model_config = ConfigDict(extra="ignore")

    correlation_status: CorrelationStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    ai_support_level: SupportLevel
    rule_support_level: SupportLevel
    recommended_review_action: ReviewAction
    supported_claims: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    conflicts: List[dict] = Field(default_factory=list)
    evidence_matches: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    requires_human_review: bool = True
