"""
pytest integration — runs each stage as a test.

Usage:
    pytest evals/test_eval_pipeline.py -v
    pytest evals/test_eval_pipeline.py -v -k llm1
    pytest evals/test_eval_pipeline.py -v --llm-stages llm1,priority

Set SKIP_LLM_STAGES=1 to skip stages that require live API calls.
"""

import os
import pytest
from self_assessment.eval.eval_pipeline import (
    eval_llm1_classifier,
    eval_llm2_kb_generator,
    eval_llm3_audit,
    eval_llm4_example_generator,
    eval_dimension_evaluators,
    eval_priority_computation,
    EvalReport,
    PASS,
    WARN,
)

SKIP_LLM = os.getenv("SKIP_LLM_STAGES", "0") == "1"
requires_llm = pytest.mark.skipif(SKIP_LLM, reason="SKIP_LLM_STAGES=1")

MIN_PASS_RATE = 0.70   # at least 70% of cases must PASS
MIN_AVG_SCORE = 0.75   # average score must be ≥ 0.75


def _assert_report(report: EvalReport, name: str):
    pass_rate = report.passed / max(report.total, 1)
    assert pass_rate >= MIN_PASS_RATE, (
        f"{name}: pass rate {pass_rate:.0%} below threshold {MIN_PASS_RATE:.0%}. "
        f"Results: {[(r.case_id, r.status, r.score) for r in report.results]}"
    )
    assert report.avg_score >= MIN_AVG_SCORE, (
        f"{name}: avg score {report.avg_score:.2f} below threshold {MIN_AVG_SCORE:.2f}"
    )


@requires_llm
def test_llm1_classifier():
    report = eval_llm1_classifier()
    _assert_report(report, "LLM1 classifier")


@requires_llm
def test_llm2_kb_generator():
    report = eval_llm2_kb_generator()
    _assert_report(report, "LLM2 KB generator")


@requires_llm
def test_llm3_audit():
    report = eval_llm3_audit()
    _assert_report(report, "LLM3 audit")


@requires_llm
def test_llm4_example_generator():
    report = eval_llm4_example_generator()
    _assert_report(report, "LLM4 example generator")


@requires_llm
def test_dimension_evaluators():
    report = eval_dimension_evaluators()
    _assert_report(report, "Dimension evaluators")


def test_priority_computation():
    """Unit test — no LLM needed, always runs."""
    report = eval_priority_computation()
    assert report.passed == report.total, (
        f"Priority computation: {report.failed} case(s) failed — "
        f"{[(r.case_id, r.checks) for r in report.results if r.status != PASS]}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Parametrised latency guard (requires_llm)
# ──────────────────────────────────────────────────────────────────────────────

LATENCY_BUDGETS_MS = {
    "llm1": 5_000,
    "llm2": 30_000,
    "llm3": 5_000,
    "llm4": 10_000,
    "dim": 10_000,
}

@requires_llm
@pytest.mark.parametrize("stage,budget", LATENCY_BUDGETS_MS.items())
def test_latency_budgets(stage, budget):
    from self_assessment.eval.eval_pipeline import STAGE_MAP
    report = STAGE_MAP[stage]()
    over_budget = [
        r for r in report.results if r.latency_ms > budget
    ]
    assert not over_budget, (
        f"[{stage}] {len(over_budget)} case(s) exceeded {budget}ms latency budget: "
        f"{[(r.case_id, r.latency_ms) for r in over_budget]}"
    )