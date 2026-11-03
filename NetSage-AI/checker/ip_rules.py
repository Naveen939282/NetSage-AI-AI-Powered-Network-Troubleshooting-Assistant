from __future__ import annotations
from typing import List
import re
import ipaddress

from checker.common import make_result
from checker import normalize


def _extract_ips(text: str) -> List[str]:
    return re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)


def run_ip_rules(case) -> dict:
    """Run IP-related deterministic checks.

    Returns a dict with overall status and list of findings.
    """
    findings = []
    so = case.show_output or ""
    ips = _extract_ips(so)
    # Duplicate IP detection - scan the ARP table only. A recurring network
    # address token (e.g. 10.0.0.0 appearing in both `show ip route` and
    # `show ip dhcp pool`) is not a duplicate-IP fault; the real symptom is a
    # single IP responding on two different MACs in the ARP table.
    sections = normalize.split_sections(so)
    arp = normalize._parse_arp("\n".join(sections.get("show ip arp", [])))
    arp_ips = [entry["ip"] for entry in arp]
    dup = {ip for ip in arp_ips if arp_ips.count(ip) > 1}
    if dup:
        findings.append(make_result("FAIL", "DUPLICATE_IP", "HIGH",
                                    f"Duplicate IPs detected: {', '.join(sorted(dup))}",
                                    evidence=", ".join(sorted(dup))))

    # Invalid IP tokens
    for ip in set(ips):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            findings.append(make_result("FAIL", "INVALID_IP", "HIGH",
                                        f"Invalid IP token found: {ip}", evidence=ip))

    # Invalid subnet masks: look for patterns like 255.255.255.0 in output
    masks = re.findall(r"\b(?:255|254|252|248|240|224|192|128|0)\.(?:255|254|252|248|240|224|192|128|0)\.(?:255|254|252|248|240|224|192|128|0)\.(?:255|254|252|248|240|224|192|128|0)\b", so)
    for m in set(masks):
        try:
            ipaddress.IPv4Network(f"0.0.0.0/{m}")
        except Exception:
            findings.append(make_result("FAIL", "INVALID_SUBNET_MASK", "HIGH",
                                        f"Invalid subnet mask: {m}", evidence=m))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

