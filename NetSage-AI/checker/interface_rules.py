from __future__ import annotations
from checker.common import make_result
from checker import normalize


def run_interface_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)

    # Parse 'show interfaces status' if present
    if "show interfaces status" in sections:
        interfaces = normalize._parse_interfaces_status("\n".join(sections["show interfaces status"]))
        for iface, info in interfaces.items():
            if info.get("admin_status") == "down":
                findings.append(make_result("FAIL", "INTERFACE_ADMIN_DOWN", "HIGH",
                                            f"Interface {iface} administratively down", evidence=str(info)))
            elif info.get("oper_status") == "down":
                findings.append(make_result("FAIL", "INTERFACE_OPER_DOWN", "MEDIUM",
                                            f"Interface {iface} operationally down", evidence=str(info)))

    # Parse 'show ip interface brief' which may show administratively down states
    if "show ip interface brief" in sections:
        ipbrief = normalize._parse_ip_brief("\n".join(sections["show ip interface brief"]))
        for row in ipbrief:
            if row.get("admin_status") == "down":
                findings.append(make_result("FAIL", "INTERFACE_ADMIN_DOWN", "HIGH",
                                            f"Interface {row.get('interface')} administratively down", evidence=str(row)))
            elif row.get("oper_status") == "down":
                findings.append(make_result("FAIL", "INTERFACE_OPER_DOWN", "MEDIUM",
                                            f"Interface {row.get('interface')} operationally down", evidence=str(row)))

    # Parse 'show interfaces' detailed if present
    if "show interfaces" in sections:
        parsed = normalize._parse_show_interface("\n".join(sections["show interfaces"]))
        for iface, info in parsed.items():
            if info.get("admin_status") == "down":
                findings.append(make_result("FAIL", "INTERFACE_ADMIN_DOWN", "HIGH",
                                            f"Interface {iface} administratively down", evidence=str(info)))
            elif info.get("oper_status") in ("down", "down"):
                findings.append(make_result("FAIL", "INTERFACE_OPER_DOWN", "MEDIUM",
                                            f"Interface {iface} operationally {info.get('oper_status')}", evidence=str(info)))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

