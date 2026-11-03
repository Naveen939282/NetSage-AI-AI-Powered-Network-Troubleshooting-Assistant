"""Tests for the network_rules facade that aggregates all rule modules."""
import checker.network_rules as nr
from utils.csv_loader import case_by_id, Case
from checker.network_rules import run_network_rules, run_all_rules

# A small, healthy multi-section show output that satisfies every rule module:
# a default route whose next-hop lives in a connected subnet, plus a matching
# DHCP pool so dhcp_rules does not flag a missing pool.
HEALTHY_SHOW = """\
R1#show ip route
S*   0.0.0.0/0 [1/0] via 10.0.0.254
C    10.0.0.0/24 is directly connected, Ethernet0/0
R1#show ip dhcp pool
Pool LAN: 10.0.0.0/24
"""


def _synth(show_output):
    return Case(case_id="SYN", category="Test", title="t",
                symptom="", topology="", show_output=show_output,
                expected_fault="", osi_layer="Layer 3", concept="",
                severity="LOW", expected_command="", expected_fix="")


def test_facade_returns_merged_findings_from_real_case():
    case = case_by_id("NETSAGE-002")  # VLAN-creation fault -> MISSING_VLAN
    res = run_network_rules(case)
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "MISSING_VLAN" in rules
    # every merged finding carries its source module
    assert all("module" in f for f in res["findings"])


def test_facade_alias_is_present():
    assert run_all_rules is run_network_rules


def test_facade_healthy_case_is_pass():
    res = run_network_rules(_synth(HEALTHY_SHOW))
    assert res["status"] == "PASS"
    assert res["findings"] == []


def test_facade_empty_case_flags_missing_defaults():
    # No routing evidence at all -> gateway + routing modules both fire, and the
    # facade merges findings from multiple modules with module annotations.
    res = run_network_rules(_synth(""))
    assert res["status"] == "FAIL"
    rules = [f["rule"] for f in res["findings"]]
    assert "DEFAULT_GATEWAY_MISSING" in rules
    assert "DEFAULT_ROUTE_MISSING" in rules
    assert all("module" in f and f["module"] for f in res["findings"])


def test_facade_isolates_broken_module():
    """A runner that raises must not abort the whole aggregation."""
    case = case_by_id("NETSAGE-002")
    saved = nr._RULE_RUNNERS[:]

    def _boom(c):
        raise RuntimeError("kaboom")

    try:
        nr._RULE_RUNNERS = [("boom", _boom)] + saved
        res = run_network_rules(case)
        # the boom module is skipped, but the VLAN finding still surfaces
        assert res["status"] == "FAIL"
        rules = [f["rule"] for f in res["findings"]]
        assert "MISSING_VLAN" in rules
        assert "boom" not in [f["module"] for f in res["findings"]]
    finally:
        nr._RULE_RUNNERS = saved
