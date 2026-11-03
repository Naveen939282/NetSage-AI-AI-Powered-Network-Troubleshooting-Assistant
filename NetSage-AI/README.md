# NetSage-AI

Evidence-Grounded AI Network Troubleshooting Assistant with Human-in-the-Loop Validation

Overview
- Purpose: assist network engineers by combining deterministic rule checks with an evidence-grounded AI diagnosis and a human review workflow.

Installation
1. Create a virtualenv: `python -m venv .venv`
2. Activate and install: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and edit if needed.

Run (demo mode):
```
streamlit run app.py
```

This repository contains a dataset of troubleshooting cases in `data/cases.csv`, a deterministic rule checker, an AI schema, and a Streamlit dashboard.

## Phase 5 — Offline Evaluation & Benchmarking

A reproducible, self-contained evaluation framework lives in `evaluation/`. It runs the **deterministic runtime pipeline** (rule checker → `MockProvider` AI diagnosis → evidence correlation → review recommendation) over every case in `data/cases.csv` and scores it against **oracle labels derived only from the ground-truth columns** (`expected_fault`, `expected_command`, `expected_fix`, `concept`, `osi_layer`, `severity`).

**Ground-truth isolation.** The ground-truth columns are read *only* in `evaluation/ground_truth.py`. The live pipeline modules (`checker/`, `ai/`, `correlation/`, `review/`) never import the evaluator, so ground truth cannot leak into runtime decisions. (`MockProvider` echoes `expected_fault` for demo display; this is reported transparently as a mock limitation, not live-AI accuracy.)

**Reproducibility.** Runs offline with no internet, API keys, GPU, or live devices — the AI provider is the deterministic `MockProvider`. Results are byte-for-byte reproducible across runs.

**Metrics produced (covers all seven objectives).**
1. Rule-checker — per-case/per-category hit accuracy + per-rule precision/recall/F1.
2. AI diagnosis — concept-addressed, sentiment-correct, text-exact-match, OSI-layer & severity accuracy.
3. Evidence correlation — status correctness vs. oracle + correlation confusion matrix.
4. Conflict detection — precision / recall / F1 of flagged conflicts.
5. Category-level — per-category breakdown (VLAN, Gateway, Routing, ACL, NAT, DHCP, …).
6. Human-review recommendation — recommendation accuracy vs. oracle action + review coverage.
7. Overall — aggregate accuracy, conflict F1, review-recall.

**Run:**
```bash
python -m evaluation.runner --output-dir eval_reports
```
Outputs per run in `eval_reports/`: `evaluation_<timestamp>.json` (full per-case + aggregate), `metrics_<timestamp>.csv` (flat table), and `summary_<timestamp>.txt` (human-readable dashboard).

**Test:**
```bash
python -m pytest -q
```
