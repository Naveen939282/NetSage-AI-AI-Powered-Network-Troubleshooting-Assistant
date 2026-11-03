"""Evidence normalization for NetSage-AI.

Transforms the free-text ``show_output`` field of a case into a structured
dictionary of network facts (VLANs, interfaces, routes, ACLs, DHCP, ARP,
NAT, DNS, OSPF, wireless).  Both the deterministic rule checker and the AI
diagnosis provider consume this normalized evidence.

A line is treated as a section header when, after stripping an optional
``hostname#``/``hostname>`` prompt, the remainder begins with ``show``.
"""
from __future__ import annotations

import re
import ipaddress

_IPV4_RE = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
_ROUTE_NET_RE = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})")

_STATUS_WORDS = {"connected", "notconnect", "disabled", "err-disabled",
                 "notpresent", "inactive", "unmanaged", "monitoring"}


def split_sections(show_output: str) -> dict:
    """Return {section_name: [body_lines...]} keyed by lowercased command."""
    sections: dict = {}
    current: list | None = None
    for raw in show_output.splitlines():
        line = raw.rstrip()
        key = _section_key(line)
        if key is not None:
            current = []
            sections[key] = current
        elif current is not None:
            current.append(line.strip())
    return sections


def _section_key(line: str) -> str | None:
    s = line.strip()
    for sep in ("#", ">"):
        idx = s.rfind(sep)
        if idx != -1 and idx < 50:
            rem = s[idx + 1:].strip()
            if rem.lower().startswith("show"):
                return rem.lower()
    if s.lower().startswith("show"):
        return s.lower()
    return None


def _ip_token(token: str) -> str | None:
    m = re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", token)
    return token if m else None


def _net_key(ip: str, prefix: int) -> str | None:
    try:
        return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False))
    except ValueError:
        return None


def _net_from_cidr(cidr: str) -> str | None:
    try:
        return str(ipaddress.ip_network(cidr, strict=False))
    except ValueError:
        return None


def _parse_vlan_brief(text: str) -> dict:
    vlans: dict = {}
    data = [ln for ln in text.splitlines()
            if ln.strip() and not ln.strip().startswith("----")]
    for line in data:
        tokens = line.split()
        try:
            int(tokens[0])
        except (ValueError, IndexError):
            continue
        vid = tokens[0]
        vlans[vid] = {"name": tokens[1] if len(tokens) > 1 else "",
                      "status": tokens[2] if len(tokens) > 2 else "",
                      "ports": tokens[3:]}
    return vlans


def _parse_interfaces_status(text: str) -> dict:
    interfaces: dict = {}
    for line in text.splitlines():
        tokens = line.split()
        if not tokens or not re.match(r"^[A-Za-z]", tokens[0]):
            continue
        iface = tokens[0]
        status = None
        status_idx = None
        for i, t in enumerate(tokens):
            if t.lower() in _STATUS_WORDS:
                status_idx = i
                status = t.lower()
                break
        if status is None:
            continue
        vlan = tokens[status_idx + 1] if status_idx + 1 < len(tokens) else ""
        admin = "down" if status in ("notconnect", "disabled") else "up"
        oper = "down" if status in ("notconnect", "disabled",
                                    "err-disabled") else "up"
        interfaces[iface] = {"admin_status": admin, "oper_status": oper,
                             "vlan": vlan, "raw_status": status}
    return interfaces


def _parse_ip_brief(text: str) -> list:
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 6 or not re.match(r"^[A-Za-z]", tokens[0]):
            continue
        ip = _ip_token(tokens[1])
        if not ip:
            continue
        tail = " ".join(tokens[4:])
        if "administratively down" in tail or " down" in tail:
            admin, oper = "down", "down"
        else:
            admin, oper = "up", "up"
        rows.append({"interface": tokens[0], "ip": ip,
                     "admin_status": admin, "oper_status": oper})
    return rows


def _parse_show_interface(text: str) -> dict:
    result: dict = {}
    for line in text.splitlines():
        m = re.match(
            r"^(\S+)\s+is\s+(administratively down|up|down),\s+line protocol is\s+(\w+)",
            line.strip())
        if m:
            iface = m.group(1)
            admin = "down" if m.group(2) == "administratively down" else m.group(2)
            result[iface] = {"admin_status": admin, "oper_status": m.group(3)}
    return result


def _parse_ip_interface(text: str) -> list:
    rows = []
    cur = None
    for line in text.splitlines():
        if re.match(r"^\S+\s+is\s+\w", line) and "Internet address" not in line:
            cur = line.split()[0]
        m = re.search(r"Internet address is\s+([\d.]+)\s*/\s*(\d+)", line)
        if m and cur:
            rows.append({"interface": cur, "ip": m.group(1),
                         "prefix": int(m.group(2))})
    return rows


