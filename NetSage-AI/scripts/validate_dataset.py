#!/usr/bin/env python3
"""Run dataset structural validation for NetSage-AI."""
from __future__ import annotations

from utils.csv_loader import load_cases
from utils.validators import validate_dataset


def main() -> int:
    cases = load_cases()
    result = validate_dataset(cases)
    print("Dataset validation result:")
    print(f"  ok: {result['ok']}")
    print(f"  count: {result['count']}")
    if result.get("errors"):
        print("  errors:")
        for e in result["errors"]:
            print(f"    - {e}")
    if result.get("warnings"):
        print("  warnings:")
        for w in result["warnings"]:
            print(f"    - {w}")
    print("Category counts:")
    for k, v in result.get("category_counts", {}).items():
        print(f"  {k}: {v}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
