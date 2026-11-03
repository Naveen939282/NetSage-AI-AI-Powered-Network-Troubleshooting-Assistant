"""Tests for the correlation result schema (controlled values + validation)."""
import pytest
from pydantic import ValidationError

from correlation.schemas import (
    CorrelationResult, STATUS_VALUES, AI_SUPPORT_VALUES, REVIEW_ACTION_VALUES,
)


def _ok(**overrides):
    base = dict(correlation_status="AGREEMENT", confidence=0.9,
                ai_support_level="SUPPORTED", rule_support_level="SUPPORTED",
                recommended_review_action="ACCEPT")
    base.update(overrides)
    return CorrelationResult(**base)


def test_schema_defaults_populate_lists():
    r = _ok()
    assert r.supported_claims == []
    assert r.conflicts == []
    assert r.missing_evidence == []
    assert r.requires_human_review is True


def test_invalid_correlation_status():
    with pytest.raises(ValidationError):
        _ok(correlation_status="BOGUS")


def test_invalid_ai_support_level():
    with pytest.raises(ValidationError):
        _ok(ai_support_level="MAYBE")


def test_invalid_rule_support_level():
    with pytest.raises(ValidationError):
        _ok(rule_support_level="MAYBE")


def test_invalid_review_action():
    with pytest.raises(ValidationError):
        _ok(recommended_review_action="MAYBE")


def test_confidence_validation():
    with pytest.raises(ValidationError):
        _ok(confidence=1.5)
    with pytest.raises(ValidationError):
        _ok(confidence=-0.1)
    # boundaries are valid
    CorrelationResult(correlation_status="AGREEMENT", confidence=0.0,
                      ai_support_level="SUPPORTED", rule_support_level="SUPPORTED",
                      recommended_review_action="ACCEPT")
    CorrelationResult(correlation_status="AGREEMENT", confidence=1.0,
                      ai_support_level="SUPPORTED", rule_support_level="SUPPORTED",
                      recommended_review_action="ACCEPT")


def test_controlled_value_enums():
    assert set(STATUS_VALUES) == {"AGREEMENT", "CONFLICT", "PARTIAL_AGREEMENT", "INSUFFICIENT_EVIDENCE"}
    assert set(AI_SUPPORT_VALUES) == {"SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNKNOWN"}
    assert set(REVIEW_ACTION_VALUES) == {"ACCEPT", "EDIT", "REJECT", "INVESTIGATE"}


def test_conflicts_are_dicts():
    r = _ok(conflicts=[{"concept": "route", "why": "x"}])
    assert r.conflicts[0]["concept"] == "route"


def test_requires_human_review_stays_true_on_conflict():
    r = _ok(correlation_status="CONFLICT", confidence=0.2)
    assert r.requires_human_review is True
