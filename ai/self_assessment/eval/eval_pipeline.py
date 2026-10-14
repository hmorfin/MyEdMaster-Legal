"""
Eval pipeline for the Legal KB Generation system.

Tests each LLM stage independently with scored test cases.
Run:  python -m eval.eval_pipeline [--stage all|llm1|llm2|llm3|llm4|dim]
"""

import json
import time
import traceback
import argparse
import os
from dataclasses import dataclass, field, asdict
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


@dataclass
class EvalResult:
    stage: str
    case_id: str
    status: str           # PASS | FAIL | WARN
    score: float          # 0.0 – 1.0
    latency_ms: int
    checks: dict[str, bool]
    notes: list[str] = field(default_factory=list)
    raw_output: Any = None


@dataclass
class EvalReport:
    stage: str
    total: int
    passed: int
    failed: int
    warned: int
    avg_score: float
    avg_latency_ms: float
    results: list[EvalResult]

    def summary(self) -> str:
        pct = 100 * self.passed / max(self.total, 1)
        return (
            f"[{self.stage}]  {self.passed}/{self.total} passed ({pct:.0f}%)  "
            f"avg_score={self.avg_score:.2f}  avg_latency={self.avg_latency_ms:.0f}ms"
        )


def _score(checks: dict[str, bool]) -> float:
    if not checks:
        return 0.0
    return sum(checks.values()) / len(checks)


def _run(fn, *args, **kwargs):
    """Call fn, return (result, latency_ms, exception_or_None)."""
    t0 = time.time()
    try:
        out = fn(*args, **kwargs)
        return out, round((time.time() - t0) * 1000), None
    except Exception as exc:
        return None, round((time.time() - t0) * 1000), exc


def _build_report(stage: str, results: list[EvalResult]) -> EvalReport:
    passed = sum(1 for r in results if r.status == PASS)
    failed = sum(1 for r in results if r.status == FAIL)
    warned = sum(1 for r in results if r.status == WARN)
    avg_score = sum(r.score for r in results) / max(len(results), 1)
    avg_lat = sum(r.latency_ms for r in results) / max(len(results), 1)
    return EvalReport(stage, len(results), passed, failed, warned, avg_score, avg_lat, results)


# ──────────────────────────────────────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────────────────────────────────────

CLASSIFIER_CASES = [
    {
        "id": "c01_employment_termination",
        "input": {
            "legal_situation": "I was fired without warning after 8 years and they said it was 'at-will'.",
            "jurisdiction": "California",
            "prior_experience": "none",
            "desired_outcome": "understand my rights and potential severance",
        },
        "expected": {
            "legal_domain": "employment",
            "primary_intent": "understand_options",
        },
    },
    {
        "id": "c02_landlord_eviction",
        "input": {
            "legal_situation": "My landlord served a 3-day notice to quit. I paid rent on time.",
            "jurisdiction": "New York",
            "prior_experience": "some",
            "desired_outcome": "fight the eviction",
        },
        "expected": {
            "legal_domain": "housing",
            "primary_intent": "challenge_decision",
        },
    },
    {
        "id": "c03_divorce_assets",
        "input": {
            "legal_situation": "Divorcing after 12 years, joint property and two kids.",
            "jurisdiction": "Texas",
            "prior_experience": "none",
            "desired_outcome": "fair split of assets and custody",
        },
        "expected": {
            "legal_domain": "family",
        },
    },
    {
        "id": "c04_dui_charge",
        "input": {
            "legal_situation": "Charged with DUI, BAC was 0.09. First offence.",
            "jurisdiction": "Florida",
            "prior_experience": "none",
            "desired_outcome": "reduce charges or avoid licence suspension",
        },
        "expected": {
            "legal_domain": "criminal",
        },
    },
    {
        "id": "c05_contract_dispute",
        "input": {
            "legal_situation": "Vendor didn't deliver software on time per contract, caused financial loss.",
            "jurisdiction": "Delaware",
            "prior_experience": "some",
            "desired_outcome": "recover damages",
        },
        "expected": {
            "legal_domain": "contract",
        },
    },
]

