from __future__ import annotations
import re

from checker.common import make_result
from checker import normalize


def run_nat_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)

    # Basic NAT presence
    if "show ip nat statistics" in sections:
        text = "\n".join(sections["show ip nat statistics"]) or ""
        if "Total translations: 0" in text:
            findings.append(make_result("FAIL", "NAT_MISSING", "HIGH",
                                        "No NAT translations present; NAT may be missing", evidence=text))

    # Check running-config for ip nat inside/outside pairs
    if "show running-config | section interface" in sections:
        cfg = "\n".join(sections["show running-config | section interface"]) or ""
        ins = re.search(r"ip nat inside", cfg)
        out = re.search(r"ip nat outside", cfg)
        if ins and out:
            # ok
            pass
        else:
            findings.append(make_result("FAIL", "NAT_INTERFACE_MISSING", "HIGH",
                                        "ip nat inside/outside not configured on interfaces as expected", evidence=cfg))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}
