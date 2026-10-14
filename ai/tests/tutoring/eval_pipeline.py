"""
Evaluation pipeline for lesson_graph, assessment_graph, and feedback_graph.

Run:
    python eval_pipeline.py                  # all suites
    python eval_pipeline.py --suite lesson   # one suite
    python eval_pipeline.py --verbose        # show full output diffs
"""

from __future__ import annotations

import argparse
import json
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

def _import_graphs():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from graph.course_builder import lesson_graph, assessment_graph, feedback_graph  
    return lesson_graph, assessment_graph, feedback_graph


# ===========================================================================
# Result & Score primitives
# ===========================================================================

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    suite: str
    passed: bool
    latency_s: float
    checks: list[CheckResult] = field(default_factory=list)
    error: str | None = None
    output: dict | None = None

    @property
    def score(self) -> float:
        if not self.checks:
            return 1.0 if self.passed else 0.0
        return sum(c.passed for c in self.checks) / len(self.checks)


# ===========================================================================
# Generic check helpers
# ===========================================================================

def check_no_error(state: dict) -> CheckResult:
    err = state.get("error")
    return CheckResult("no_error", err is None, f"error={err!r}")


def check_field_non_empty(state: dict, field_name: str) -> CheckResult:
    val = state.get(field_name)
    ok = bool(val)
    return CheckResult(f"{field_name}_non_empty", ok, f"type={type(val).__name__}, len={len(val) if hasattr(val, '__len__') else 'n/a'}")


def check_min_length(state: dict, field_name: str, min_len: int) -> CheckResult:
    val = state.get(field_name, "")
    ok = isinstance(val, str) and len(val) >= min_len
    return CheckResult(f"{field_name}_min_length_{min_len}", ok, f"actual={len(val)}")


def check_list_min_count(state: dict, field_name: str, min_count: int) -> CheckResult:
    val = state.get(field_name, [])
    ok = isinstance(val, list) and len(val) >= min_count
    return CheckResult(f"{field_name}_min_count_{min_count}", ok, f"actual={len(val)}")


# ===========================================================================
# Lesson graph checks
# ===========================================================================

def check_lesson_content_has_sections(state: dict) -> CheckResult:
    """Lesson markdown should have at least two heading markers."""
    content = state.get("content", "")
    heading_count = content.count("\n#")
    ok = heading_count >= 2
    return CheckResult("content_has_sections", ok, f"headings={heading_count}")


def check_key_terms_structure(state: dict) -> CheckResult:
    """Every key term must have 'term' and 'definition' keys."""
    terms = state.get("key_terms", [])
    if not terms:
        return CheckResult("key_terms_structure", True, "no terms to validate")
    bad = [t for t in terms if not (isinstance(t, dict) and "term" in t and "definition" in t)]
    ok = len(bad) == 0
    return CheckResult("key_terms_structure", ok, f"bad_terms={len(bad)}/{len(terms)}")


def check_content_mentions_topic(state: dict, topic: str) -> CheckResult:
    content = state.get("content", "").lower()
    ok = topic.lower() in content
    return CheckResult("content_mentions_topic", ok, f"topic={topic!r}")


# ===========================================================================
# Assessment graph checks
# ===========================================================================

def check_question_schema(state: dict) -> CheckResult:
    """Every question must have question/options/correct_index/explanation."""
    questions = state.get("questions", [])
    if not questions:
        return CheckResult("question_schema", False, "no questions")
    required_keys = {"question", "options", "correct_index", "explanation"}
    bad = [q for q in questions if not required_keys.issubset(q.keys())]
    ok = len(bad) == 0
    return CheckResult("question_schema", ok, f"invalid={len(bad)}/{len(questions)}")


def check_options_count(state: dict) -> CheckResult:
    questions = state.get("questions", [])
    bad = [q for q in questions if len(q.get("options", [])) != 4]
    ok = len(bad) == 0
    return CheckResult("options_count_4", ok, f"bad={len(bad)}/{len(questions)}")


def check_correct_index_in_range(state: dict) -> CheckResult:
    questions = state.get("questions", [])
    bad = [q for q in questions if not (isinstance(q.get("correct_index"), int) and 0 <= q["correct_index"] <= 3)]
    ok = len(bad) == 0
    return CheckResult("correct_index_in_range", ok, f"bad={len(bad)}/{len(questions)}")