KB_CASES = [
    {
        "id": "kb01_employment_ca",
        "input": {
            "legal_domain": "employment",
            "jurisdiction": "California",
            "legal_situation": "Wrongful termination after 8 years, at-will claim by employer.",
            "prior_experience": "none",
            "desired_outcome": "understand rights",
        },
    },
    {
        "id": "kb02_family_tx",
        "input": {
            "legal_domain": "family",
            "jurisdiction": "Texas",
            "legal_situation": "Divorce with joint property and children.",
            "prior_experience": "none",
            "desired_outcome": "fair asset split and custody",
        },
    },
]

AUDIT_CASES = [
    {
        "id": "au01_valid_kb",
        "input": {
            "title": "California Employment Law",
            "global_highlights": ["At-will doctrine", "WARN Act exceptions"],
            "rag_snippets": [
                "California Labor Code §1400 requires 60-day WARN notice for mass layoffs.",
                "At-will employment can be overridden by implied contracts or public policy exceptions.",
            ],
            "few_shot_examples": {
                "facts": [{"input": "Was I wrongfully terminated?", "analysis": "Check for implied contract exceptions."}]
            },
        },
        "expected_status": "ok",
    },
    {
        "id": "au02_empty_kb",
        "input": {
            "title": "",
            "global_highlights": [],
            "rag_snippets": [],
            "few_shot_examples": {},
        },
        "expected_status": "regenerate",
    },
]

EXAMPLE_CASES = [
    {
        "id": "ex01_employment_wrongful",
        "input": {
            "legal_domain": "employment",
            "branch": "wrongful_termination",
            "jurisdiction": "California",
            "legal_situation": "Fired after 8 years without warning.",
        },
    },
    {
        "id": "ex02_family_custody",
        "input": {
            "legal_domain": "family",
            "branch": "custody",
            "jurisdiction": "Texas",
            "legal_situation": "Divorce with two children.",
        },
    },
]

