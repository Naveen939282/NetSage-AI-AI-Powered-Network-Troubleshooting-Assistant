from utils.csv_loader import case_by_id
from checker.interface_rules import run_interface_rules


def test_interface_admin_down():
    case = case_by_id("NETSAGE-008")
    res = run_interface_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "INTERFACE_ADMIN_DOWN" in rules


def test_interface_up_up():
    # Choose a case where interfaces are up (NETSAGE-001 shows connected interfaces)
    case = case_by_id("NETSAGE-001")
    res = run_interface_rules(case)
    assert res["status"] in ("PASS", "FAIL")
    # ensure we don't incorrectly flag INTERFACE_ADMIN_DOWN for up interfaces
    rules = [f["rule"] for f in res["findings"]]
    assert "INTERFACE_ADMIN_DOWN" not in rules
