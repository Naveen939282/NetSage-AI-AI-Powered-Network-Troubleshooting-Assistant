"""Tests for the deterministic evidence-matching helpers."""
from correlation import evidence_matcher as em


def _norm(routes=None, vlan=None, acls=None, arp=None, nat_stats=None, nat_rules=None,
          wireless_clients=None, dns_servers=None, interface_status=None, ip_brief=None,
          dhcp_pools=None, excluded_addresses=None, dhcp_bindings=None):
    return {
        "routes": routes or {}, "vlan": vlan or {}, "acls": acls or {}, "arp": arp or {},
        "nat_stats": nat_stats or {}, "nat_rules": nat_rules or [],
        "wireless_clients": wireless_clients or [], "dns_servers": dns_servers or [],
        "interface_status": interface_status or {}, "ip_brief": ip_brief or [],
        "dhcp_pools": dhcp_pools or {}, "excluded_addresses": excluded_addresses or {},
        "dhcp_bindings": dhcp_bindings or {},
    }


def test_rule_concept_mapping():
    assert em.rule_concept("DEFAULT_GATEWAY_MISSING") == "gateway"
    assert em.rule_concept("GATEWAY_OUTSIDE_SUBNET") == "gateway"
    assert em.rule_concept("DEFAULT_ROUTE_MISSING") == "route"
    assert em.rule_concept("INVALID_NEXT_HOP") == "route"
    assert em.rule_concept("VLAN_MISMATCH") == "vlan"
    assert em.rule_concept("MISSING_VLAN") == "vlan"
    assert em.rule_concept("ACL_DENY") == "acl"
    assert em.rule_concept("DUPLICATE_IP") == "ip"
    assert em.rule_concept("MISSING_DHCP_POOL") == "dhcp"
    assert em.rule_concept("NAT_INTERFACE_MISSING") == "nat"
    assert em.rule_concept("INTERFACE_OPER_DOWN") == "interface"
    assert em.rule_concept("UNKNOWN_RULE") == "general"


def test_rule_sentiment():
    assert em.rule_sentiment("DEFAULT_GATEWAY_MISSING") == "absent"
    assert em.rule_sentiment("DEFAULT_ROUTE_EXISTS") == "present"
    assert em.rule_sentiment("VLAN_MISMATCH") == "problematic"
    assert em.rule_sentiment("ACL_DENY") == "problematic"


def test_classify_rule_combo():
    concept, sentiment = em.classify_rule("MISSING_DHCP_POOL")
    assert concept == "dhcp" and sentiment == "absent"


def test_is_hedged():
    assert em.is_hedged("VLAN configuration appears problematic.")
    assert em.is_hedged("The root cause is likely a routing issue.")
    assert not em.is_hedged("Default gateway is outside the host subnet.")


def test_detect_ai_concepts():
    assert em.detect_ai_concepts("Default gateway is outside the host subnet.").get("gateway") == "problematic"
    assert em.detect_ai_concepts("Default route is missing.").get("route") == "absent"
    assert em.detect_ai_concepts("VLAN configuration appears problematic.").get("vlan") == "problematic"
    assert em.detect_ai_concepts("The switch rebooted.") == {}


def test_claim_extraction():
    text = "Default route is missing here. Other noise."
    assert "route" in em.ai_claim_for("route", text).lower()


def test_evidence_sentiment():
    present = _norm(routes={"default_route": {"next_hop": "10.0.0.1"},
                            "connected_subnets": [{"network": "10.0.0.0/24"}]})
    assert em.evidence_sentiment("route", present) == "present"
    assert em.evidence_sentiment("gateway", present) == "present"
    assert em.evidence_sentiment("vlan", _norm(vlan={"1": {"name": "x"}})) == "present"
    absent = _norm()
    assert em.evidence_sentiment("route", absent) == "none"
    assert em.evidence_sentiment("dns", absent) == "none"
    assert em.evidence_sentiment("unknown_concept", absent) == "none"