def check_question_count(state: dict, expected: int) -> CheckResult:
    actual = len(state.get("questions", []))
    ok = actual == expected
    return CheckResult(f"question_count_{expected}", ok, f"actual={actual}")


# ===========================================================================
# Feedback graph checks
# ===========================================================================

def check_feedback_mentions_score(state: dict, score_pct: int) -> CheckResult:
    feedback = state.get("feedback", "").lower()
    ok = str(score_pct) in feedback or str(score_pct - 1) in feedback  # allow ±1 rounding
    return CheckResult("feedback_mentions_score", ok, f"score_pct={score_pct}")


def check_feedback_tone_for_pass(state: dict, passed: bool) -> CheckResult:
    """Passed = positive words; failed = improvement words."""
    feedback = state.get("feedback", "").lower()
    if passed:
        positive = ["great", "well done", "excellent", "passed", "congratulations", "good work"]
        ok = any(w in feedback for w in positive)
        return CheckResult("feedback_positive_tone", ok, "no positive language found")
    else:
        improvement = ["review", "try again", "improve", "missed", "study", "practice", "did not pass", "not passed"]
        ok = any(w in feedback for w in improvement)
        return CheckResult("feedback_improvement_tone", ok, "no improvement language found")


# ===========================================================================
# Test fixtures
# ===========================================================================

LESSON_CASES = [
    {
        "id": "lesson_beginner_contracts",
        "input": {
            "lesson_id": "L001",
            "lesson_title": "Introduction to Contract Formation",
            "module_title": "Contracts Fundamentals",
            "course_title": "Bar Prep: Contracts",
            "legal_topic": "Contract Law",
            "level": "beginner",
            "learning_objectives": [
                "Define a valid contract",
                "Identify offer, acceptance, and consideration",
                "Distinguish contracts from agreements",
            ],
            "user_context": {
                "mastery_scores": {"Contract Law": 0.1},
                "jurisdiction": "Federal",
                "profession": "Law Student",
            },
            "content": "",
            "key_terms": [],
            "error": None,
        },
        "extra_checks": lambda s: [
            check_content_mentions_topic(s, "contract"),
            check_lesson_content_has_sections(s),
        ],
    },
    {
        "id": "lesson_advanced_evidence",
        "input": {
            "lesson_id": "L002",
            "lesson_title": "Hearsay Exceptions Under FRE 803",
            "module_title": "Federal Rules of Evidence",
            "course_title": "Evidence Mastery",
            "legal_topic": "Evidence",
            "level": "advanced",
            "learning_objectives": [
                "Enumerate the 23 FRE 803 exceptions",
                "Apply each exception to fact patterns",
                "Distinguish 803 from 804 exceptions",
            ],
            "user_context": {
                "mastery_scores": {"Evidence": 0.8},
                "jurisdiction": "Federal",
                "profession": "Attorney",
            },
            "content": "",
            "key_terms": [],
            "error": None,
        },
        "extra_checks": lambda s: [
            check_content_mentions_topic(s, "hearsay"),
        ],
    },
    {
        "id": "lesson_intermediate_torts",
        "input": {
            "lesson_id": "L003",
            "lesson_title": "Negligence: Duty and Breach",
            "module_title": "Tort Law",
            "course_title": "Civil Liability Fundamentals",
            "legal_topic": "Tort Law",
            "level": "intermediate",
            "learning_objectives": [
                "Define duty of care",
                "Apply the reasonable person standard",
                "Identify breach through risk-utility balancing",
            ],
            "user_context": {
                "mastery_scores": {"Tort Law": 0.45},
                "jurisdiction": "California",
                "profession": "Paralegal",
            },
            "content": "",
            "key_terms": [],
            "error": None,
        },
        "extra_checks": lambda s: [
            check_content_mentions_topic(s, "negligence"),
            check_lesson_content_has_sections(s),
        ],
    },
]

ASSESSMENT_CASES = [
    {
        "id": "assessment_lesson_scope_5q",
        "input": {
            "legal_topic": "Contract Law",
            "level": "beginner",
            "scope": "lesson",
            "title": "Introduction to Contract Formation",
            "content_summary": "Covers offer, acceptance, consideration, and mutual assent as the four elements of a valid contract.",
            "question_count": 5,
            "user_mastery": 0.2,
            "questions": [],
            "error": None,
        },
        "extra_checks": lambda s: [
            check_question_count(s, 5),
        ],
    },
    {
        "id": "assessment_module_scope_10q_high_mastery",
        "input": {
            "legal_topic": "Evidence",
            "level": "advanced",
            "scope": "module",
            "title": "Federal Rules of Evidence",
            "content_summary": "Comprehensive review of FRE 401-803 covering relevance, privileges, witnesses, opinions, and hearsay.",
            "question_count": 10,
            "user_mastery": 0.85,
            "questions": [],
            "error": None,
        },
        "extra_checks": lambda s: [
            check_question_count(s, 10),
        ],
    },
]

