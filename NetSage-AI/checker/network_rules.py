"""Network-level rules facade (public entry point for the checker layer).

``run_network_rules`` is the single entry point used by the Streamlit app and
the test harness.  It delegates to the focused rule modules (a fixed registry),
runs each against the same ``case``, and merges their findings into one list.

Runners isolate per-module exceptions so a single failing module can never
abort the whole diagnostic pass.
"""
from __future__ import annotations

from checker import (
    vlan_rules,
    ip_rules,
    gateway_rules,
    routing_rules,
    acl_rules,
    dhcp_rules,
    interface_rules,
    nat_rules,
)

# Ordered registry of (module_name, runner) pairs.  Adding a new rule module
# only requires appending to this list.
_RULE_RUNNERS = [
    ("vlan", vlan_rules.run_vlan_rules),
    ("ip", ip_rules.run_ip_rules),
    ("gateway", gateway_rules.run_gateway_rules),
    ("routing", routing_rules.run_routing_rules),
    ("acl", acl_rules.run_acl_rules),
    ("dhcp", dhcp_rules.run_dhcp_rules),
    ("interface", interface_rules.run_interface_rules),
    ("nat", nat_rules.run_nat_rules),
]


def run_network_rules(case) -> dict:
    """Run every registered rule module on ``case`` and merge findings.

    Returns ``{"status": "PASS"|"FAIL", "findings": [...merged...]}``.
    """
    findings = []
    for module_name, runner in _RULE_RUNNERS:
        try:
            result = runner(case)
        except Exception:
            # A failing module must not break the overall diagnostic pass.
            continue
        if isinstance(result, dict) and result.get("findings"):
            for finding in result["findings"]:
                entry = dict(finding)
                entry.setdefault("module", module_name)
                findings.append(entry)
    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}


# Backwards-compatible alias used by older callers / tests.
run_all_rules = run_network_rules

