"""Streamlit UI components for the live case diagnosis dashboard."""
from __future__ import annotations

import json
import streamlit as st

from checker import normalize as _norm
from review import human_review


_STATUS_LABEL = {
    "AGREEMENT": "AGREEMENT",
    "CONFLICT": "CONFLICT",
    "PARTIAL_AGREEMENT": "PARTIAL_AGREEMENT",
    "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
}


@st.cache_data
def diagnose_case(case_id):
    """Re-run the deterministic pipeline for a case (display context only).

    The dashboard intentionally surfaces the human-readable expected vs.
    detected fault for failing cases WITHOUT recalibrating any metric. The
    same unchanged pipeline is executed; the offline metrics remain the source
    of truth for scoring.
    """
    from utils.csv_loader import case_by_id
    from checker.network_rules import run_network_rules
    from ai.provider import get_provider
    from ai.diagnosis import safe_diagnosis
    from correlation.engine import correlate
    case = case_by_id(case_id)
    if case is None:
        return None
    findings = run_network_rules(case)["findings"]
    diag = safe_diagnosis(get_provider(), case, rule_findings=findings)
    corr = correlate(case, findings, diag) if diag is not None else None
    return {"case": case, "findings": findings, "diag": diag, "corr": corr}


def render_case_header(case):
    st.subheader(case.title or case.case_id)
    st.caption("Case ID: " + case.case_id + "  |  Category: " + case.category
               + "  |  Severity: " + case.severity.upper())


def render_evidence(case):
    st.subheader("Network Evidence")
    st.markdown("**Topology**")
    st.write(case.topology or "_(no topology provided)_")
    so = case.show_output or ""
    with st.expander("Show raw show output (collapsible)", expanded=False):
        st.code(so)
    norm = _norm.normalize_show_output(so)
    sections = sum(1 for v in norm.values() if v)
    st.caption("Normalized " + str(sections) + " evidence sections from "
               + str(len(norm.get("raw_sections", [])))
               + " parsed show commands.")


def render_rules(check_result):
    st.subheader("Deterministic Rule Checker")
    findings = check_result.get("findings", []) if isinstance(check_result, dict) else []
    if not findings:
        st.success("PASS - no deterministic rule findings.")
        return
    rows = [{"Rule": f.get("rule", ""), "Module": f.get("module", ""),
             "Severity": f.get("severity", ""), "Finding": f.get("message", ""),
             "Evidence": f.get("evidence", "")} for f in findings]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.error("FAIL - " + str(len(findings)) + " rule finding(s).")


def render_diagnosis(diag, demo=True):
    st.subheader("AI Diagnosis")
    if demo:
        st.info("DEMO MODE - deterministic MockProvider output (not a live LLM).")
    if diag is None:
        st.error("AI provider could not produce a valid diagnosis.")
        return
    st.markdown("**Root cause:** " + diag.root_cause)
    c1, c2, c3 = st.columns(3)
    c1.metric("OSI layer", diag.osi_layer)
    c2.metric("Confidence", str(diag.confidence))
    c3.metric("Severity", diag.severity)
    if diag.next_command:
        st.markdown("**Recommended command:** `" + diag.next_command + "`")
    if diag.fix_steps:
        st.markdown("**Fix steps:**")
        for i, s in enumerate(diag.fix_steps, 1):
            st.markdown(str(i) + ". " + s)
    if diag.evidence:
        with st.expander("Diagnosis evidence"):
            for e in diag.evidence:
                st.markdown("- " + str(e))



def render_correlation(corr):
    st.subheader("Evidence Correlation")
    if corr is None:
        st.info("No correlation available (requires a valid AI diagnosis).")
        return
    label = _STATUS_LABEL.get(corr.correlation_status, corr.correlation_status)
    st.markdown("**" + label + "**"
                + "  |  AI support: " + corr.ai_support_level
                + "  |  Rule support: " + corr.rule_support_level
                + "  |  Confidence: " + str(round(corr.confidence, 3)))
    st.progress(corr.confidence)
    if corr.supported_claims:
        st.success("Supported claims: " + str(len(corr.supported_claims)))
    if corr.unsupported_claims:
        st.warning("Unsupported claims: " + str(len(corr.unsupported_claims)))
    if corr.conflicts:
        st.error("CONFLICTS (" + str(len(corr.conflicts)) + ") - AI vs. rule/evidence:")
        st.json(corr.conflicts)
    if corr.missing_evidence:
        st.info("Missing evidence: " + str(len(corr.missing_evidence)))
    st.caption("Recommendation: " + corr.recommended_review_action.upper())


def render_human_review(case, diag, corr, findings):
    st.subheader("Human Review")
    st.caption("Review the Evidence Correlation result above BEFORE deciding. "
               "The correlation result MUST be visible before ACCEPT / EDIT / REJECT.")
    if diag is None or corr is None:
        st.info("No diagnosis or correlation available - human review is gated off.")
        return
    corr_fields = {
        "correlation_status": corr.correlation_status,
        "correlation_confidence": str(corr.confidence),
        "ai_support_level": corr.ai_support_level,
        "rule_support_level": corr.rule_support_level,
        "recommended_review_action": corr.recommended_review_action,
        "conflicts": json.dumps(corr.conflicts),
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("ACCEPT", key="dash_accept"):
            human_review.submit_review("ACCEPT", case.case_id, diag.root_cause,
                                       diag.root_cause, "Accepted as correct", **corr_fields)
            st.success("Decision saved: ACCEPT")
    with c2:
        if st.button("REJECT", key="dash_reject"):
            human_review.submit_review("REJECT", case.case_id, diag.root_cause,
                                       "", "Rejected by reviewer", **corr_fields)
            st.success("Decision saved: REJECT")
    with c3:
        if st.button("Toggle EDIT", key="dash_edit_toggle"):
            st.session_state["dash_edit_open"] = not st.session_state.get("dash_edit_open", False)
    if st.session_state.get("dash_edit_open"):
        with st.form(key="edit_form"):
            ed_root = st.text_area("root_cause", value=diag.root_cause, key="ed_root")
            ed_fix = st.text_area("fix_steps (one per line)",
                                  value=chr(10).join(diag.fix_steps), key="ed_fix")
            ed_note = st.text_area("reviewer_note", key="ed_note")
            if st.form_submit_button("Save EDIT"):
                fix = [s.strip() for s in ed_fix.splitlines() if s.strip()]
                human_review.submit_review("EDIT", case.case_id, diag.root_cause,
                                           ed_root, ed_note,
                                           edited_fix_steps=json.dumps(fix), **corr_fields)
                st.success("Decision saved: EDIT")
