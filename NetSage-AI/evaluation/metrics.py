"""Offline evaluation metrics for NetSage-AI (no network, no API keys).

Ground-truth fields (e.g. case.expected_fault) are consumed ONLY here, in
keeping with the Phase 5 isolation rule that the rest of the pipeline must
never depend on the oracle.
"""
from __future__ import annotations

from collections import defaultdict

from correlation import evidence_matcher as em
from evaluation import ground_truth as gt


def _safe_div(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def per_case_metrics(case, findings, diag, corr):
    """Compare the deterministic pipeline output for one case against the oracle."""
    expected_concept = gt.expected_concept(case)
    rule_concepts = [em.rule_concept(f.get("rule", "")) for f in findings]
    hit = expected_concept in rule_concepts
    relevant = sum(1 for c in rule_concepts if c == expected_concept)
    total_findings = len(findings)
    precision = _safe_div(relevant, total_findings)
    recall = 1.0 if hit else 0.0

    if diag is not None:
        state = em.detect_ai_concepts(diag.root_cause).get(expected_concept, "none")
    else:
        state = "none"
    ai_addressed = state in ("problematic", "present", "absent")
    ai_sentiment_correct = state == "problematic"

    text_exact_match = bool(
        diag is not None
        and (diag.root_cause or "").strip().lower()
        == (case.expected_fault or "").strip().lower()
    )
    osi_match = bool(
        diag is not None
        and (diag.osi_layer or "").strip() == (case.osi_layer or "").strip()
    )
    severity_match = bool(
        diag is not None
        and (diag.severity or "").upper() == (case.severity or "").upper()
    )

    expected_status = gt.expected_correlation_status(case, findings, diag)
    status = corr.correlation_status if corr is not None else "NONE"
    correlation_correct = status == expected_status
    expected_conflict = gt.expected_conflict(case, findings, diag)
    flagged = bool(corr is not None and len(corr.conflicts) > 0)
    conflict_correct = flagged == expected_conflict
    expected_action = gt.expected_action(case, findings, diag)
    recommended_action = corr.recommended_review_action if corr is not None else "INVESTIGATE"
    action_correct = recommended_action == expected_action

    return {
        "case_id": case.case_id,
        "category": case.category,
        "rule_checker": {"hit": hit, "findings": total_findings, "relevant": relevant,
                         "precision": precision, "recall": recall,
                         "expected_concept": expected_concept},
        "ai_diagnosis": {"addressed": ai_addressed, "sentiment_correct": ai_sentiment_correct,
                         "text_exact_match": text_exact_match, "osi_match": osi_match,
                         "severity_match": severity_match},
        "correlation": {"status": status, "expected_status": expected_status,
                        "correct": correlation_correct,
                        "confidence": corr.confidence if corr is not None else 0.0,
                        "ai_support": corr.ai_support_level if corr is not None else "NONE",
                        "rule_support": corr.rule_support_level if corr is not None else "NONE"},
        "conflict": {"expected": expected_conflict, "flagged": flagged, "correct": conflict_correct},
        "review": {"expected_action": expected_action, "recommended_action": recommended_action,
                   "action_correct": action_correct,
                   "requires_human_review": bool(corr is not None and corr.requires_human_review)},
    }


def aggregate(per_cases):
    """Aggregate per-case records into overall / per-category / confusion views."""
    n = len(per_cases)
    if n == 0:
        return {"overall": {}, "category": {}, "correlation_confusion": {}}

    overall = {
        "num_cases": n,
        "rule_checker_accuracy": _safe_div(sum(c["rule_checker"]["hit"] for c in per_cases), n),
        "ai_concept_addressed_rate": _safe_div(sum(c["ai_diagnosis"]["addressed"] for c in per_cases), n),
        "ai_sentiment_correct_rate": _safe_div(sum(c["ai_diagnosis"]["sentiment_correct"] for c in per_cases), n),
        "ai_text_exact_match_rate": _safe_div(sum(c["ai_diagnosis"]["text_exact_match"] for c in per_cases), n),
        "ai_osi_match_rate": _safe_div(sum(c["ai_diagnosis"]["osi_match"] for c in per_cases), n),
        "ai_severity_match_rate": _safe_div(sum(c["ai_diagnosis"]["severity_match"] for c in per_cases), n),
        "correlation_correct_rate": _safe_div(sum(c["correlation"]["correct"] for c in per_cases), n),
    }

    tp = sum(1 for c in per_cases if c["conflict"]["flagged"] and c["conflict"]["expected"])
    predicted = sum(1 for c in per_cases if c["conflict"]["flagged"])
    actual = sum(1 for c in per_cases if c["conflict"]["expected"])
    overall["conflict_precision"] = _safe_div(tp, predicted)
    overall["conflict_recall"] = _safe_div(tp, actual)
    overall["conflict_f1"] = _safe_div(2 * tp, predicted + actual)
    overall["review_recommendation_accuracy"] = _safe_div(sum(c["review"]["action_correct"] for c in per_cases), n)
    overall["review_coverage"] = _safe_div(sum(c["review"]["requires_human_review"] for c in per_cases), n)

    confusion = defaultdict(lambda: defaultdict(int))
    for c in per_cases:
        confusion[c["correlation"]["expected_status"]][c["correlation"]["status"]] += 1
    correlation_confusion = {k: dict(v) for k, v in confusion.items()}

    buckets = defaultdict(lambda: {"n": 0, "hits": 0, "sent": 0, "corr": 0, "act": 0, "conf": 0.0})
    for c in per_cases:
        g = buckets[c["category"]]
        g["n"] += 1
        g["hits"] += 1 if c["rule_checker"]["hit"] else 0
        g["sent"] += 1 if c["ai_diagnosis"]["sentiment_correct"] else 0
        g["corr"] += 1 if c["correlation"]["correct"] else 0
        g["act"] += 1 if c["review"]["action_correct"] else 0
        g["conf"] += c["correlation"]["confidence"]

    category = {}
    for cat, g in buckets.items():
        category[cat] = {
            "n": g["n"],
            "rule_checker_accuracy": _safe_div(g["hits"], g["n"]),
            "ai_sentiment_correct_rate": _safe_div(g["sent"], g["n"]),
            "correlation_correct_rate": _safe_div(g["corr"], g["n"]),
            "review_recommendation_accuracy": _safe_div(g["act"], g["n"]),
            "average_confidence": _safe_div(g["conf"], g["n"]),
        }

    return {"overall": overall, "category": category, "correlation_confusion": correlation_confusion}
