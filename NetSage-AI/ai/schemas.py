from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, validator


class AIDiagnosis(BaseModel):
    root_cause: str = Field(...)
    osi_layer: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(...)
    evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    next_command: str = Field(default="")
    fix_steps: List[str] = Field(default_factory=list)
    reasoning_summary: str = Field(default="")
    rule_checker_findings: List[dict] = Field(default_factory=list)
    requires_human_review: bool = Field(default=True)

    @validator("severity")
    def severity_must_be_valid(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"invalid severity '{v}'")
        return v.upper()

    @validator("osi_layer")
    def osi_layer_must_be_valid(cls, v: str) -> str:
        allowed = {"Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5", "Layer 6", "Layer 7", "Multiple Layers", "Unknown"}
        if v not in allowed:
            # Allow case-insensitive shorthand like 'Layer 3'
            if v.title() in allowed:
                return v.title()
            raise ValueError(f"invalid osi_layer '{v}'")
        return v

