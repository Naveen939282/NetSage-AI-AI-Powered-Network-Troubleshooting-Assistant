"""Deterministic correlation of AI diagnosis, rule findings and evidence."""
from __future__ import annotations

from checker import normalize as _norm
from correlation.schemas import CorrelationResult
from correlation import evidence_matcher as em

_DIAG_ATTRS = ("root_cause", "reasoning_summary", "next_command", "osi_layer", "severity")
_BASE = {"AGREEMENT": 0.9, "PARTIAL_AGREEMENT": 0.55, "CONFLICT": 0.25, "INSUFFICIENT_EVIDENCE": 0.30}


def _diag_text(diag):
    p = [str(getattr(diag, a)) for a in _DIAG_ATTRS if getattr(diag, a, None)]
    p += [str(e) for e in (getattr(diag, "evidence", None) or [])]
    p += [str(s) for s in (getattr(diag, "fix_steps", None) or [])]
    return " . ".join(p).lower()


def _so(case):
    return case.show_output or "" if hasattr(case, "show_output") else case.get("show_output", "")


def correlate(case, rule_findings, ai_diagnosis):
    """Return a CorrelationResult, or None when ai_diagnosis is None."""
    if ai_diagnosis is None:
        return None
    rule_findings = list(rule_findings or [])
    norm = _norm.normalize_show_output(_so(case))
    ai_text = _diag_text(ai_diagnosis)
    hedged = em.is_hedged(ai_text)

    by_concept = {}
    for f in rule_findings:
        rn = f.get("rule", "") if isinstance(f, dict) else ""
        c, s = em.classify_rule(rn)
        by_concept.setdefault(c, {"sentiment": s, "finding": f})
    ai = em.detect_ai_concepts(ai_text)

    shared = [c for c in by_concept if c in ai]
    rule_only = [c for c in by_concept if c not in ai]
    ai_only = [c for c in ai if c not in by_concept]
    supported, unsupported, conflicts, matches, missing = [], [], [], [], []

    for c in shared:
        rs, ais = by_concept[c]["sentiment"], ai[c]
        claim = em.ai_claim_for(c, ai_text)
        fnd = by_concept[c]["finding"]
        name = fnd.get("rule", "") if isinstance(fnd, dict) else ""
        if ais == rs:
            supported.append(f"AI claim '{claim}' aligns with rule {name}.")
        else:
            conflicts.append({"concept": c, "rule_finding": name, "rule_sentiment": rs,
                              "ai_claim": claim, "ai_sentiment": ais,
                              "explanation": f"Rule indicates {rs} for {c}, but AI indicates {ais}."})

    for c in ai_only:
        ais, claim = ai[c], em.ai_claim_for(c, ai_text)
        ev = em.evidence_sentiment(c, norm)
        if ev == "none":
            unsupported.append(f"AI claim '{claim}' (concept {c}) is not backed by any rule finding or evidence.")
            missing.append(f"No {c} evidence found in show output for AI claim '{claim}'.")
        elif ais == ev:
            matches.append(f"Evidence supports AI claim '{claim}' (concept {c}).")
            supported.append(f"AI claim '{claim}' supported by evidence (concept {c}).")
        else:
            conflicts.append({"concept": c, "rule_finding": "", "rule_sentiment": ev,
                              "ai_claim": claim, "ai_sentiment": ais,
                              "explanation": f"Evidence indicates {ev} for {c}, but AI indicates {ais}."})

    for c in rule_only:
        fnd = by_concept[c]["finding"]
        missing.append(f"AI did not address rule concept '{c}' (rule {fnd.get('rule', '') if isinstance(fnd, dict) else ''} not reflected in diagnosis).")

    hc, hs, hu, hr, he = bool(conflicts), bool(supported), bool(unsupported), bool(rule_only), bool(matches)
    if hc:
        status = "CONFLICT"
    elif not by_concept and not he:
        status = "INSUFFICIENT_EVIDENCE"
    elif hs and not hedged and not hu and not hr:
        status = "AGREEMENT"
    elif hs and (hedged or hu or hr):
        status = "PARTIAL_AGREEMENT"
    elif hu and not hs:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "PARTIAL_AGREEMENT"

    if hc:
        ai_s = "UNSUPPORTED"
    elif hs and not hu and not hedged:
        ai_s = "SUPPORTED"
    elif hs:
        ai_s = "PARTIALLY_SUPPORTED"
    elif hu:
        ai_s = "UNSUPPORTED"
    else:
        ai_s = "UNKNOWN"

    if hc:
        rule_s = "UNSUPPORTED"
    elif hs and not hr and not hedged:
        rule_s = "SUPPORTED"
    elif hs:
        rule_s = "PARTIALLY_SUPPORTED"
    elif hr and not hs:
        rule_s = "UNSUPPORTED"
    elif not by_concept:
        rule_s = "UNKNOWN"
    else:
        rule_s = "PARTIALLY_SUPPORTED"

    if status == "AGREEMENT":
        action = "ACCEPT"
    elif status == "CONFLICT":
        action = "INVESTIGATE"
    elif ai_s == "UNSUPPORTED":
        action = "EDIT"
    else:
        action = "INVESTIGATE"

    conf = round(min(1.0, max(0.0, _BASE[status] + 0.03 * len(supported) - 0.05 * len(unsupported))), 3)
    return CorrelationResult(
        correlation_status=status, confidence=conf, ai_support_level=ai_s,
        rule_support_level=rule_s, recommended_review_action=action,
        supported_claims=supported, unsupported_claims=unsupported, conflicts=conflicts,
        evidence_matches=matches, missing_evidence=missing, requires_human_review=True)
