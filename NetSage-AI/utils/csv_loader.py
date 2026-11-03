"""CSV data loading helpers for NetSage-AI."""
from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from typing import Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CASES_CSV = os.path.join(DATA_DIR, "cases.csv")
RESPONSIBLE_LOG_CSV = os.path.join(DATA_DIR, "responsible_ai_log.csv")

# Canonical field order (matches cases.csv header exactly).
CASE_FIELDS = [
    "case_id", "category", "title", "symptom", "topology", "show_output",
    "expected_fault", "osi_layer", "concept", "severity",
    "expected_command", "expected_fix",
]


@dataclass
class Case:
    case_id: str
    category: str
    title: str
    symptom: str
    topology: str
    show_output: str
    expected_fault: str
    osi_layer: str
    concept: str
    severity: str
    expected_command: str
    expected_fix: str

    def to_dict(self) -> dict:
        return asdict(self)


def _strip(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _row_to_case(row: dict) -> Case:
    return Case(**{f: _strip(row.get(f, "")) for f in CASE_FIELDS})


def load_cases(path: Optional[str] = None) -> list[Case]:
    """Load all troubleshooting cases from cases.csv."""
    path = path or CASES_CSV
    cases: list[Case] = []
    if not os.path.exists(path):
        return cases
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(_row_to_case(row))
    return cases


def case_by_id(case_id: str, path: Optional[str] = None) -> Optional[Case]:
    for c in load_cases(path):
        if c.case_id == case_id:
            return c
    return None


def load_responsible_log(path: Optional[str] = None) -> list[dict]:
    path = path or RESPONSIBLE_LOG_CSV
    rows: list[dict] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def category_counts(cases: list[Case]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in cases:
        counts[c.category] = counts.get(c.category, 0) + 1
    return counts
