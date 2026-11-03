import pytest
from ai.schemas import AIDiagnosis


def test_valid_schema():
    payload = {
        "root_cause": "Test",
        "osi_layer": "Layer 3",
        "confidence": 0.5,
        "severity": "HIGH",
        "evidence": ["line1"],
        "missing_evidence": [],
        "next_command": "show ip route",
        "fix_steps": ["do something"],
        "reasoning_summary": "summary",
        "rule_checker_findings": [],
        "requires_human_review": True,
    }
    d = AIDiagnosis.model_validate(payload)
    assert d.confidence == 0.5


def test_invalid_confidence():
    payload = {"root_cause": "x", "osi_layer": "Layer 3", "confidence": 1.5, "severity": "LOW"}
    with pytest.raises(Exception):
        AIDiagnosis.model_validate(payload)


def test_invalid_severity():
    payload = {"root_cause": "x", "osi_layer": "Layer 3", "confidence": 0.5, "severity": "BAD"}
    with pytest.raises(Exception):
        AIDiagnosis.model_validate(payload)