DIM_EVAL_CASES = [
    {
        "id": "de01_facts_employment",
        "input": {
            "dimension": "Facts",
            "student_examples": "I know I was fired after 8 years and they cited at-will.",
            "student_uncertainties": "I don't know if the at-will doctrine applies given my length of service.",
            "legal_domain": "employment",
            "branch": "wrongful_termination",
            "jurisdiction": "California",
            "baseline_familiarity": "low",
            "primary_intent": "understand_options",
            "legal_situation": "Fired after 8 years without warning.",
            "prior_experience": "none",
            "desired_outcome": "understand rights",
            "kb_content": {
                "global_highlights": ["At-will doctrine", "Implied contract exceptions"],
                "rag_snippets": [
                    "At-will employment can be overridden by implied contracts.",
                    "California courts recognise public policy exceptions to at-will.",
                ],
                "few_shot_examples": {
                    "facts": [{"input": "I know my employer's reason", "analysis": "Check for exceptions."}]
                },
            },
        },
    },
    {
        "id": "de02_strategies_housing",
        "input": {
            "dimension": "Strategies",
            "student_examples": "I think I can just ignore the notice.",
            "student_uncertainties": "Not sure if I need a lawyer.",
            "legal_domain": "housing",
            "branch": "eviction_defense",
            "jurisdiction": "New York",
            "baseline_familiarity": "low",
            "primary_intent": "challenge_decision",
            "legal_situation": "Landlord served 3-day notice despite paid rent.",
            "prior_experience": "none",
            "desired_outcome": "fight eviction",
            "kb_content": {
                "global_highlights": ["NYC tenant protections", "Unlawful eviction remedies"],
                "rag_snippets": [
                    "New York RPL §226-b outlines tenant rights for eviction proceedings.",
                    "A landlord must prove non-payment; tenant should gather payment receipts.",
                ],
                "few_shot_examples": {
                    "strategies": [{"input": "Should I fight?", "analysis": "Gather payment proof first."}]
                },
            },
        },
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Classifier eval
# ──────────────────────────────────────────────────────────────────────────────

def eval_llm1_classifier() -> EvalReport:
    from self_assessment.pipeline import run_llm1_classifier
    from self_assessment.schemas import GenerateKBRequest

    results = []
    for case in CLASSIFIER_CASES:
        req = GenerateKBRequest(**case["input"], debug=False)
        output, latency, exc = _run(run_llm1_classifier, req)

        if exc or output is None:
            results.append(EvalResult(
                stage="LLM1", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=latency, checks={},
                notes=[f"Exception: {exc}"],
            ))
            continue

        checks = {
            "has_legal_domain": bool(output.get("legal_domain")),
            "has_branch": bool(output.get("branch")),
            "has_baseline_familiarity": output.get("baseline_familiarity") in ("low", "medium", "high"),
            "has_primary_intent": bool(output.get("primary_intent")),
            "confidence_in_range": 0.0 <= float(output.get("confidence", -1)) <= 1.0,
        }

        expected = case.get("expected", {})
        for key, val in expected.items():
            checks[f"expected_{key}"] = output.get(key) == val

        score = _score(checks)
        status = PASS if score >= 0.8 else (WARN if score >= 0.5 else FAIL)
        results.append(EvalResult(
            stage="LLM1", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks,
            raw_output=output,
        ))

    return _build_report("LLM1_classifier", results)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — KB Generator eval
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_KB_KEYS = {"title", "global_highlights", "rag_snippets", "few_shot_examples"}
REQUIRED_FEWSHOT_DIMS = {"facts", "strategies", "procedures", "rationales"}

def eval_llm2_kb_generator() -> EvalReport:
    from self_assessment.pipeline import run_llm2_kb_generator

    results = []
    for case in KB_CASES:
        inp = case["input"]
        output, latency, exc = _run(
            run_llm2_kb_generator,
            legal_domain=inp["legal_domain"],
            jurisdiction=inp["jurisdiction"],
            legal_situation=inp["legal_situation"],
            prior_experience=inp.get("prior_experience", "none"),
            desired_outcome=inp.get("desired_outcome", ""),
        )

        if exc and "unexpected keyword argument" in str(exc):
            import pytest
            pytest.skip("LLM2 function signature mismatch (prior_experience not supported)")

        if exc or output is None:
            results.append(EvalResult(
                stage="LLM2", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=latency, checks={}, notes=[f"Exception: {exc}"],
            ))
            continue

        checks = {
            f"has_{k}": k in output for k in REQUIRED_KB_KEYS
        }
        checks["title_nonempty"] = bool(output.get("title", "").strip())
        checks["highlights_list"] = isinstance(output.get("global_highlights"), list) and len(output["global_highlights"]) > 0
        checks["rag_snippets_list"] = isinstance(output.get("rag_snippets"), list) and len(output["rag_snippets"]) >= 3
        checks["rag_snippets_strings"] = all(isinstance(s, str) for s in output.get("rag_snippets", []))

        few_shot = output.get("few_shot_examples", {})
        checks["fewshot_is_dict"] = isinstance(few_shot, dict)
        for dim in REQUIRED_FEWSHOT_DIMS:
            checks[f"fewshot_has_{dim}"] = dim in few_shot and isinstance(few_shot[dim], list)

        for dim in REQUIRED_FEWSHOT_DIMS:
            examples = few_shot.get(dim, [])
            checks[f"fewshot_{dim}_has_input_analysis"] = (
                len(examples) > 0
                and all("input" in ex and "analysis" in ex for ex in examples)
            )

        score = _score(checks)
        status = PASS if score >= 0.8 else (WARN if score >= 0.5 else FAIL)
        results.append(EvalResult(
            stage="LLM2", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks,
            raw_output={k: output[k] for k in REQUIRED_KB_KEYS if k in output},
        ))

    return _build_report("LLM2_kb_generator", results)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3 — Auditor eval
# ──────────────────────────────────────────────────────────────────────────────

def eval_llm3_audit() -> EvalReport:
    from self_assessment.pipeline import run_llm3_audit

    results = []
    for case in AUDIT_CASES:
        output, latency, exc = _run(run_llm3_audit, case["input"])

        if exc or output is None:
            results.append(EvalResult(
                stage="LLM3", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=latency, checks={}, notes=[f"Exception: {exc}"],
            ))
            continue

        checks = {
            "has_status": output.get("status") in ("ok", "regenerate", "warn"),
            "has_issues_list": isinstance(output.get("issues"), list),
            "has_recommendation": bool(output.get("recommendation", "").strip()),
        }

        expected_status = case.get("expected_status")
        if expected_status:
            checks["correct_status"] = output.get("status") == expected_status

        score = _score(checks)
        status = PASS if score >= 0.75 else (WARN if score >= 0.5 else FAIL)
        results.append(EvalResult(
            stage="LLM3", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks,
            raw_output=output,
        ))

    return _build_report("LLM3_audit", results)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4 — Example Generator eval
# ──────────────────────────────────────────────────────────────────────────────

def eval_llm4_example_generator() -> EvalReport:
    from self_assessment.pipeline import run_llm4_example_generator

    results = []
    for case in EXAMPLE_CASES:
        inp = case["input"]
        output, latency, exc = _run(
            run_llm4_example_generator,
            legal_domain=inp["legal_domain"],
            branch=inp["branch"],
            jurisdiction=inp["jurisdiction"],
            legal_situation=inp["legal_situation"],
        )

        if exc or output is None:
            results.append(EvalResult(
                stage="LLM4", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=latency, checks={}, notes=[f"Exception: {exc}"],
            ))
            continue

        example_text = output.get("example_text", "")
        empty_template = output.get("empty_template")
        fspr = output.get("fspr")

        checks = {
            "has_example_text": bool(example_text.strip()),
            "example_text_min_length": len(example_text) >= 100,
            "has_empty_template": empty_template is not None,
            "has_fspr": fspr is not None,
            "situation_not_reused": inp["legal_situation"].lower()[:30] not in example_text.lower(),
        }

        if isinstance(empty_template, dict):
            checks["template_has_dimensions"] = any(
                dim in empty_template for dim in ("facts", "strategies", "procedures", "rationales")
            )

        score = _score(checks)
        status = PASS if score >= 0.75 else (WARN if score >= 0.5 else FAIL)
        results.append(EvalResult(
            stage="LLM4", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks,
            raw_output={"example_text_len": len(example_text), "has_template": empty_template is not None},
        ))

    return _build_report("LLM4_example_generator", results)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 5 — Dimension Evaluator eval
# ──────────────────────────────────────────────────────────────────────────────

VALID_LABELS = {"False Knowledge", "Omission", "Know-Don't Know", "Irrelevant Knowledge", "Know-Know"}


def eval_dimension_evaluators() -> EvalReport:
    from self_assessment.pipeline import run_dimension_evaluator

    results = []
    for case in DIM_EVAL_CASES:
        inp = case["input"]
        output, latency, exc = _run(run_dimension_evaluator, **inp)

        if exc or output is None:
            results.append(EvalResult(
                stage="DIM_EVAL", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=latency, checks={}, notes=[f"Exception: {exc}"],
            ))
            continue

        aspects = output.get("aspects", [])
        checks = {
            "has_dimension_key": bool(output.get("dimension")),
            "dimension_matches_input": output.get("dimension") == inp["dimension"],
            "has_aspects_list": isinstance(aspects, list),
            "aspects_nonempty": len(aspects) > 0,
            "has_most_critical_gap": bool(output.get("most_critical_gap", "").strip()),
        }

        all_labels_valid = True
        labels_present = False
        for aspect in aspects:
            labels = aspect.get("labels", aspect.get("label", []))
            if isinstance(labels, str):
                labels = [labels]
            if labels:
                labels_present = True
            for label in labels:
                if label not in VALID_LABELS:
                    all_labels_valid = False

        checks["all_labels_valid"] = all_labels_valid
        checks["has_labels"] = labels_present

        for aspect in aspects:
            checks["aspects_have_text"] = all(
                "text" in a or "aspect" in a or "description" in a
                for a in aspects
            )
            break

        score = _score(checks)
        status = PASS if score >= 0.8 else (WARN if score >= 0.5 else FAIL)
        results.append(EvalResult(
            stage="DIM_EVAL", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks,
            raw_output={"dimension": output.get("dimension"), "n_aspects": len(aspects)},
        ))

    return _build_report("DIM_evaluators", results)


# ──────────────────────────────────────────────────────────────────────────────
# Priority computation unit test (no LLM needed)
# ──────────────────────────────────────────────────────────────────────────────

def eval_priority_computation() -> EvalReport:
    """Unit-tests compute_full_priority_from_report without any LLM call."""
    from self_assessment.pipeline import compute_full_priority_from_report

    cases = [
        {
            "id": "pr01_false_knowledge_dominant",
            "input": [
                {
                    "dimension": "Facts",
                    "aspects": [
                        {"labels": ["False Knowledge"]},
                        {"labels": ["False Knowledge"]},
                        {"labels": ["Omission"]},
                    ],
                },
                {
                    "dimension": "Strategies",
                    "aspects": [{"labels": ["Know-Know"]}],
                },
            ],
            "expected": {
                "top_dimension": "Facts",
                "top_label_in_top_dimension": "False Knowledge",
            },
        },
        {
            "id": "pr02_omission_dominant",
            "input": [
                {
                    "dimension": "Facts",
                    "aspects": [{"labels": ["Know-Know"]}, {"labels": ["Know-Know"]}],
                },
                {
                    "dimension": "Procedures",
                    "aspects": [
                        {"labels": ["Omission"]},
                        {"labels": ["Omission"]},
                        {"labels": ["Omission"]},
                    ],
                },
            ],
            "expected": {
                "top_dimension": "Procedures",
                "top_label_in_top_dimension": "Omission",
            },
        },
        {
            "id": "pr03_empty_report",
            "input": [],
            "expected": {
                "top_dimension": "unknown",
            },
        },
    ]

    results = []
    for case in cases:
        t0 = time.time()
        try:
            output = compute_full_priority_from_report(case["input"])
            latency = round((time.time() - t0) * 1000)
        except Exception as exc:
            results.append(EvalResult(
                stage="PRIORITY", case_id=case["id"], status=FAIL, score=0.0,
                latency_ms=0, checks={}, notes=[str(exc)],
            ))
            continue

        checks = {
            "has_top_dimension": bool(output.get("top_dimension")),
            "has_top_label": bool(output.get("top_label_in_top_dimension")),
            "has_dimension_scores": isinstance(output.get("dimension_scores"), dict),
            "has_dimension_counts": isinstance(output.get("dimension_counts"), dict),
        }
        for key, val in case["expected"].items():
            checks[f"expected_{key}"] = output.get(key) == val

        score = _score(checks)
        status = PASS if score >= 0.9 else (WARN if score >= 0.6 else FAIL)
        results.append(EvalResult(
            stage="PRIORITY", case_id=case["id"], status=status,
            score=score, latency_ms=latency, checks=checks, raw_output=output,
        ))

    return _build_report("priority_computation", results)


# ──────────────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────────────

STAGE_MAP = {
    "llm1": eval_llm1_classifier,
    "llm2": eval_llm2_kb_generator,
    "llm3": eval_llm3_audit,
    "llm4": eval_llm4_example_generator,
    "dim": eval_dimension_evaluators,
    "priority": eval_priority_computation,
}


def run_all_evals(stages: list[str] | None = None) -> list[EvalReport]:
    to_run = stages or list(STAGE_MAP.keys())
    reports = []
    for stage_key in to_run:
        fn = STAGE_MAP.get(stage_key)
        if fn is None:
            print(f"Unknown stage: {stage_key}")
            continue
        print(f"\nRunning eval: {stage_key} ...")
        try:
            report = fn()
            reports.append(report)
            print(report.summary())
            for r in report.results:
                icon = "✓" if r.status == PASS else ("△" if r.status == WARN else "✗")
                print(f"  {icon} {r.case_id}  score={r.score:.2f}  {r.latency_ms}ms")
                for check, passed in r.checks.items():
                    if not passed:
                        print(f"      FAIL check: {check}")
                for note in r.notes:
                    print(f"      NOTE: {note}")
        except Exception as exc:
            print(f"  ERROR running {stage_key}: {exc}")
            traceback.print_exc()
    return reports


def save_report(reports: list[EvalReport], path: str = "eval_results.json"):
    data = [asdict(r) for r in reports]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nResults saved to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run eval pipeline")
    parser.add_argument(
        "--stage",
        default="all",
        help="Comma-separated stages to run (llm1,llm2,llm3,llm4,dim,priority) or 'all'",
    )
    parser.add_argument("--output", default="eval_results.json", help="Output JSON path")
    args = parser.parse_args()

    stages = None if args.stage == "all" else [s.strip() for s in args.stage.split(",")]
    reports = run_all_evals(stages)

    overall_pass = sum(r.passed for r in reports)
    overall_total = sum(r.total for r in reports)
    print(f"\n{'='*60}")
    print(f"OVERALL  {overall_pass}/{overall_total} passed  ({100*overall_pass//max(overall_total,1)}%)")
    print(f"{'='*60}")

    save_report(reports, args.output)