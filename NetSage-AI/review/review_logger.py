from __future__ import annotations

import csv
import os
from datetime import datetime
from utils.csv_loader import RESPONSIBLE_LOG_CSV


def append_review(row: dict) -> None:
    path = RESPONSIBLE_LOG_CSV
    exists = os.path.exists(path)
    fields = [
        "case_id",
        "ai_root_cause",
        "human_decision",
        "corrected_root_cause",
        "reason_for_correction",
        "reviewer_note",
        "edited_osi_layer",
        "edited_confidence",
                "edited_next_command",
        "edited_fix_steps",
        "correlation_status",
        "correlation_confidence",
        "ai_support_level",
        "rule_support_level",
        "recommended_review_action",
        "conflicts",
        "timestamp",
    ]
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        if "timestamp" not in row:
            row["timestamp"] = datetime.utcnow().isoformat() + "Z"
        writer.writerow({k: row.get(k, "") for k in fields})