def _parse_routes(text: str) -> dict:
    connected, statics, default = [], [], None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _ROUTE_NET_RE.search(s)
        if not m:
            continue
        net = m.group(1)
        if "directly connected" in s or "is connected" in s:
            iface_m = re.search(r"connected,\s+(\S+)", s)
            connected.append({"network": net,
                              "interface": iface_m.group(1) if iface_m else ""})
        elif "via" in s:
            nh_m = re.search(r"via\s+([\d.]+)", s)
            nh = nh_m.group(1) if nh_m else ""
            if net == "0.0.0.0/0" or s.startswith("S*"):
                default = {"next_hop": nh}
            else:
                statics.append({"network": net, "next_hop": nh})
    return {"connected_subnets": connected, "static_routes": statics,
            "default_route": default}




def _parse_acls(text: str) -> list:
    acls, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*(Standard|Extended) IP access list\s+(\S+)", line)
        if m:
            cur = m.group(2)
            continue
        m = re.match(r"^\s*(\d+)\s+(deny|permit)\s+(\S+)(?:\s+(.*))?$", line)
        if m and cur:
            rest = (m.group(4) or "").split()
            acls.append({"name": cur, "seq": m.group(1), "action": m.group(2),
                         "protocol": m.group(3),
                         "src": rest[0] if rest else "any",
                         "src_wildcard": rest[1] if len(rest) > 1 else "any",
                         "dst": rest[2] if len(rest) > 2 else "any",
                         "dst_wildcard": rest[3] if len(rest) > 3 else "any"})
    return acls


def _parse_acl_interfaces(text: str) -> list:
    applied, cur = [], None
    for line in text.splitlines():
        if line and not line[0].isspace():
            cur = line.strip()
            applied.append({"interface": cur, "in": None, "out": None})
        elif cur:
            if "Inbound access list" in line:
                v = line.split(":", 1)[1].strip() if ":" in line else ""
                if v and v != "not set":
                    applied[-1]["in"] = v
            elif "Outbound access list" in line:
                v = line.split(":", 1)[1].strip() if ":" in line else ""
                if v and v != "not set":
                    applied[-1]["out"] = v
    return applied


def _parse_dhcp_pool(text: str) -> list:
    pools = []
    for line in text.splitlines():
        m = re.match(r"Pool\s+(\S+):\s+(\S+)\s+(\S+)\s+used\s+(\d+)\s+free\s+(\d+)", line)
        if m:
            rng = m.group(3)
            first, last = (rng.split("-") if "-" in rng else (rng, rng))
            pools.append({"name": m.group(1), "network": m.group(2),
                          "first": first, "last": last,
                          "used": int(m.group(4)), "free": int(m.group(5))})
    return pools


def _parse_excluded(text: str) -> list:
    out = []
    for line in text.splitlines():
        m = re.match(r"([\d.]+)\s*-\s*([\d.]+)", line.strip())
        if m:
            out.append({"start": m.group(1), "end": m.group(2)})
    return out


def _parse_dhcp_bindings(text: str) -> list:
    out = []
    for line in text.splitlines():
        t = line.split()
        if len(t) >= 2 and _ip_token(t[0]) and re.match(r"^[0-9a-fA-F]{4}\.", t[1]):
            out.append({"ip": t[0], "mac": t[1]})
    return out


def _parse_arp(text: str) -> list:
    out = []
    for line in text.splitlines():
        m = re.match(r"Internet\s+([\d.]+)\s+\S+\s+([\da-fA-F.]+)\s+(\S+)\s+(\S+)", line)
        if m:
            out.append({"ip": m.group(1), "mac": m.group(2),
                        "type": m.group(3), "interface": m.group(4)})
    return out


def _parse_dns(text: str) -> list:
    servers = []
    lines = text.splitlines()
    follow = False
    for line in lines:
        low = line.lower()
        if "name-server" in low:
            servers.extend(_IPV4_RE.findall(line))
            follow = False
            continue
        if "dns server" in low or "dns servers" in low:
            servers.extend(_IPV4_RE.findall(line))
            follow = True
            continue
        if follow:
            if not line.strip():
                break
            servers.extend(_IPV4_RE.findall(line))
    return servers


def _wildmask_to_prefix(mask: str):
    try:
        return 32 - sum(bin(int(x)).count("1") for x in mask.split("."))
    except Exception:
        return None


