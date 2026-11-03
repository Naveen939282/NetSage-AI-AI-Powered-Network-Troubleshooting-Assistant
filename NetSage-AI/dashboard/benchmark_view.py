"""Streamlit components for the NetSage-AI benchmark / performance dashboard."""
from __future__ import annotations

import streamlit as st


def render_system_overview(data, n_rule_modules):
    st.header("System Overview")
    if data:
        o = data["aggregate"]["overall"]
        cols = st.columns(4)
        cols[0].metric("Benchmark cases", o["num_cases"])
        cols[1].metric("Categories", len(data["aggregate"]["category"]))
        cols[2].metric("Rule modules", n_rule_modules)
        cols[3].metric("Correlation accuracy", str(round(o["correlation_correct_rate"] * 100, 1)) + "%")
    else:
        st.info("No evaluation report found. Run `python -m evaluation.runner` first.")
    st.caption("Benchmark uses the deterministic MockProvider; not representative of "
               "live LLM accuracy.")


def render_benchmark(data):
    st.header("Benchmark")
    if not data:
        st.warning("Evaluation report missing. Run `python -m evaluation.runner` "
                   "--output-dir eval_reports`.")
        return
    o = data["aggregate"]["overall"]
    st.markdown("Report timestamp: `" + data.get("generated_at", "?")
                + "`  run_id: " + data.get("run_id", "?"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rule-checker accuracy", str(round(o["rule_checker_accuracy"] * 100, 1)) + "%")
    c2.metric("Correlation correctness", str(round(o["correlation_correct_rate"] * 100, 1)) + "%")
    c3.metric("Conflict F1", str(round(o["conflict_f1"], 3)))
    c4.metric("Review-rec. accuracy", str(round(o["review_recommendation_accuracy"] * 100, 1)) + "%")
    st.markdown("**MockProvider text exact match:** "
                + str(round(o["ai_text_exact_match_rate"] * 100, 1))
                + "% -- deterministic mock echo, not live LLM accuracy.")
    st.info("Benchmark uses the deterministic MockProvider; not representative of "
            "live LLM accuracy.")


def render_category_table(data):
    st.subheader("Category performance")
    if not data:
        st.caption("No evaluation report available.")
        return
    rows = []
    for cat, m in data["aggregate"]["category"].items():
        rows.append({"Category": cat, "Cases": m["n"],
                     "Detection rate": str(round(m["rule_checker_accuracy"] * 100, 1)) + "%",
                     "Correlation correct": str(round(m["correlation_correct_rate"] * 100, 1)) + "%"})
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_failure_cases(data):
    st.header("Known Failure Cases (offline evaluation)")
    from dashboard import case_view
    if not data:
        st.info("No evaluation report available.")
        return
    fails = [c for c in data.get("per_case", [])
             if not c["correlation"]["correct"] or not c["review"]["action_correct"]]
    if not fails:
        st.success("No failures found in the current benchmark.")
        return
    st.caption("Representative cases where the pipeline diverges from the ground-truth "
                               "oracle. OFFLINE EVALUATION information only.")
    for c in fails[:8]:
        expander = st.expander(c["case_id"] + "  (offline)")
        with expander:
            st.markdown("**Correlation:** " + c["correlation"]["status"]
                        + "  (expected " + c["correlation"]["expected_status"] + ")")
            st.markdown("**Recommendation:** " + c["review"]["recommended_action"]
                        + "  (expected " + c["review"]["expected_action"] + ")")
            reason = "correlation " + c["correlation"]["status"] + " != expected " + c["correlation"]["expected_status"]
            if c["review"]["recommended_action"] != c["review"]["expected_action"]:
                reason = reason + "; recommendation mismatch"
            st.markdown("**Reason:** " + reason)
            # Expensive: only re-run the unchanged pipeline when the case is expanded.
            if expander.expanded:
                ctx = case_view.diagnose_case(c["case_id"])
                case = ctx["case"] if ctx else None
                diag = ctx["diag"] if ctx else None
                expected = case.expected_fault if case else ""
                detected = diag.root_cause if diag else ""
                st.markdown("**Expected fault (oracle):** " + (expected or "_(none)_"))
                st.markdown("**Detected root cause:** " + (detected or "_(none)_"))


def render_demo_flow():
    st.header("Demo Flow")
    st.markdown("""
1. Load a troubleshooting case from `data/cases.csv`.
2. Extract structured evidence (topology, show output).
3. Deterministic rules identify observable faults.
4. The AI (MockProvider) generates a diagnosis using rule findings.
5. The correlation engine checks whether the AI is evidence-supported.
6. The human reviewer decides ACCEPT / EDIT / REJECT -- AFTER reviewing
   the Evidence Correlation result above.
""")


def render_architecture():
    st.header("System Architecture")
    st.markdown("""
```
Evidence (show output / topology / symptom)
  -> Deterministic Rule Checker            (no LLM)
  -> AI Diagnosis (MockProvider in demo)
  -> Evidence Correlation                  (no LLM)
     | AI supported by evidence? AI/rule CONFLICT? |
  -> HUMAN REVIEW GATE  (ACCEPT / EDIT / REJECT -- only after reviewing
                        the Evidence Correlation result above)
  -> Audit log (responsible_ai_log.csv)
```
""")
    st.caption("NetSage-AI is decision-support only: it never pushes configuration "
               "and never executes CLI against live devices.")
