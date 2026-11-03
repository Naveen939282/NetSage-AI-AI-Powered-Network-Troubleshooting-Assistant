"""Deterministic evidence-matching helpers for the correlation engine.

Small, explainable concept/sentiment vocabulary. No LLM is used here.
"""
from __future__ import annotations

import re

# Concept identifiers
GATEWAY, ROUTE, VLAN, ACL, IP = "gateway", "route", "vlan", "acl", "ip"
DHCP, NAT, WIRELESS, DNS, INTERFACE, GENERAL = "dhcp", "nat", "wireless", "dns", "interface", "general"

_RULE_KEYWORDS = [
    ("gateway", GATEWAY), ("vlan", VLAN), ("acl", ACL), ("dhcp", DHCP),
    ("nat", NAT), ("wireless", WIRELESS), ("ssid", WIRELESS),
    ("next_hop", ROUTE), ("next-hop", ROUTE), ("route", ROUTE), ("routing", ROUTE),
    ("interface", INTERFACE), ("dns", DNS), ("duplicate_ip", IP),
    ("invalid_ip", IP), ("subnet_mask", IP), ("invalid_subnet", IP),
]

# concept -> (required, absent-sentiment, problematic-sentiment)
_AI_PROBE = {
    GATEWAY: (["gateway", "default gateway"],
              ["gateway is missing", "no gateway", "no default gateway", "default gateway missing"],
              ["outside", "invalid gateway", "gateway outside"]),
    ROUTE: (["route", "routing", "next-hop", "next_hop"],
            ["route is missing", "no route", "no default route", "missing default route",
             "default route is missing", "default route missing"],
            ["invalid next-hop", "invalid next hop", "next-hop unreachable"]),
    VLAN: (["vlan"],
           ["vlan missing", "no vlan", "vlan is missing", "vlan is absent", "not present", "vlan not present"],
           ["mismatch", "problem", "issue", "incorrect", "wrong", "misconfiguration"]),
    ACL: (["acl", "access list", "access-list"],
          ["no acl", "no access list", "no access-list"], ["deny", "blocked", "block"]),
    IP: (["ip", "address"], ["ip missing", "no ip"],
         ["duplicate ip", "duplicate address", "invalid ip", "invalid subnet mask"]),
    DHCP: (["dhcp"], ["dhcp missing", "no dhcp", "no dhcp pool", "dhcp pool missing"], ["dhcp"]),
    NAT: (["nat"], ["nat missing", "no nat", "nat not configured", "no nat"], ["incomplete", "asymmetric"]),
    WIRELESS: (["wireless", "ssid"], ["no wireless"], ["unreachable", "down", "not associated", "isolated"]),
    DNS: (["dns", "resolver", "name server"], ["dns missing", "no dns", "no dns server"],
          ["unreachable", "not responding", "down"]),
    INTERFACE: (["interface", "port"], ["no interface"],
                ["down", "notconnect", "error-disabled", "err-disabled", "flapping"]),
}

_HEDGE = ["appears", "appears to", "likely", "seems", "may be", "might be", "possibly",
          "could be", "suggests", "additional evidence", "additional information",
          "cannot confirm", "can't confirm", "inconclusive", "probably"]


def rule_concept(rule_name: str) -> str:
    r = (rule_name or "").lower()
    for kw, concept in _RULE_KEYWORDS:
        if kw in r:
            return concept
    return GENERAL


def rule_sentiment(rule_name: str) -> str:
    r = (rule_name or "").lower()
    if "missing" in r:
        return "absent"
    if "exists" in r:
        return "present"
    return "problematic"


def classify_rule(rule_name: str):
    return rule_concept(rule_name), rule_sentiment(rule_name)


def is_hedged(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in _HEDGE)


def detect_ai_concepts(text: str) -> dict:
    t = (text or "").lower()
    out = {}
    for concept, (reqs, absent, problem) in _AI_PROBE.items():
        if not any(req in t for req in reqs):
            continue
        if any(p in t for p in absent):
            out[concept] = "absent"
        elif any(p in t for p in problem):
            out[concept] = "problematic"
        else:
            out[concept] = "present"
    return out


def evidence_sentiment(concept: str, norm: dict) -> str:
    """Sentiment of a concept in normalized evidence: present/absent/problematic/none."""
    routes = norm.get("routes") or {}
    if concept == ROUTE:
        return "present" if (routes.get("default_route") or routes.get("static_routes")
                            or routes.get("connected_subnets")) else "none"
    if concept == GATEWAY:
        return "present" if (routes.get("default_route") or routes.get("connected_subnets")) else "none"
    if concept == VLAN:
        return "present" if norm.get("vlan") else "none"
    if concept == ACL:
        return "present" if norm.get("acls") else "none"
    if concept == IP:
        return "present" if norm.get("arp") else "none"
    if concept == DHCP:
        return "present" if (norm.get("dhcp_pools") or norm.get("excluded_addresses")
                            or norm.get("dhcp_bindings")) else "none"
    if concept == NAT:
        ns = norm.get("nat_stats") or {}
        return "present" if (ns or norm.get("nat_rules")) else "none"
    if concept == WIRELESS:
        return "present" if norm.get("wireless_clients") else "none"
    if concept == DNS:
        return "present" if norm.get("dns_servers") else "none"
    if concept == INTERFACE:
        return "present" if (norm.get("interface_status") or norm.get("ip_brief")) else "none"
    return "none"


def ai_claim_for(concept: str, text: str) -> str:
    probe = _AI_PROBE.get(concept)
    reqs = probe[0] if probe else [concept]
    sentences = []
    for s in re.split(r"[.!?]+", text or ""):
        s = s.strip()
        if s and any(r in s.lower() for r in reqs):
            sentences.append(s)
    return (sentences[0] + ".") if sentences else (text or "").strip()[:120]
