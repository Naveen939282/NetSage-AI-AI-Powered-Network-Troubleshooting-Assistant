"""Phase 6 dashboard tests."""
import os
import pytest
from streamlit.testing.v1 import AppTest

from utils.csv_loader import load_cases
from dashboard import eval_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def test_report_loads():
    rep = eval_data.load_report()
    assert rep is not None
    assert rep["aggregate"]["overall"]["num_cases"] > 0


def test_missing_report_handled():
    assert eval_data.load_report("/no/such/file.json") is None
    p = eval_data.latest_report_path()
    assert p is None or os.path.exists(p)


def test_demo_cases_available():
    cases = load_cases()
    cats = {c.category for c in cases}
    for c in ["VLAN", "Default Gateway", "Routing", "ACL", "DHCP"]:
        assert c in cats


def test_app_smoke_loads():
    # AppTest's 3s default is too tight for a cold dashboard render (first-time
    # imports of the ai/correlation/checker modules + streamlit element
    # serialization). The dashboard is decision-support only and must render the
    # full, unchanged pipeline in one pass, so allow a generous timeout.
    at = AppTest.from_file(os.path.join(ROOT, "app.py")).run(timeout=15)
    assert not at.exception


def test_sources_contain_required_sections():
    app = _src("app.py")
    cv = _src("dashboard/case_view.py")
    bv = _src("dashboard/benchmark_view.py")
    assert "MockProvider" in app and "DEMO MODE" in app          # disclaimer
    assert "if diag is None or corr is None" in cv               # review gate
    assert "ACCEPT" in cv and "REJECT" in cv and "EDIT" in cv    # review actions
    assert "Evidence Correlation" in cv                          # correlation shown
    assert "Known Failure Cases" in bv and "System Architecture" in bv and "Demo Flow" in bv
