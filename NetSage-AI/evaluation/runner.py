"""Offline evaluation runner for NetSage-AI.

Reproducible from ``data/cases.csv`` alone.  No internet, API keys, GPU or
live Cisco devices are required: the AI provider is the deterministic
MockProvider, and every pipeline stage is a pure function of the case.

Usage::

    python -m evaluation.runner [--output-dir DIR] [--cases N]

Produces, per run, a JSON report, a flat CSV, and a human-readable summary.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("AI_PROVIDER", "mock")

from utils.csv_loader import load_cases
from checker.network_rules import run_network_rules
from ai.provider import get_provider
from ai.diagnosis import safe_diagnosis
from correlation.engine import correlate
from evaluation.metrics import per_case_metrics, aggregate

CSV_FIELDS = [
    "case_id", "category", "checker_hit", "num_findings", "checker_precision",
    "ai_addressed", "ai_sentiment_correct", "ai_text_exact", "ai_osi_match",
    "ai_severity_match", "corr_status", "corr_expected_status", "corr_correct",
    "corr_confidence", "conflict_expected", "conflict_flagged", "conflict_correct",
    "rec_action", "rec_expected_action", "rec_correct",
]


def _run_case(case):
    findings = run_network_rules(case)["findings"]
    provider = get_provider()
    diag = safe_diagnosis(provider, case, rule_findings=findings)
    corr = correlate(case, findings, diag) if diag is not None else None
    return findings, diag, corr


def evaluate(cases=None):
    cases = list(cases) if cases is not None else load_cases()
    per = []
    for case in cases:
        findings, diag, corr = _run_case(case)
        per.append(per_case_metrics(case, findings, diag, corr))
    return per, aggregate(per)


def _flat(c):
    rc, ai, co, cf, rv = c["rule_checker"], c["ai_diagnosis"], c["correlation"], c["conflict"], c["review"]
    return {
        "case_id": c["case_id"], "category": c["category"],
        "checker_hit": rc["hit"], "num_findings": rc["findings"], "checker_precision": rc["precision"],
        "ai_addressed": ai["addressed"], "ai_sentiment_correct": ai["sentiment_correct"],
        "ai_text_exact": ai["text_exact_match"], "ai_osi_match": ai["osi_match"],
        "ai_severity_match": ai["severity_match"],
        "corr_status": co["status"], "corr_expected_status": co["expected_status"],
        "corr_correct": co["correct"], "corr_confidence": co["confidence"],
        "conflict_expected": cf["expected"], "conflict_flagged": cf["flagged"],
        "conflict_correct": cf["correct"],
        "rec_action": rv["recommended_action"], "rec_expected_action": rv["expected_action"],
        "rec_correct": rv["action_correct"],
    }


def write_reports(per_cases, agg, output_dir, run_id):
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = "evaluation_" + ts + "_" + run_id
    json_path = os.path.join(output_dir, base + ".json")
    csv_path = os.path.join(output_dir, base + ".csv")
    summary_path = os.path.join(output_dir, base + ".txt")
    report = {"generated_at": ts, "run_id": run_id, "num_cases": len(per_cases),
              "aggregate": agg, "per_case": per_cases}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for c in per_cases:
            w.writerow(_flat(c))

    o = agg["overall"]
    lines = [
        "NetSage-AI Evaluation Summary",
        "  Methodology: deterministic pipeline (MockProvider, no network/API/GPU).",
        "  Ground truth used ONLY here, for oracle labels (see evaluation/ground_truth.py).",
        "  cases evaluated  : " + str(o["num_cases"]),
        "  rule-checker accuracy        : " + str(round(o["rule_checker_accuracy"] * 100, 1)) + "%",
        "  AI concept addressed          : " + str(round(o["ai_concept_addressed_rate"] * 100, 1)) + "%",
        "  AI sentiment correct          : " + str(round(o["ai_sentiment_correct_rate"] * 100, 1)) + "%",
        "  AI text exact match (mock*)   : " + str(round(o["ai_text_exact_match_rate"] * 100, 1)) + "%",
        "  AI osi layer match            : " + str(round(o["ai_osi_match_rate"] * 100, 1)) + "%",
        "  AI severity match             : " + str(round(o["ai_severity_match_rate"] * 100, 1)) + "%",
        "  correlation correctness       : " + str(round(o["correlation_correct_rate"] * 100, 1)) + "%",
        "  conflict precision/recall/F1  : " +
        str(round(o["conflict_precision"], 3)) + "/" +
        str(round(o["conflict_recall"], 3)) + "/" + str(round(o["conflict_f1"], 3)),
        "  review-recommendation accuracy: " + str(round(o["review_recommendation_accuracy"] * 100, 1)) + "%",
        "  review coverage               : " + str(round(o["review_coverage"] * 100, 1)) + "%",
        "",
        "  * MockProvider echoes expected_fault verbatim; 100% text match reflects the",
        "    demo provider, not live AI.",
        "",
        "Per-category:",
    ]
    for cat, m in sorted(agg["category"].items()):
        lines.append("  " + cat.ljust(10) + " n=" + str(m["n"]).ljust(4) +
                     " checker=" + str(round(m["rule_checker_accuracy"] * 100, 1)) + "%  "
                     "ai_sent=" + str(round(m["ai_sentiment_correct_rate"] * 100, 1)) + "%  "
                     "corr=" + str(round(m["correlation_correct_rate"] * 100, 1)) + "%  "
                     "rec=" + str(round(m["review_recommendation_accuracy"] * 100, 1)) + "%  "
                     "conf=" + str(round(m["average_confidence"], 3)))
    lines.append("")
    lines.append("Correlation status confusion (rows=expected, cols=actual):")
    for e, row in agg["correlation_confusion"].items():
        cells = "  ".join(k + "=" + str(v) for k, v in sorted(row.items()))
        lines.append("  " + e.ljust(22) + cells)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(chr(10).join(lines) + chr(10))
    return {"json": json_path, "csv": csv_path, "summary": summary_path, "report": report}


def main(argv=None):
    p = argparse.ArgumentParser(description="Run the offline NetSage-AI evaluation.")
    p.add_argument("--output-dir", default=os.path.join(_ROOT, "eval_reports"))
    p.add_argument("--cases", type=int, default=0, help="limit to first N cases (0 = all)")
    p.add_argument("--run-id", default="netsagai")
    args = p.parse_args(argv)
    cases = load_cases()
    if args.cases:
        cases = cases[:args.cases]
    per, agg = evaluate(cases)
    paths = write_reports(per, agg, args.output_dir, args.run_id)
    print(paths["summary"])
    print("-" * 60)
    with open(paths["summary"], encoding="utf-8") as f:
        print(f.read())
    print("Wrote:", paths["json"])
    print("Wrote:", paths["csv"])
    print("Wrote:", paths["summary"])


if __name__ == "__main__":
    main()
