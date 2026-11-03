from utils.csv_loader import case_by_id
from checker.vlan_rules import run_vlan_rules


def test_missing_vlan():
    case = case_by_id("NETSAGE-002")
    res = run_vlan_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "MISSING_VLAN" in rules


def test_trunk_vlan_not_allowed():
    case = case_by_id("NETSAGE-003")
    res = run_vlan_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "TRUNK_VLAN_NOT_ALLOWED" in rules
