from utils.csv_loader import case_by_id
from checker.dhcp_rules import run_dhcp_rules


def test_missing_dhcp_pool():
    case = case_by_id("NETSAGE-010")
    res = run_dhcp_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "MISSING_DHCP_POOL" in rules


def test_dhcp_excluded_overlap():
    case = case_by_id("NETSAGE-011")
    res = run_dhcp_rules(case)
    rules = [f["rule"] for f in res.get("findings", [])]
    assert "DHCP_EXCLUDED_OVERLAP" in rules
