"""Ground-truth label derivation for the offline NetSage-AI evaluator.

THIS IS THE ONLY OFFLINE module that reads ground-truth columns
(``expected_fault``, ``expected_command``, ``expected_fix``, ``concept``,
``osi_layer``, ``severity``) from a ``Case``.  The live runtime pipeline
(checker / AI / correlation / human-review) never imports this module, so
ground truth cannot leak into any runtime decision.

Oracle methodology (documented):
  * ``expected_concept``      - maps a case category to the em concept key.
  * ``expected_correlation_status`` - AGREE/CONFLICT/PARTIAL/INSUFFICIENT
    derived from (rule-checker concept vs. AI detected concept & sentiment)
    using the SAME concept detectors the pipeline uses -- i.e. it answers
    "should a correct engine have agreed or flagged a conflict?".
  * ``expected_conflict``     - True when the rule checker signals the fault
    concept as ``problematic`` but the AI states that concept with a
    non-problematic sentiment (present/absent): an objective disagreement.
  * ``expected_action``       - ACCEPT / INVESTIGATE / EDIT derived from the
    oracle above.

NOTE: the offline MockProvider echoes ``expected_fault`` verbatim, so
``ai_text_exact_match`` will read ~100% -- this is reported transparently as
a known property of the demo provider, not an inflation of live AI.
"""
from __future__ import annotations

from correlation import evidence_matcher as em

_CATEGORY_CONCEPT = {
    "VLAN": "vlan", "Access VLAN": "vlan",
    "Gateway": "gateway", "Default Gateway": "gateway",
    "Routing": "route", "Route": "route",
    "ACL": "acl",
    "NAT": "nat",
    "DHCP": "dhcp",
    "IP": "ip",
    "Interface": "interface",
    "Wireless": "wireless",
    "OSPF": "ospf",
    "DNS": "dns",
}


def expected_concept(case):
    """em concept key the ground-truth fault belongs to (from case.category)."""
    return _CATEGORY_CONCEPT.get(case.category, "general")


def _ai_state(diag, ec):
    if diag is None:
        return "none"
    return em.detect_ai_concepts(diag.root_cause).get(ec, "none")


def expected_correlation_status(case, findings, diag):
    """Oracle correlation label derived purely from ground-truth semantics."""
    ec = expected_concept(case)
    checker_hit = ec in {em.rule_concept(f.get("rule", "")) for f in findings}
    ai_state = _ai_state(diag, ec)
    ai_addressed = ai_state in ("problematic", "present", "absent")
    ai_sent_ok = ai_state == "problematic"
    if checker_hit and ai_addressed and ai_sent_ok:
        return "AGREEMENT"
    if checker_hit and ai_addressed and not ai_sent_ok:
        return "CONFLICT"
    if checker_hit and not ai_sent_ok:
        return "PARTIAL_AGREEMENT"
    if not checker_hit and ai_sent_ok:
        return "PARTIAL_AGREEMENT"
    return "INSUFFICIENT_EVIDENCE"


def expected_conflict(case, findings, diag):
    """True when rules signal a fault the AI downplays/contradicts."""
    ec = expected_concept(case)
    ai_state = _ai_state(diag, ec)
    checker_says_problem = any(
        em.rule_concept(f.get("rule", "")) == ec
        and em.rule_sentiment(f.get("rule", "")) == "problematic"
        for f in findings)
    ai_mismatch = ai_state in ("present", "absent")  # stated, but not as a fault
    return bool(checker_says_problem and ai_mismatch)


def expected_action(case, findings, diag):
    if expected_conflict(case, findings, diag):
        return "INVESTIGATE"
    status = expected_correlation_status(case, findings, diag)
    if status == "AGREEMENT":
        return "ACCEPT"
    if status == "INSUFFICIENT_EVIDENCE":
        return "EDIT"
    return "INVESTIGATE"
