from __future__ import annotations
import re

from checker.common import make_result
from checker import normalize


def run_dhcp_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    sections = normalize.split_sections(so)

    pools = []
    if "show ip dhcp pool" in sections:
        for ln in sections["show ip dhcp pool"]:
            m = re.search(r"Pool\s+(\S+):\s+(\d+\.\d+\.\d+\.\d+/\d+)", ln)
            if m:
                pools.append(m.group(2))
            else:
                # try simpler IP detection
                ipm = re.search(r"(\d+\.\d+\.\d+\.\d+/\d+)", ln)
                if ipm:
                    pools.append(ipm.group(1))

    # Check connected subnets and ensure there is a pool for them when evidence exists
    if "show ip route" in sections:
        routes = normalize._parse_routes("\n".join(sections["show ip route"]))
        for c in routes.get("connected_subnets", []):
            # If no pool matches this connected network, flag missing pool
            net = c.get("network")
            if net and all(net != p for p in pools):
                findings.append(make_result("FAIL", "MISSING_DHCP_POOL", "HIGH",
                                            f"No DHCP pool for connected subnet {net}", evidence=so,
                                            details={"subnet": net, "pools": pools}))

    # Check for excluded-address overlap: handle ranges like '192.168.20.10 - 192.168.20.15'
    if "show ip dhcp excluded-address" in sections and "show ip dhcp pool" in sections:
        excl_txt = "\n".join(sections["show ip dhcp excluded-address"]) or ""
        pooltxt = "\n".join(sections["show ip dhcp pool"]) or ""
        excl_ranges = re.findall(r"(\d+\.\d+\.\d+\.\d+)\s*-\s*(\d+\.\d+\.\d+\.\d+)", excl_txt)
        pool_ranges = re.findall(r"(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+)", pooltxt)
        # also consider single excluded IPs
        excl_singles = re.findall(r"(?m)^\s*(\d+\.\d+\.\d+\.\d+)\s*$", excl_txt)

        def ip_to_int(a: str) -> int:
            import ipaddress

            return int(ipaddress.ip_address(a))

        for e in excl_ranges:
            estart, eend = ip_to_int(e[0]), ip_to_int(e[1])
            for p in pool_ranges:
                pstart, pend = ip_to_int(p[0]), ip_to_int(p[1])
                if not (eend < pstart or estart > pend):
                    findings.append(make_result("FAIL", "DHCP_EXCLUDED_OVERLAP", "MEDIUM",
                                                f"Excluded range {e[0]}-{e[1]} overlaps pool range {p[0]}-{p[1]}",
                                                evidence=f"{e[0]}-{e[1]} vs {p[0]}-{p[1]}"))
        # single IPs
        for s in excl_singles:
            si = ip_to_int(s)
            for p in pool_ranges:
                pstart, pend = ip_to_int(p[0]), ip_to_int(p[1])
                if pstart <= si <= pend:
                    findings.append(make_result("FAIL", "DHCP_EXCLUDED_OVERLAP", "MEDIUM",
                                                f"Excluded address {s} overlaps DHCP pool range {p[0]}-{p[1]}", evidence=s))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

