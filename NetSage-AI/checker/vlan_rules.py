from __future__ import annotations
import re

from checker.common import make_result
from checker import normalize


def _parse_access_mode_vlan(section_lines: list[str]) -> dict:
    # Return mapping iface -> access vlan
    mapping = {}
    text = "\n".join(section_lines)
    # look for blocks like 'Name : Gi0/2' then lines with 'Access Mode VLAN : 10'
    blocks = re.split(r"\n(?=Name\s+: )", text)
    for b in blocks:
        m = re.search(r"Name\s+:\s*(\S+)", b)
        if m:
            iface = m.group(1)
            m2 = re.search(r"Access Mode VLAN\s*:\s*(\d+)", b)
            if m2:
                mapping[iface] = m2.group(1)
    return mapping


def run_vlan_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)

    vlan_brief = {}
    if "show vlan brief" in sections:
        vlan_brief = normalize._parse_vlan_brief("\n".join(sections["show vlan brief"]))

    # Missing VLAN detection: if an interface is configured for VLAN X but VLAN X absent
    if "show interfaces switchport" in sections:
        mapping = _parse_access_mode_vlan(sections["show interfaces switchport"])
        for iface, av in mapping.items():
            if av not in vlan_brief:
                findings.append(make_result("FAIL", "MISSING_VLAN", "HIGH",
                                            f"Interface {iface} assigned to VLAN {av} but VLAN {av} missing from database",
                                            evidence=str({iface: av}), details={"vlan": av, "interface": iface}))

    # Trunk allowed VLANs check
    if "show interfaces trunk" in sections and vlan_brief:
        text = "\n".join(sections["show interfaces trunk"]) if sections.get("show interfaces trunk") else ""
        m = re.search(r"Vlans Allowed on Trunk\s*(.*)$", text, re.IGNORECASE | re.MULTILINE)
        if m:
            allowed = m.group(1).strip()
            # allowed might be like '10,20' or '10-20'
            allowed_set = set()
            for part in re.split(r",|\s+", allowed):
                part = part.strip().strip(',')
                if not part:
                    continue
                if "-" in part:
                    a, b = part.split("-")
                    for i in range(int(a), int(b) + 1):
                        allowed_set.add(str(i))
                else:
                    # may be comma-separated list
                    for v in part.split(','):
                        if v:
                            allowed_set.add(v)
            # any VLAN in vlan_brief but not in allowed_set reported as missing on trunk
            for vid in vlan_brief:
                if vid not in allowed_set:
                    # only report if VLAN has ports (meaning intended to be used)
                    if vlan_brief[vid].get("ports"):
                        findings.append(make_result("FAIL", "TRUNK_VLAN_NOT_ALLOWED", "MEDIUM",
                                                    f"VLAN {vid} present but not allowed on trunk", evidence=vid,
                                                    details={"allowed": sorted(list(allowed_set))}))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

