from __future__ import annotations

from ai.provider import get_provider
from ai.parser import parse_ai_response
from ai.schemas import AIDiagnosis


def generate_diagnosis(case, rule_findings=None, provider=None):
    """Run the configured (or explicitly supplied) provider and normalize to AIDiagnosis."""
    provider = provider or get_provider()
    raw = provider.generate_diagnosis(case, rule_findings=rule_findings)
    if isinstance(raw, AIDiagnosis):
        return raw
    return parse_ai_response(raw)


def safe_diagnosis(provider, case, rule_findings=None):
    """Run generate_diagnosis but never raise; return None on any failure.

    Lets the Streamlit app degrade gracefully: the Human Review section gates on
    the returned value, so an AI parse/provider failure can never produce an
    unbound variable or break that section.
    """
    try:
        return generate_diagnosis(case, rule_findings=rule_findings, provider=provider)
    except Exception:
        return None
