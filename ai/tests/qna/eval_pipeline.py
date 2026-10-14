from __future__ import annotations
import argparse
import json
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

def _import_graph():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from graph.builder import legal_graph
    return legal_graph

# Result & Score primitives

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


# Generic check helpers

def check_no_error(state: dict) -> CheckResult:
    err = state.get("error")
    return CheckResult("no_error", err is None, f"error={err!r}")


def check_field_non_empty(state: dict, field_name: str) -> CheckResult:
    val = state.get(field_name)
    ok = bool(val)
    return CheckResult(
        f"{field_name}_non_empty",
        ok,
        f"type={type(val).__name__}, len={len(val) if hasattr(val, '__len__') else 'n/a'}",
    )


def check_min_length(state: dict, field_name: str, min_len: int) -> CheckResult:
    val = state.get(field_name, "")
    ok = isinstance(val, str) and len(val) >= min_len
    return CheckResult(f"{field_name}_min_length_{min_len}", ok, f"actual={len(val)}")


def check_list_min_count(state: dict, field_name: str, min_count: int) -> CheckResult:
    val = state.get(field_name, [])
    ok = isinstance(val, list) and len(val) >= min_count
    return CheckResult(f"{field_name}_min_count_{min_count}", ok, f"actual={len(val)}")


# QnA-specific check helpers

def check_final_answer_non_empty(state: dict) -> CheckResult:
    answer = state.get("final_answer", "")
    ok = bool(answer) and len(answer.strip()) > 0
    return CheckResult("final_answer_non_empty", ok, f"len={len(answer)}")


def check_final_answer_min_length(state: dict, min_len: int = 100) -> CheckResult:
    answer = state.get("final_answer", "")
    ok = isinstance(answer, str) and len(answer) >= min_len
    return CheckResult(f"final_answer_min_length_{min_len}", ok, f"actual={len(answer)}")


def check_not_fallback_message(state: dict) -> CheckResult:
    """Answer should not be the generic error fallback."""
    answer = state.get("final_answer", "").lower()
    fallback_phrases = [
        "could you please rephrase",
        "i wasn't able to generate",
        "ran into an issue",
        "please try again",
    ]
    ok = not any(p in answer for p in fallback_phrases)
    return CheckResult("not_fallback_message", ok, f"answer_start={answer[:80]!r}")


def check_detected_topic_is_list(state: dict) -> CheckResult:
    val = state.get("detected_topic")
    ok = isinstance(val, list)
    return CheckResult("detected_topic_is_list", ok, f"type={type(val).__name__}")


def check_confidence_delta_valid(state: dict) -> CheckResult:
    delta = state.get("confidence_delta")
    ok = isinstance(delta, (int, float)) and 0.0 <= float(delta) <= 1.0
    return CheckResult("confidence_delta_valid", ok, f"value={delta}")


def check_answer_mentions_topic(state: dict, topic: str) -> CheckResult:
    answer = state.get("final_answer", "").lower()
    ok = topic.lower() in answer
    return CheckResult("answer_mentions_topic", ok, f"topic={topic!r}")


def check_detected_topic_contains(state: dict, expected_topic: str) -> CheckResult:
    topics = state.get("detected_topic") or []
    ok = any(expected_topic.lower() in t.lower() for t in topics)
    return CheckResult(
        "detected_topic_contains_expected",
        ok,
        f"expected={expected_topic!r}, actual={topics}",
    )


def check_answer_not_repeat_summary(state: dict, summary: str) -> CheckResult:
    """Answer should not repeat verbatim phrases from the summary."""
    answer = state.get("final_answer", "").lower()
    summary_start = summary[:80].lower()
    ok = summary_start not in answer
    return CheckResult(
        "answer_not_repeat_summary",
        ok,
        f"summary_start={summary_start!r}",
    )


def check_answer_addresses_urgency(state: dict) -> CheckResult:
    """Urgent queries should get a direct substantive answer."""
    answer = state.get("final_answer", "").lower()
    ok = len(answer) >= 150
    return CheckResult("answer_addresses_urgency", ok, f"len={len(answer)}")


