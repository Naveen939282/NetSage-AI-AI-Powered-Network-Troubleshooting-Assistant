from utils.csv_loader import case_by_id
from checker.routing_rules import run_routing_rules


def test_invalid_next_hop():
    case = case_by_id("NETSAGE-017")
    res = run_routing_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "INVALID_NEXT_HOP" in rules


def test_default_route_missing_routing():
    case = case_by_id("NETSAGE-019")
    res = run_routing_rules(case)
    rules = [f["rule"] for f in res.get("findings", [])]
    assert "DEFAULT_ROUTE_MISSING" in rules
