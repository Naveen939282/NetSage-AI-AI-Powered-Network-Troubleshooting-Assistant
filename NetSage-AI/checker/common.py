from __future__ import annotations

def make_result(status: str, rule: str, severity: str, message: str, evidence: str = "", details: dict | None = None) -> dict:
    return {
        "status": status,
        "rule": rule,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "details": details or {},
    }