def check_llm_response_valid_json_or_text(state: dict) -> CheckResult:
    """llm_response should be a non-empty string."""
    llm_response = state.get("llm_response", "")
    ok = isinstance(llm_response, str) and len(llm_response.strip()) > 0
    return CheckResult("llm_response_non_empty", ok, f"len={len(llm_response)}")


# Base initial state helper

def _base_state(
    query: str,
    user_context: dict | None = None,
    conversation_history: list | None = None,
    self_assessment_context: dict | None = None,
    conversation_summary: str | None = None,
) -> dict:
    return {
        "user_id": "eval_user_001",
        "query": query,
        "chat_id": "eval_chat_001",
        "document_paths": [],
        "document_text": "",
        "document_urls": [],
        "user_context": user_context or {
            "knowledge_level": "beginner",
            "jurisdiction": "Arizona",
            "profession": "Student",
            "mastery_scores": {},
            "conversation_history": conversation_history or [],
            "historical_document_paths": [],
            "is_new_user": False,
        },
        "conversation_history": conversation_history or [],
        "primary_topic": None,
        "self_assessment_context": self_assessment_context or {},
        "conversation_summary": conversation_summary,
        "knowledge_chunks": [],
        "anon_query": "",
        "anon_knowledge": [],
        "anon_document": "",
        "llm_response": "",
        "final_answer": "",
        "detected_topic": None,
        "confidence_delta": None,
        "error": None,
    }


# Test fixtures -- Reasoning suite (standard legal queries)

REASONING_CASES = [
    {
        "id": "reasoning_tenant_rights_beginner",
        "input": _base_state(
            query="My landlord hasn't fixed my heating for two months. What can I do?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Arizona",
                "profession": "Student",
                "mastery_scores": {},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
        ),
        "extra_checks": lambda s: [
            check_answer_mentions_topic(s, "landlord"),
            check_detected_topic_contains(s, "Tenant"),
        ],
    },
    {
        "id": "reasoning_employment_wrongful_termination",
        "input": _base_state(
            query="I was fired after telling HR about workplace harassment. Do I have a case?",
            user_context={
                "knowledge_level": "intermediate",
                "jurisdiction": "California",
                "profession": "Engineer",
                "mastery_scores": {"Employment & Labor Law": 0.4},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
        ),
        "extra_checks": lambda s: [
            check_detected_topic_contains(s, "Employment"),
        ],
    },
    {
        "id": "reasoning_contract_dispute",
        "input": _base_state(
            query="The contractor I hired didn't finish the job but kept the deposit. What are my options?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Texas",
                "profession": "Homeowner",
                "mastery_scores": {},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
        ),
        "extra_checks": lambda s: [
            check_detected_topic_contains(s, "Contract"),
        ],
    },
    {
        "id": "reasoning_criminal_rights",
        "input": _base_state(
            query="I was arrested last night. What are my rights?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Federal",
                "profession": "Student",
                "mastery_scores": {},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
        ),
        "extra_checks": lambda s: [
            check_detected_topic_contains(s, "Criminal"),
        ],
    },
]


# Test fixtures -- FSPR suite (self-assessment context injected)

FSPR_CASES = [
    {
        "id": "fspr_employment_with_evaluation",
        "input": _base_state(
            query="My employer is reducing my hours without warning. Is this legal?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "New York",
                "profession": "Retail Worker",
                "mastery_scores": {"Employment & Labor Law": 0.2},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
            self_assessment_context={
                "legal_domain": "Employment Law",
                "jurisdiction": "New York",
                "legal_situation": "Employer reducing hours without notice",
                "prior_experience": "None",
                "desired_outcome": "Understand my rights",
                "baseline_familiarity": "low",
                "priority_focus": "Strategies - Know-Don't Know",
                "evaluation_report": "User knows they have rights but does not know what specific strategies are available. Most critical gap is in understanding legal remedies and reporting options.",
            },
        ),
        "extra_checks": lambda s: [
            check_detected_topic_contains(s, "Employment"),
        ],
    },
    {
        "id": "fspr_tenant_with_false_knowledge",
        "input": _base_state(
            query="My landlord told me he can enter anytime he wants since he owns the property.",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Florida",
                "profession": "Tenant",
                "mastery_scores": {},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
            self_assessment_context={
                "legal_domain": "Tenant & Landlord Rights",
                "jurisdiction": "Florida",
                "legal_situation": "Landlord claiming right to enter without notice",
                "prior_experience": "None",
                "desired_outcome": "Know my rights as a tenant",
                "baseline_familiarity": "low",
                "priority_focus": "Facts - False Knowledge",
                "evaluation_report": "User has false knowledge about landlord entry rights. Believes landlord can enter freely. Most critical gap is correcting this misconception.",
            },
        ),
        "extra_checks": lambda s: [
            check_answer_mentions_topic(s, "notice"),
            check_detected_topic_contains(s, "Tenant"),
        ],
    },
]


# Test fixtures -- Summary suite (conversation summary injected)

_TENANT_SUMMARY = (
    "User is a tenant in Tempe, Arizona dealing with a broken heater. "
    "Landlord was notified in writing two weeks ago and has not responded. "
    "User has not yet withheld rent or contacted any authorities. "
    "Prior advice covered Arizona landlord-tenant law and the 5-day written notice requirement."
)

SUMMARY_CASES = [
    {
        "id": "summary_followup_with_prior_context",
        "input": _base_state(
            query="What happens if my landlord still doesn't fix it after I send the notice?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Arizona",
                "profession": "Student",
                "mastery_scores": {"Tenant & Landlord Rights": 0.3},
                "conversation_history": [
                    {"role": "user", "content": "My landlord won't fix the heating"},
                    {"role": "llm", "content": "Under Arizona law you must provide written notice giving the landlord 5 days to repair. Has your landlord received written notice?"},
                ],
                "historical_document_paths": [],
                "is_new_user": False,
            },
            conversation_summary=_TENANT_SUMMARY,
        ),
        "extra_checks": lambda s: [
            check_answer_not_repeat_summary(s, _TENANT_SUMMARY),
            check_detected_topic_contains(s, "Tenant"),
        ],
    },
    {
        "id": "summary_new_question_different_topic",
        "input": _base_state(
            query="Also, my employer hasn't paid me for last week. What can I do about that?",
            user_context={
                "knowledge_level": "beginner",
                "jurisdiction": "Arizona",
                "profession": "Student",
                "mastery_scores": {},
                "conversation_history": [],
                "historical_document_paths": [],
                "is_new_user": False,
            },
            conversation_summary=_TENANT_SUMMARY,
        ),
        "extra_checks": lambda s: [
            check_detected_topic_contains(s, "Employment"),
        ],
    },
]


