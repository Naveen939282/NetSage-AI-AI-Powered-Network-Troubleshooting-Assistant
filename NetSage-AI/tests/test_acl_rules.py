from utils.csv_loader import case_by_id
from checker.acl_rules import run_acl_rules


def test_acl_deny_detection():
    case = case_by_id("NETSAGE-022")
    res = run_acl_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "ACL_DENY" in rules


def test_acl_insufficient_evidence():
    # A case with no ACL output should be INSUFFICIENT_EVIDENCE or PASS
    case = case_by_id("NETSAGE-001")
    res = run_acl_rules(case)
    # Should not falsely report deny
    rules = [f["rule"] for f in res.get("findings", [])]
    assert "ACL_DENY" not in rules
