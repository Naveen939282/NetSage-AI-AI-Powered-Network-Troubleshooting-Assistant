import os
from ai.provider import get_provider, MockProvider
from utils.csv_loader import case_by_id
from ai.schemas import AIDiagnosis


def test_get_provider_default():
    os.environ.pop("AI_PROVIDER", None)
    p = get_provider()
    assert isinstance(p, MockProvider)


def test_mock_provider_outputs_schema():
    case = case_by_id("NETSAGE-001")
    p = MockProvider()
    diag = p.generate_diagnosis(case, rule_findings=[{"rule": "X"}])
    assert isinstance(diag, AIDiagnosis)
    assert diag.requires_human_review is True
