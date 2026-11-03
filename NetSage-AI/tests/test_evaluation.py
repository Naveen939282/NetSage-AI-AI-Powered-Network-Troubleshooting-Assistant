"""Tests for the Phase 5 offline evaluation framework."""
import inspect
import json
import csv
import os
import importlib

from evaluation import ground_truth, metrics
from evaluation.runner import evaluate, write_reports


def test_evaluation_is_reproducible():
    a_per, a_agg = evaluate()
    b_per, b_agg = evaluate()
    assert a_agg == b_agg
    assert [c["case_id"] for c in a_per] == [c["case_id"] for c in b_per]
    assert a_agg["overall"]["num_cases"] > 0


def test_outputs_are_written(tmp_path):
    per, agg = evaluate()
    paths = write_reports(per, agg, str(tmp_path), "test")
    for k in ("json", "csv", "summary"):
        assert os.path.exists(paths[k])
    report = json.load(open(paths["json"], encoding="utf-8"))
    assert report["num_cases"] == len(per)
    assert "overall" in report["aggregate"]
    assert "category" in report["aggregate"]
    rows = list(csv.DictReader(open(paths["csv"], encoding="utf-8")))
    assert len(rows) == len(per)
    assert "corr_status" in rows[0]


def test_ground_truth_is_isolated_to_eval_framework():
    pipeline = ["checker.network_rules", "correlation.engine", "correlation.evidence_matcher",
                "review.human_review", "review.review_logger", "ai.diagnosis", "ai.schemas"]
    for name in pipeline:
        src = inspect.getsource(importlib.import_module(name))
        assert "ground_truth" not in src, f"{name} must not import the eval ground_truth module"
        assert "expected_fault" not in src, f"{name} must not read expected_fault"
        assert "expected_fix" not in src, f"{name} must not read expected_fix"
        assert "expected_command" not in src, f"{name} must not read expected_command"
    # the eval framework is the only consumer of the ground-truth columns
    assert "expected_fault" in inspect.getsource(metrics)


def test_metrics_handles_missing_diagnosis():
    from utils.csv_loader import Case
    c = Case(case_id="X", category="VLAN", title="t", symptom="", topology="",
             show_output="", expected_fault="", osi_layer="Layer 2", concept="c",
             severity="LOW", expected_command="", expected_fix="")
    m = metrics.per_case_metrics(c, [], None, None)
    assert m["case_id"] == "X"
    assert m["correlation"]["status"] == "NONE"
    assert m["review"]["requires_human_review"] is False
    assert m["conflict"]["expected"] is False


def test_aggregate_shape():
    per, agg = evaluate()
    o = agg["overall"]
    for k in ["num_cases", "rule_checker_accuracy", "ai_concept_addressed_rate",
              "ai_sentiment_correct_rate", "correlation_correct_rate", "conflict_f1",
              "review_recommendation_accuracy", "review_coverage"]:
        assert k in o
    assert 0.0 <= o["correlation_correct_rate"] <= 1.0
    assert 0.0 <= o["conflict_f1"] <= 1.0
