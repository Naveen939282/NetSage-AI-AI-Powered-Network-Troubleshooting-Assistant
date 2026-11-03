"""Phase 3 integration tests.

Covers:
- rule findings are passed into the AI provider and preserved
- demo-mode labeling + unsupported AI_PROVIDER fallback
- human ACCEPT / REJECT / EDIT review persistence
- an AI/provider failure never breaks the human-review path
"""
import csv
import json

import pytest

from utils.csv_loader import case_by_id
from checker.network_rules import run_network_rules
from ai.provider import get_provider, MockProvider, AIProvider
from ai.diagnosis import generate_diagnosis, safe_diagnosis
from ai.schemas import AIDiagnosis
from review import human_review
from review import review_logger as rl

SAMPLE_CASE_ID = "NETSAGE-002"


def _findings(case):
    return run_network_rules(case)["findings"]


# ---------------------------------------------------------------------------
# Evidence -> Rule checker -> AI provider wiring
# ---------------------------------------------------------------------------
def test_rule_findings_are_passed_into_provider():
    """The provider receives the deterministic rule findings for the case."""
    case = case_by_id(SAMPLE_CASE_ID)
    findings = _findings(case)
    assert findings, "NETSAGE-002 should produce rule findings"
    diag = MockProvider().diagnose(case, rule_findings=findings)
    assert isinstance(diag, AIDiagnosis)
    assert diag.rule_checker_findings == findings


def test_provider_preserves_rule_findings():
    """safe_diagnosis carries the exact findings list onto the diagnosis."""
    case = case_by_id(SAMPLE_CASE_ID)
    findings = _findings(case)
    diag = safe_diagnosis(MockProvider(), case, rule_findings=findings)
    assert diag is not None
        # pydantic v2 rebuilds the list (contents preserved, not the same object)
    assert diag.rule_checker_findings == findings


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------
def test_demo_mode_labeling():
    case = case_by_id("NETSAGE-001")
    dump = MockProvider().diagnose(case, rule_findings=[]).model_dump()
    assert any("DEMO MODE" in e for e in dump["evidence"])
    assert "DEMO MODE" in dump["reasoning_summary"]


def test_demo_mode_unsupported_value_falls_back(monkeypatch):
    """An unsupported AI_PROVIDER must fall back to the mock (demo) provider."""
    monkeypatch.setenv("AI_PROVIDER", "weave")
    assert isinstance(get_provider(), MockProvider)


# ---------------------------------------------------------------------------
# Human review (log isolated to a temp CSV)
# ---------------------------------------------------------------------------
@pytest.fixture
def isolate_log(monkeypatch, tmp_path):
    log = tmp_path / "reviews.csv"
    monkeypatch.setattr(rl, "RESPONSIBLE_LOG_CSV", str(log))
    return log


def test_human_accept_review(isolate_log):
    human_review.submit_review("ACCEPT", "NETSAGE-001", "root-a", "root-a", "Accepted as correct")
    rows = list(csv.DictReader(open(isolate_log, encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["human_decision"] == "ACCEPT"
    assert rows[0]["corrected_root_cause"] == "root-a"


def test_human_reject_review(isolate_log):
    human_review.submit_review("REJECT", "NETSAGE-001", "root-a", "", "Rejected by reviewer")
    rows = list(csv.DictReader(open(isolate_log, encoding="utf-8")))
    assert rows[0]["human_decision"] == "REJECT"
    assert rows[0]["corrected_root_cause"] == ""


def test_human_edit_review(isolate_log):
    human_review.submit_review(
        "EDIT", "NETSAGE-001", "root-a", "edited-root", "reviewer note",
        edited_osi_layer="Layer 3", edited_confidence="0.7",
        edited_next_command="show ip route",
        edited_fix_steps=json.dumps(["step one", "step two"]),
    )
    rows = list(csv.DictReader(open(isolate_log, encoding="utf-8")))
    r = rows[0]
    assert r["human_decision"] == "EDIT"
    assert r["corrected_root_cause"] == "edited-root"
    assert r["edited_osi_layer"] == "Layer 3"
    assert r["edited_confidence"] == "0.7"
    assert r["edited_next_command"] == "show ip route"
    assert json.loads(r["edited_fix_steps"]) == ["step one", "step two"]


# ---------------------------------------------------------------------------
# Resilience: AI failure must not break the human-review section
# ---------------------------------------------------------------------------
class _BadProvider(AIProvider):
    def generate_diagnosis(self, case, rule_findings=None):
        raise RuntimeError("simulated provider failure")


def test_ai_failure_does_not_break_human_review():
    """safe_diagnosis swallows provider failures so the app can gate review off None."""
    case = case_by_id("NETSAGE-001")
    assert safe_diagnosis(_BadProvider(), case, rule_findings=[]) is None
    # The un-guarded generator still surfaces the error (the app relies on
    # safe_diagnosis to contain it).
    with pytest.raises(RuntimeError):
        generate_diagnosis(case, rule_findings=[], provider=_BadProvider())