def _parse_nat_stats(text: str) -> dict:
    out = {"total": 0, "active": 0}
    for line in text.splitlines():
        m = re.search(r"Total translations:\s+(\d+)", line)
        if m:
            out["total"] = int(m.group(1))
        m = re.search(r"Active translations:\s+(\d+)", line)
        if m:
            out["active"] = int(m.group(1))
    return out


def _parse_ospf(text: str) -> dict:
    out = {"neighbors": [], "routes": []}
    for line in text.splitlines():
        m = re.match(r"^(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\S+)\s+\d+\s+(\S+)", line)
        if m:
            out["neighbors"].append({"id": m.group(1), "state": m.group(2),
                                     "interface": m.group(3)})
    return out


def _parse_wireless(text: str) -> list:
    clients = []
    for line in text.splitlines():
        m = re.match(r"([\da-fA-F.:]+)\s+[\d.]+\s+\d+\s+(\S+)\s+(\d+)\s+(\d+)", line)
        if m:
            clients.append({"mac": m.group(1), "ssid": m.group(2),
                            "vlan": m.group(3), "rssi": m.group(4)})
    return clients



def _parse_running_config(text: str) -> dict:
    """Lightweight structure of a show running-config."""
    static_routes = []
    nat_rules = []
    interfaces = {}
    cur_iface = None
    for raw in text.splitlines():
        s = raw.strip()
        m = re.match(r"^interface\s+(\S+)", s)
        if m:
            cur_iface = m.group(1)
            interfaces[cur_iface] = {"ip": None, "prefix": None,
                                     "nat": None, "shutdown": False}
            continue
        if cur_iface:
            if s == "shutdown":
                interfaces[cur_iface]["shutdown"] = True
            m = re.match(r"ip address\s+([\d.]+)\s+([\d.]+)", s)
            if m:
                interfaces[cur_iface]["ip"] = m.group(1)
                interfaces[cur_iface]["prefix"] = _wildmask_to_prefix(m.group(2))
            m = re.match(r"ip nat (\w+)", s)
            if m:
                interfaces[cur_iface]["nat"] = m.group(1)
        m = re.match(r"ip route\s+(\S+)\s+(\S+)\s+([\d.]+)", s)
        if m:
            static_routes.append({"network": m.group(1), "mask": m.group(2),
                                  "next_hop": m.group(3)})
            continue
        m = re.search(r"ip route 0\.0\.0\.0\s+0\.0\.0\.0\s+([\d.]+)", s)
        if m:
            static_routes.append({"network": "0.0.0.0", "mask": "0.0.0.0",
                                  "next_hop": m.group(1)})
        m = re.search(r"ip nat inside source (.*)", s)
        if m:
            nat_rules.append(m.group(1).strip())
    return {"interfaces": interfaces, "static_routes": static_routes,
            "nat": nat_rules}


def normalize_show_output(show_output: str) -> dict:
    """Aggregate every parser into one structured evidence dict."""
    sections = split_sections(show_output)

    def body(key):
        return "\n".join(sections.get(key, []))

    rc = _parse_running_config(body("show running-config"))
    evidence = {
        "raw_sections": list(sections.keys()),
        "vlan": _parse_vlan_brief(body("show vlan brief")),
        "interface_status": _parse_interfaces_status(body("show interfaces status")),
        "ip_brief": _parse_ip_brief(body("show ip interface brief")),
        "interface_detail": _parse_show_interface(body("show interfaces")),
        "ip_interfaces": _parse_ip_interface(body("show ip interface")),
        "routes": _parse_routes(body("show ip route")),
        "static_routes_cfg": rc["static_routes"],
        "interfaces_cfg": rc["interfaces"],
        "nat_rules": rc["nat"],
        "acls": _parse_acls(body("show ip access-lists")),
        "acl_interfaces": _parse_acl_interfaces(body("show running-config | section interface")),
        "dhcp_pools": _parse_dhcp_pool(body("show ip dhcp pool")),
        "excluded_addresses": _parse_excluded(body("show ip dhcp excluded-address")),
        "dhcp_bindings": _parse_dhcp_bindings(body("show ip dhcp binding")),
        "arp": _parse_arp(body("show ip arp")),
        "dhcp_snooping": _parse_arp(body("show ip dhcp snooping")),
        "dns_servers": _parse_dns(body("show ip dns") + "\n" + body("show running-config")),
        "nat_stats": _parse_nat_stats(body("show ip nat statistics")),
        "ospf": _parse_ospf(body("show ip ospf neighbor")),
        "wireless_clients": _parse_wireless(body("show wireless client mac-address")),
    }
    return evidence
