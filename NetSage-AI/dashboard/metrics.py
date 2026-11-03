from __future__ import annotations
from utils.csv_loader import load_cases, load_responsible_log


def summary_counts() -> dict:
    cases = load_cases()
    total = len(cases)
    by_cat = {}
    for c in cases:
        by_cat[c.category] = by_cat.get(c.category, 0) + 1
    return {"total": total, "by_category": by_cat}
