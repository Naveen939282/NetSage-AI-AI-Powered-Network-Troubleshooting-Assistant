from __future__ import annotations
import ipaddress

from checker.common import make_result
from checker import normalize


def run_routing_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)
    routes = {}
    if "show ip route" in sections:
        routes = normalize._parse_routes("\n".join(sections["show ip route"]))

    # Missing default route
    if not routes.get("default_route"):
        findings.append(make_result("FAIL", "DEFAULT_ROUTE_MISSING", "HIGH",
                                    "No default route present in routing table", evidence=so))
    else:
        # Validate static next-hops are reachable
        connected = routes.get("connected_subnets", [])
        for s in routes.get("static_routes", []):
            nh = s.get("next_hop")
            try:
                nh_ip = ipaddress.ip_address(nh)
            except Exception:
                findings.append(make_result("FAIL", "INVALID_NEXT_HOP", "HIGH",
                                            f"Invalid next-hop IP: {nh}", evidence=nh))
                continue
            reachable = False
            for c in connected:
                try:
                    net = ipaddress.ip_network(c["network"], strict=False)
                    if nh_ip in net:
                        reachable = True
                        break
                except Exception:
                    continue
            if not reachable:
                findings.append(make_result("FAIL", "INVALID_NEXT_HOP", "HIGH",
                                            f"Next-hop {nh} for route {s.get('network')} is not in any connected subnet",
                                            evidence=str(s), details={"connected": connected}))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

