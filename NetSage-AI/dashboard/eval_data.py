"""Load and interpret offline evaluation reports for the dashboard.

Consumes the JSON artifacts produced by ``evaluation/runner.py``.  Never
recalculates metrics — it only reads and shapes the evaluator's output.
"""
from __future__ import annotations

import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(ROOT, "eval_reports")


def latest_report_path():
    """Return the newest ``evaluation_*.json`` path, or None."""
    if not os.path.isdir(EVAL_DIR):
        return None
    files = sorted(glob.glob(os.path.join(EVAL_DIR, "evaluation_*.json")))
    return files[-1] if files else None


def load_report(path=None):
    """Return a parsed report dict, or None if missing/malformed."""
    path = path or latest_report_path()
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "aggregate" not in data:
        return None
    return data


def overall(data):
    if not data:
        return {}
    return data["aggregate"]["overall"]


def category_rows(data):
    """Category table rows the dashboard can render directly."""
    if not data:
        return []
    out = []
    for cat, m in data["aggregate"]["category"].items():
        out.append({"category": cat, "cases": m["n"],
                    "detection_rate": m["rule_checker_accuracy"],
                    "correlation_correct": m["correlation_correct_rate"],
                    "conf_f1": m.get("average_confidence", 0.0)})
    return out


def failure_cases(data, max_n=8):
    """Per-case rows where the pipeline diverged from the oracle."""
    if not data:
        return []
    out = [c for c in data.get("per_case", [])
           if not c["correlation"]["correct"] or not c["review"]["action_correct"]]
    return out[:max_n]
