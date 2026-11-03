from utils.csv_loader import case_by_id
from checker.nat_rules import run_nat_rules


def test_nat_missing():
    case = case_by_id("NETSAGE-026")
    res = run_nat_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "NAT_MISSING" in rules or "NAT_INTERFACE_MISSING" in rules
