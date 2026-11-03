from __future__ import annotations
import ipaddress

from checker.common import make_result
from checker import normalize


def run_gateway_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)
    routes = {}
    if "show ip route" in sections:
        routes = normalize._parse_routes("\n".join(sections["show ip route"]))

    default = routes.get("default_route")
    connected = routes.get("connected_subnets", [])

    if default is None:
        findings.append(make_result("FAIL", "DEFAULT_GATEWAY_MISSING", "HIGH",
                                    "No default route found in routing table.", evidence=so))
        return {"status": "FAIL", "findings": findings}

    gw = default.get("next_hop")
    if not gw:
        findings.append(make_result("INSUFFICIENT_EVIDENCE", "GATEWAY_UNKNOWN", "INFO",
                                    "Default route exists but next-hop could not be parsed.", evidence=so))
        return {"status": "INSUFFICIENT_EVIDENCE", "findings": findings}

    # Check if gateway is in any connected subnet
    try:
        gw_ip = ipaddress.ip_address(gw)
    except Exception:
        findings.append(make_result("FAIL", "INVALID_GATEWAY", "HIGH",
                                    f"Default gateway IP is invalid: {gw}", evidence=gw))
        return {"status": "FAIL", "findings": findings}

    in_subnet = False
    for c in connected:
        try:
            net = ipaddress.ip_network(c["network"], strict=False)
            if gw_ip in net:
                in_subnet = True
                break
        except Exception:
            continue

    if not in_subnet:
        findings.append(make_result("FAIL", "GATEWAY_OUTSIDE_SUBNET", "HIGH",
                                    f"Default gateway {gw} is outside connected subnets.", evidence=so,
                                    details={"gateway": gw, "connected_subnets": connected}))
        return {"status": "FAIL", "findings": findings}

    return {"status": "PASS", "findings": findings}

