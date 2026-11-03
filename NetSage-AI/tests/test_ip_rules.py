from utils.csv_loader import case_by_id
from checker.ip_rules import run_ip_rules


def test_invalid_subnet_mask_negative():
    # None of the provided cases have invalid masks, so ensure no false positives
    case = case_by_id("NETSAGE-001")
    res = run_ip_rules(case)
    rules = [f["rule"] for f in res.get("findings", [])]
    assert "INVALID_SUBNET_MASK" not in rules


def test_duplicate_ip_detection_synthetic():
    # Create a synthetic Case-like object
    from utils.csv_loader import Case

    so = """
show ip arp
Internet  192.168.1.10     0   001b.638a.0101   ARPA   Vlan10
Internet  192.168.1.10     0   001b.638a.0102   ARPA   Vlan10
"""
    case = Case(case_id="SYN-001", category="VLAN", title="dup",
                symptom="", topology="", show_output=so,
                expected_fault="", osi_layer="Layer 2", concept="", severity="LOW",
                expected_command="", expected_fix="")
    res = run_ip_rules(case)
    rules = [f["rule"] for f in res.get("findings", [])]
    assert "DUPLICATE_IP" in rules
