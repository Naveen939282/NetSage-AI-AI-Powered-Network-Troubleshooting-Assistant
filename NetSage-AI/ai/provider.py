from __future__ import annotations
from typing import Any, Optional
import os

from ai.schemas import AIDiagnosis
from utils.csv_loader import Case
from ai.parser import parse_ai_response


class AIProvider:
    def generate_diagnosis(self, case: Case, rule_findings: list | None = None) -> Any:
        raise NotImplementedError()
    
    # Backwards-compatible alias used by the Streamlit app
    def diagnose(self, case: Case, rule_findings: list | None = None) -> Any:
        return self.generate_diagnosis(case, rule_findings=rule_findings)


class MockProvider(AIProvider):
    """Deterministic demo provider used when no AI key is configured.

    Returns a Pydantic AIDiagnosis built from case.expected_fault and the case evidence.
    Clearly labeled as DEMO output: callers should treat this as mock data.
    """

    def generate_diagnosis(self, case: Case, rule_findings: list | None = None) -> AIDiagnosis:
        lines = [l.strip() for l in case.show_output.splitlines() if l.strip()]
        evidence = lines[:6]
        conf_map = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.4, "CRITICAL": 0.95}
        confidence = conf_map.get(case.severity.upper(), 0.5)

        diag = AIDiagnosis(
            root_cause=case.expected_fault or "Insufficient evidence to determine the root cause",
            osi_layer=case.osi_layer or "Unknown",
            confidence=confidence,
            severity=case.severity or "MEDIUM",
            evidence=[f"DEMO MODE — {e}" for e in evidence],
            missing_evidence=[],
            next_command=case.expected_command or "",
            fix_steps=[case.expected_fix] if case.expected_fix else [],
            reasoning_summary=f"DEMO MODE — derived from dataset expected_fault for {case.case_id}",
            rule_checker_findings=rule_findings or [],
            requires_human_review=True,
        )
        return diag

    # Compatibility: Streamlit app expects `diagnose()`; keep as thin wrapper.
    def diagnose(self, case: Case, rule_findings: list | None = None) -> AIDiagnosis:
        return self.generate_diagnosis(case, rule_findings=rule_findings)


def get_provider() -> AIProvider:
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockProvider()
    # For now, fallback to MockProvider for any other setting; placeholder for live providers
    return MockProvider()