FEEDBACK_CASES = [
    {
        "id": "feedback_passed_perfect",
        "input": {
            "legal_topic": "Contract Law",
            "score": 1.0,
            "passed": True,
            "results": [
                {
                    "question": "Which of the following is NOT required for a valid contract?",
                    "options": ["Offer", "Acceptance", "Consideration", "Writing"],
                    "correct_answer": 3,
                    "user_answer": 3,
                    "is_correct": True,
                }
            ],
            "next_action": "next_lesson",
            "feedback": "",
            "error": None,
        },
        "extra_checks": lambda s: [
            check_feedback_mentions_score(s, 100),
            check_feedback_tone_for_pass(s, True),
        ],
    },
    {
        "id": "feedback_failed_50pct",
        "input": {
            "legal_topic": "Evidence",
            "score": 0.5,
            "passed": False,
            "results": [
                {
                    "question": "What is the primary purpose of FRE 403?",
                    "options": ["Exclude hearsay", "Balance probative vs prejudicial value", "Authenticate documents", "Qualify experts"],
                    "correct_answer": 1,
                    "user_answer": 0,
                    "is_correct": False,
                },
                {
                    "question": "Which exception covers present sense impressions?",
                    "options": ["FRE 801", "FRE 803(1)", "FRE 804(b)(1)", "FRE 807"],
                    "correct_answer": 1,
                    "user_answer": 2,
                    "is_correct": False,
                },
                {
                    "question": "Hearsay is defined as an out-of-court statement offered to prove…",
                    "options": ["Relevance", "The truth of the matter asserted", "Character", "Habit"],
                    "correct_answer": 1,
                    "user_answer": 1,
                    "is_correct": True,
                },
                {
                    "question": "Which rule governs lay witness opinion testimony?",
                    "options": ["FRE 701", "FRE 702", "FRE 601", "FRE 611"],
                    "correct_answer": 0,
                    "user_answer": 0,
                    "is_correct": True,
                },
            ],
            "next_action": "retry_assessment",
            "feedback": "",
            "error": None,
        },
        "extra_checks": lambda s: [
            check_feedback_mentions_score(s, 50),
            check_feedback_tone_for_pass(s, False),
        ],
    },
    {
        "id": "feedback_passed_borderline",
        "input": {
            "legal_topic": "Tort Law",
            "score": 0.7,
            "passed": True,
            "results": [
                {"question": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": 0, "user_answer": 0, "is_correct": True},
                {"question": "Q2", "options": ["A", "B", "C", "D"], "correct_answer": 1, "user_answer": 1, "is_correct": True},
                {"question": "Q3", "options": ["A", "B", "C", "D"], "correct_answer": 2, "user_answer": 1, "is_correct": False},
                {"question": "Q4", "options": ["A", "B", "C", "D"], "correct_answer": 0, "user_answer": 0, "is_correct": True},
                {"question": "Q5", "options": ["A", "B", "C", "D"], "correct_answer": 3, "user_answer": 2, "is_correct": False},
                {"question": "Q6", "options": ["A", "B", "C", "D"], "correct_answer": 1, "user_answer": 1, "is_correct": True},
                {"question": "Q7", "options": ["A", "B", "C", "D"], "correct_answer": 2, "user_answer": 2, "is_correct": True},
                {"question": "Q8", "options": ["A", "B", "C", "D"], "correct_answer": 0, "user_answer": 0, "is_correct": True},
                {"question": "Q9", "options": ["A", "B", "C", "D"], "correct_answer": 1, "user_answer": 0, "is_correct": False},
                {"question": "Q10", "options": ["A", "B", "C", "D"], "correct_answer": 3, "user_answer": 3, "is_correct": True},
            ],
            "next_action": "next_lesson",
            "feedback": "",
            "error": None,
        },
        "extra_checks": lambda s: [
            check_feedback_mentions_score(s, 70),
            check_feedback_tone_for_pass(s, True),
        ],
    },
]


# ===========================================================================
# Runner
# ===========================================================================

def run_case(
    graph,
    case: dict,
    suite: str,
    base_checks: list[Callable],
    verbose: bool = False,
) -> CaseResult:
    start = time.perf_counter()
    try:
        output = graph.invoke(case["input"])
        latency = time.perf_counter() - start
    except Exception:
        latency = time.perf_counter() - start
        err = traceback.format_exc()
        return CaseResult(case["id"], suite, False, latency, error=err)

    checks: list[CheckResult] = []

    # Base structural checks
    for fn in base_checks:
        checks.append(fn(output))

    # Case-specific extra checks
    if "extra_checks" in case:
        checks.extend(case["extra_checks"](output))

    passed = all(c.passed for c in checks) and output.get("error") is None

    result = CaseResult(
        case_id=case["id"],
        suite=suite,
        passed=passed,
        latency_s=latency,
        checks=checks,
        output=output if verbose else None,
    )
    return result


def run_suite(
    name: str,
    graph,
    cases: list[dict],
    base_checks: list[Callable],
    verbose: bool = False,
) -> list[CaseResult]:
    results = []
    print(f"\n{'='*60}")
    print(f"  SUITE: {name.upper()}  ({len(cases)} cases)")
    print(f"{'='*60}")

    for case in cases:
        print(f"  ▶ {case['id']} ...", end=" ", flush=True)
        r = run_case(graph, case, name, base_checks, verbose)
        icon = "✅" if r.passed else "❌"
        print(f"{icon}  ({r.latency_s:.1f}s | score={r.score:.0%})")

        if not r.passed or verbose:
            for c in r.checks:
                status = "  ✓" if c.passed else "  ✗"
                print(f"      {status} {c.name}: {c.detail}")
            if r.error:
                print(f"      ERROR: {r.error[:300]}")

        if verbose and r.output:
            print("      OUTPUT SNIPPET:")
            snippet = json.dumps(r.output, indent=2, default=str)
            print(textwrap.indent(snippet[:800], "        "))

        results.append(r)

    return results


def print_summary(all_results: list[CaseResult]) -> None:
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")

    suites: dict[str, list[CaseResult]] = {}
    for r in all_results:
        suites.setdefault(r.suite, []).append(r)

    total_passed = sum(r.passed for r in all_results)
    total = len(all_results)

    for suite_name, results in suites.items():
        p = sum(r.passed for r in results)
        avg_score = sum(r.score for r in results) / len(results)
        avg_latency = sum(r.latency_s for r in results) / len(results)
        print(f"  {suite_name:<20} {p}/{len(results)} passed  avg_score={avg_score:.0%}  avg_latency={avg_latency:.1f}s")

    print(f"\n  TOTAL: {total_passed}/{total} cases passed")
    print()


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["lesson", "assessment", "feedback"], help="Run a single suite")
    parser.add_argument("--verbose", action="store_true", help="Print full outputs and all check details")
    args = parser.parse_args()

    lesson_graph, assessment_graph, feedback_graph = _import_graphs()

    # Base checks per suite
    LESSON_BASE = [
        check_no_error,
        lambda s: check_field_non_empty(s, "content"),
        lambda s: check_min_length(s, "content", 200),
        lambda s: check_field_non_empty(s, "key_terms"),
        check_key_terms_structure,
    ]

    ASSESSMENT_BASE = [
        check_no_error,
        lambda s: check_field_non_empty(s, "questions"),
        check_question_schema,
        check_options_count,
        check_correct_index_in_range,
        lambda s: check_list_min_count(s, "questions", 1),
    ]

    FEEDBACK_BASE = [
        check_no_error,
        lambda s: check_field_non_empty(s, "feedback"),
        lambda s: check_min_length(s, "feedback", 50),
    ]

    all_results: list[CaseResult] = []

    if args.suite in (None, "lesson"):
        all_results += run_suite("lesson", lesson_graph, LESSON_CASES, LESSON_BASE, args.verbose)

    if args.suite in (None, "assessment"):
        all_results += run_suite("assessment", assessment_graph, ASSESSMENT_CASES, ASSESSMENT_BASE, args.verbose)

    if args.suite in (None, "feedback"):
        all_results += run_suite("feedback", feedback_graph, FEEDBACK_CASES, FEEDBACK_BASE, args.verbose)

    print_summary(all_results)

    # Exit non-zero if any case failed (useful for CI)
    failed = [r for r in all_results if not r.passed]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()