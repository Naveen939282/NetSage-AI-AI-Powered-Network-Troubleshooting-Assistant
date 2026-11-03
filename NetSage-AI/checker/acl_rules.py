from __future__ import annotations
import re

from checker.common import make_result


def run_acl_rules(case) -> dict:
    findings = []
    so = case.show_output or ""
    # Look for 'access-list' and 'deny' keywords
    if "access-list" in so or "access lists" in so or "access-lists" in so:
        # Find deny lines
        denies = re.findall(r"^\s*\d+\s+deny\s+.+$", so, flags=re.IGNORECASE | re.MULTILINE)
        if denies:
            findings.append(make_result("FAIL", "ACL_DENY", "HIGH",
                                        f"ACL contains deny statements: {len(denies)} found",
                                        evidence="; ".join(denies)))
    # Also find explicit 'deny' tokens in 'show access-lists' blocks
    acl_blocks = re.findall(r"show access-lists[\s\S]*?(?=\n\s*\n|$)", so, flags=re.IGNORECASE)
    for blk in acl_blocks:
        if re.search(r"\bdeny\b", blk, flags=re.IGNORECASE):
            if not any(f for f in findings if f.get("rule") == "ACL_DENY"):
                findings.append(make_result("FAIL", "ACL_DENY", "HIGH", "ACL deny found", evidence=blk))

    status = "PASS" if not findings else "FAIL"
    return {"status": status, "findings": findings}