# Test fixtures -- Urgent suite (must answer directly, no clarification)

URGENT_CASES = [
    {
        "id": "urgent_court_date_tomorrow",
        "input": _base_state(
            query="I have a court date tomorrow and I don't know what to do.",
        ),
        "extra_checks": lambda s: [
            check_answer_addresses_urgency(s),
        ],
    },
    {
        "id": "urgent_eviction_notice_received",
        "input": _base_state(
            query="I just got an eviction notice today. I have 3 days to respond.",
        ),
        "extra_checks": lambda s: [
            check_answer_addresses_urgency(s),
            check_detected_topic_contains(s, "Tenant"),
        ],
    },
    {
        "id": "urgent_just_arrested",
        "input": _base_state(
            query="My brother was just arrested 10 minutes ago. What should he do right now?",
        ),
        "extra_checks": lambda s: [
            check_answer_addresses_urgency(s),
            check_detected_topic_contains(s, "Criminal"),
        ],
    },
]


# Test fixtures -- Edge cases

EDGE_CASES = [
    {
        "id": "edge_vague_query",
        "input": _base_state(
            query="can they do that?",
        ),
        "extra_checks": lambda s: [
            check_final_answer_non_empty(s),
        ],
    },
    {
        "id": "edge_non_legal_query",
        "input": _base_state(
            query="What is the weather like in Phoenix?",
        ),
        "extra_checks": lambda s: [
            check_final_answer_non_empty(s),
        ],
    },
    {
        "id": "edge_very_long_query",
        "input": _base_state(
            query=(
                "I have been renting an apartment in Tempe Arizona for the past two years. "
                "My landlord has repeatedly failed to fix the heating system which broke in November. "
                "I have sent three written notices via email and certified mail. "
                "The landlord has ignored all of them. "
                "I also have mold growing in the bathroom which I reported in December. "
                "My lease expires in June 2026 and I am not sure if I want to renew. "
                "I have been paying rent on time every month. "
                "Last week my landlord showed up unannounced and entered my apartment without notice. "
                "I want to know all of my legal options including withholding rent, repair and deduct, "
                "breaking my lease early without penalty, and filing a complaint with the city."
            ),
        ),
        "extra_checks": lambda s: [
            check_final_answer_non_empty(s),
            check_detected_topic_contains(s, "Tenant"),
        ],
    },
    {
        "id": "edge_with_conversation_history",
        "input": _base_state(
            query="What should I do next?",
            conversation_history=[
                {"role": "user", "content": "My landlord raised my rent by 50% with no notice"},
                {"role": "llm", "content": "That sounds like it could be a violation. Which state are you in?"},
                {"role": "user", "content": "I am in California"},
                {"role": "llm", "content": "California has strong tenant protections. In rent-controlled cities, landlords are limited in how much they can raise rent. Has your city enacted rent control?"},
                {"role": "user", "content": "I think so, I am in San Francisco"},
            ],
        ),
        "extra_checks": lambda s: [
            check_final_answer_non_empty(s),
        ],
    },
]


