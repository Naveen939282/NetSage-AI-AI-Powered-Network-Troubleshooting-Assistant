"""Tests for the deterministic correlation engine."""
import csv
import json
import pytest

from utils.csv_loader import Case, load_cases
from checker.network_rules import run_network_rules
from ai.provider import MockProvider
from ai.schemas import AIDiagnosis
from correlation.engine import correlate
from correlation.schemas import CorrelationResult
from review import human_review
from review import review_logger as rl


def _case(show_output="", case_id="TST"):
    return Case(case_id=case_id, category="Test", title="t", symptom="",
                topology="", show_output=show_output, expected_fault="",
                osi_layer="Layer 3", concept="", severity="LOW",
                expected_command="", expected_fix="")


def _diag(root_cause, **kw):
    base = dict(root_cause=root_cause, osi_layer="Layer 3", confidence=0.6,
                severity="MEDIUM", evidence=[], missing_evidence=[],
                next_command="", fix_steps=[], reasoning_summary="test",
                rule_checker_findings=[], requires_human_review=True)
    base.update(kw)
    return AIDiagnosis(**base)


def _f(rule):
    return {"rule": rule, "message": "m", "severity": "HIGH",
            "evidence": "e", "details": {}, "module": "t"}


def test_strong_agreement_gateway():
    so = """R1#show ip route
S*   0.0.0.0/0 [1/0] via 10.0.0.254
C    192.168.1.0/24 is directly connected, Ethernet0/0"""
    findings = [_f("DEFAULT_GATEWAY_OUTSIDE_SUBNET")]
    diag = _diag("Default gateway is outside the host subnet.")
    r = correlate(_case(so), findings, diag)
    assert r.correlation_status == "AGREEMENT"
    assert r.ai_support_level == "SUPPORTED"
    assert r.rule_support_level == "SUPPORTED"
    assert r.recommended_review_action == "ACCEPT"
    assert r.confidence >= 0.7


def test_partial_agreement_vlan():
    findings = [_f("VLAN_MISMATCH")]
    diag = _diag("VLAN configuration appears problematic.")
    r = correlate(_case(""), findings, diag)
    assert r.correlation_status == "PARTIAL_AGREEMENT"
    assert r.ai_support_level == "PARTIALLY_SUPPORTED"
    assert r.recommended_review_action == "INVESTIGATE"


def test_direct_conflict_route():
    so = """R1#show ip route
S*   0.0.0.0/0 [1/0] via 10.0.0.1"""
    findings = [{"rule": "DEFAULT_ROUTE_EXISTS", "message": "A default route is present",
                 "severity": "HIGH", "evidence": "e", "details": {}, "module": "t"}]
    diag = _diag("Default route is missing.")
    r = correlate(_case(so), findings, diag)
    assert r.correlation_status == "CONFLICT"
    assert r.ai_support_level == "UNSUPPORTED"
    assert r.rule_support_level == "UNSUPPORTED"
    assert len(r.conflicts) == 1
    assert r.conflicts[0]["concept"] == "route"
    assert r.recommended_review_action == "INVESTIGATE"


def test_unsupported_ai_claim_dns():
    findings = [_f("VLAN_MISMATCH")]
    diag = _diag("DNS server is unreachable.")
    r = correlate(_case(""), findings, diag)
    assert r.correlation_status == "INSUFFICIENT_EVIDENCE"
    assert r.ai_support_level == "UNSUPPORTED"
    assert any("dns" in c.lower() for c in r.unsupported_claims)


def test_insufficient_evidence_no_rules():
    diag = _diag("Routing issue.")
    r = correlate(_case(""), [], diag)
    assert r.correlation_status == "INSUFFICIENT_EVIDENCE"


def test_route_contradicts_evidence():
    so = """R1#show ip route
S*   0.0.0.0/0 [1/0] via 10.0.0.1
C    10.0.0.0/24 is directly connected, Ethernet0/0"""
    diag = _diag("Default route is missing.")
    r = correlate(_case(so), [], diag)
    assert r.correlation_status == "CONFLICT"
    assert any(c["concept"] == "route" for c in r.conflicts)


def test_acl_vs_vlan_is_insufficient_or_conflict():
    findings = [_f("ACL_DENY")]
    diag = _diag("The root cause is a missing VLAN.")
    r = correlate(_case(""), findings, diag)
    assert r.correlation_status in ("CONFLICT", "INSUFFICIENT_EVIDENCE")


def test_case_id_not_hardcoded():
    so = """R1#show ip route
S* 0.0.0.0/0 [1/0] via 10.0.0.1"""
    a = correlate(_case(so, case_id="AAA"), [], _diag("Default route exists."))
    b = correlate(_case(so, case_id="BBB"), [], _diag("Default route exists."))
    assert a.correlation_status == b.correlation_status == "AGREEMENT"


# --- integration with the real rule checker + real provider + real case ---
def test_real_pipeline_on_real_case():
    case = load_cases()[0]
    findings = run_network_rules(case)["findings"]
    diag = MockProvider().diagnose(case, rule_findings=findings)
    r = correlate(case, findings, diag)
    assert isinstance(r, CorrelationResult)
    assert 0.0 <= r.confidence <= 1.0
    assert r.correlation_status in ("AGREEMENT", "PARTIAL_AGREEMENT", "INSUFFICIENT_EVIDENCE", "CONFLICT")
    # The correlation engine must never read ground-truth fields (STEP 16).
    alt = Case(case_id=case.case_id, category=case.category, title=case.title,
               symptom=case.symptom, topology=case.topology, show_output=case.show_output,
               expected_fault="REMOVED-GROUND-TRUTH", osi_layer=case.osi_layer,
               concept=case.concept, severity=case.severity,
               expected_command=case.expected_command, expected_fix=case.expected_fix)
    r2 = correlate(alt, findings, diag)
    assert r.correlation_status == r2.correlation_status


def test_none_diagnosis_returns_none():
    assert correlate(_case("so"), [], None) is None


# --- review persistence carries the correlation fields ---
@pytest.fixture
def isolate_log(monkeypatch, tmp_path):
    log = tmp_path / "reviews.csv"
    monkeypatch.setattr(rl, "RESPONSIBLE_LOG_CSV", str(log))
    return log


def test_review_persists_correlation_fields(isolate_log):
    human_review.submit_review(
        "EDIT", "NETSAGE-002", "root cause text", "edited root", "note",
        correlation_status="CONFLICT", correlation_confidence="0.25",
        ai_support_level="UNSUPPORTED", rule_support_level="UNSUPPORTED",
        recommended_review_action="INVESTIGATE",
        conflicts=json.dumps([{"concept": "route"}]),
    )
    rows = list(csv.DictReader(open(isolate_log, encoding="utf-8")))
    assert len(rows) == 1
    r = rows[0]
    assert r["human_decision"] == "EDIT"
    assert r["correlation_status"] == "CONFLICT"
    assert r["correlation_confidence"] == "0.25"
    assert r["ai_support_level"] == "UNSUPPORTED"
    assert r["recommended_review_action"] == "INVESTIGATE"
    assert json.loads(r["conflicts"]) == [{"concept": "route"}]
