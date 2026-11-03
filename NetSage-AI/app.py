"""NetSage-AI - presentation-ready dashboard (Phase 6).

Composes the existing Phase 1-5 components into a single Streamlit UI:
case load -> evidence -> deterministic rule checker -> AI diagnosis
(MockProvider) -> evidence correlation -> human review gate -> benchmark.

No live devices and no live LLM are used. Everything is deterministic so the
dashboard scores exactly match the offline evaluation report.
"""
import streamlit as st

from utils.csv_loader import load_cases
from checker.network_rules import run_network_rules, _RULE_RUNNERS
from ai.provider import get_provider, MockProvider
from ai.diagnosis import safe_diagnosis
from correlation.engine import correlate
from dashboard import eval_data, case_view, benchmark_view

st.set_page_config(page_title="NetSage-AI", layout="wide")
st.title("NetSage-AI - Evidence-Grounded Network Troubleshooting")
st.caption("DEMO MODE: deterministic pipeline (rule checker + MockProvider AI "
           "+ evidence correlation). No live LLM, no live devices, no autonomous "
           "remediation.")

cases = load_cases()
if not cases:
    st.error("No cases found in data/cases.csv")
    st.stop()


def _fmt(case):
    return case.case_id + " (" + case.category + ")"


# Controlled demo order so a reviewer lands on a representative case.
DEMO_ORDER = ["VLAN", "Default Gateway", "Routing", "ACL", "DHCP"]
default_idx = 0
for i, c in enumerate(cases):
    if c.category in DEMO_ORDER:
        default_idx = i
        break

case = st.sidebar.selectbox("Demo case (controlled selector)", cases,
                            format_func=_fmt, index=default_idx, key="sel_case")
report = eval_data.load_report()

st.sidebar.markdown("---")
st.sidebar.caption("Dashboard renders the deterministic pipeline output. "
                   "Click a section to expand. Recommendations are advisory.")


# --- Live pipeline (deterministic; never raises to the UI) ---
try:
    check_result = run_network_rules(case)
    findings = check_result.get("findings", [])
except Exception as exc:  # pragma: no cover - defensive, kept out of eval
    check_result = {"status": "FAIL", "findings": []}
    findings = []
    st.error("Rule checker error: " + str(exc))

provider = get_provider()
demo = isinstance(provider, MockProvider)
try:
    diag = safe_diagnosis(provider, case, rule_findings=findings)
    corr = correlate(case, findings, diag) if diag is not None else None
except Exception as exc:  # pragma: no cover - defensive, kept out of eval
    diag = None
    corr = None
    st.error("AI/correlation error: " + str(exc))

# --- Dashboard sections (Phase 6 steps 2-12) ---
benchmark_view.render_system_overview(report, len(_RULE_RUNNERS))
st.markdown("---")
case_view.render_case_header(case)
case_view.render_evidence(case)
case_view.render_rules(check_result)
case_view.render_diagnosis(diag, demo=demo)
case_view.render_correlation(corr)
case_view.render_human_review(case, diag, corr, findings)
st.markdown("---")
benchmark_view.render_benchmark(report)
benchmark_view.render_category_table(report)
benchmark_view.render_failure_cases(report)
benchmark_view.render_demo_flow()
benchmark_view.render_architecture()