# Runner

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

    for fn in base_checks:
        checks.append(fn(output))

    if "extra_checks" in case:
        checks.extend(case["extra_checks"](output))

    passed = all(c.passed for c in checks)

    return CaseResult(
        case_id=case["id"],
        suite=suite,
        passed=passed,
        latency_s=latency,
        checks=checks,
        output=output if verbose else None,
    )


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
        print(f"   {case['id']} ...", end=" ", flush=True)
        r = run_case(graph, case, name, base_checks, verbose)
        icon = "PASS" if r.passed else "FAIL"
        print(f"{icon}  ({r.latency_s:.1f}s | score={r.score:.0%})")

        if not r.passed or verbose:
            for c in r.checks:
                status = "  PASS" if c.passed else "  FAIL"
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
        print(
            f"  {suite_name:<20} {p}/{len(results)} passed  "
            f"avg_score={avg_score:.0%}  avg_latency={avg_latency:.1f}s"
        )

    print(f"\n  TOTAL: {total_passed}/{total} cases passed")
    print()


# Entry point

def main():
    parser = argparse.ArgumentParser(description="QnA service evaluation pipeline")
    parser.add_argument(
        "--suite",
        choices=["reasoning", "fspr", "summary", "urgent", "edge"],
        help="Run a single suite only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full outputs and all check details",
    )
    args = parser.parse_args()

    legal_graph = _import_graph()

    QNA_BASE = [
        check_no_error,
        check_final_answer_non_empty,
        lambda s: check_final_answer_min_length(s, 50),
        check_not_fallback_message,
        check_detected_topic_is_list,
        check_confidence_delta_valid,
        check_llm_response_valid_json_or_text,
    ]

    all_results: list[CaseResult] = []

    if args.suite in (None, "reasoning"):
        all_results += run_suite("reasoning", legal_graph, REASONING_CASES, QNA_BASE, args.verbose)

    if args.suite in (None, "fspr"):
        all_results += run_suite("fspr", legal_graph, FSPR_CASES, QNA_BASE, args.verbose)

    if args.suite in (None, "summary"):
        all_results += run_suite("summary", legal_graph, SUMMARY_CASES, QNA_BASE, args.verbose)

    if args.suite in (None, "urgent"):
        all_results += run_suite("urgent", legal_graph, URGENT_CASES, QNA_BASE, args.verbose)

    if args.suite in (None, "edge"):
        all_results += run_suite("edge", legal_graph, EDGE_CASES, QNA_BASE, args.verbose)

    print_summary(all_results)

    failed = [r for r in all_results if not r.passed]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()