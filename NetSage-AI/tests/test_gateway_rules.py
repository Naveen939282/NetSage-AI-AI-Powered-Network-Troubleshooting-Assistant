from utils.csv_loader import case_by_id
from checker.gateway_rules import run_gateway_rules


def test_gateway_outside_subnet():
    case = case_by_id("NETSAGE-007")
    res = run_gateway_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "GATEWAY_OUTSIDE_SUBNET" in rules


def test_default_route_missing():
    case = case_by_id("NETSAGE-019")
    res = run_gateway_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "DEFAULT_GATEWAY_MISSING" in rules
