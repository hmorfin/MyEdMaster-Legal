import argparse
import json
import os
import time
from datetime import datetime, timezone

import httpx

DEFAULT_URL = os.getenv("AI_SERVICE_URL", "http://ai:8001")
DEFAULT_CASES = "test_cases.json"
ENDPOINT = "/self-assessment/generate-kb"
TIMEOUT = 120


def evaluate_response(response: dict, expected: dict) -> dict:
    checks = {}

    # Classification accuracy against expected
    actual_domain = response.get("legal_domain", "")
    actual_familiarity = response.get("baseline_familiarity", "")
    actual_intent = response.get("primary_intent", "")

    checks["domain_correct"] = actual_domain == expected.get("legal_domain")
    checks["branch_correct"] = response.get("branch") == expected.get("branch")
    checks["familiarity_correct"] = actual_familiarity == expected.get("baseline_familiarity")
    checks["intent_correct"] = actual_intent == expected.get("primary_intent")
    checks["confidence_in_range"] = 0.0 <= float(response.get("confidence", 0)) <= 1.0

    # KB structural quality
    highlights = response.get("global_highlights", [])
    checks["highlights_min_8"] = len(highlights) >= 8
    checks["highlights_count"] = len(highlights)

    few_shot = response.get("few_shot_examples", {})
    checks["few_shot_has_all_dimensions"] = all(
        k in few_shot for k in ["facts", "strategies", "procedures", "rationales", "tutor"]
    )
    checks["few_shot_min_2_per_dimension"] = all(
        len(few_shot.get(k, [])) >= 2
        for k in ["facts", "strategies", "procedures", "rationales"]
    )

    # Example text quality
    example_text = response.get("example_text", "")
    checks["has_example_text"] = bool(example_text)
    checks["example_text_min_length"] = len(example_text) >= 200
    checks["example_text_word_count"] = len(example_text.split())

    # Overall
    binary_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    checks["all_checks_passed"] = all(binary_checks.values())
    checks["checks_passed_count"] = sum(binary_checks.values())
    checks["checks_total"] = len(binary_checks)

    return checks


def run_test_case(
    client: httpx.Client,
    base_url: str,
    case: dict,
    run_id: str,
) -> dict:
    test_id = case["id"]
    description = case["description"]
    payload = case["payload"]
    expected = case.get("expected", {})

    print(f"  Running {test_id}: {description}")

    debug_payload = {**payload, "debug": True}

    start = time.time()
    error = None
    response_data = None
    status_code = None
    llm_calls = []

    try:
        response = client.post(
            f"{base_url}{ENDPOINT}",
            json=debug_payload,
            timeout=TIMEOUT,
        )
        status_code = response.status_code
        response_data = response.json()

        if response.status_code != 200:
            error = f"HTTP {response.status_code}: {response_data}"
            response_data = None
        else:
            llm_calls = response_data.pop("debug_log", None) or []

    except httpx.TimeoutException:
        error = f"Request timed out after {TIMEOUT}s"
    except httpx.HTTPError as e:
        error = f"HTTP error: {str(e)}"
    except Exception as e:
        error = f"Unexpected error: {str(e)}"

    latency_ms = round((time.time() - start) * 1000)

    quality_checks = {}
    if response_data and not error:
        quality_checks = evaluate_response(response_data, expected)
        passed = quality_checks.get("checks_passed_count", 0)
        total = quality_checks.get("checks_total", 0)
        status = "pass" if quality_checks.get("all_checks_passed") else "partial"
        print(f"    SUCCESS - {latency_ms}ms — {passed}/{total} checks passed")
    else:
        status = "error"
        print(f"    FAIL - {latency_ms}ms — ERROR: {error}")

    return {
        "run_id": run_id,
        "test_case_id": test_id,
        "description": description,
        "expected": expected,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "http_status_code": status_code,
        "request_payload": payload,
        "response": response_data,
        "llm_calls": llm_calls,
        "quality_checks": quality_checks,
        "error": error,
    }


def build_summary(results: list[dict], run_id: str, total_ms: int) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    partial = sum(1 for r in results if r["status"] == "partial")
    errors = sum(1 for r in results if r["status"] == "error")

    latencies = [r["latency_ms"] for r in results if r["status"] != "error"]
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    # Per-LLM latency breakdown
    llm_latencies: dict[str, list[int]] = {}
    llm_tokens: dict[str, list[int]] = {}
    for r in results:
        for call in r.get("llm_calls", []):
            llm = call.get("llm", "unknown")
            llm_latencies.setdefault(llm, []).append(call.get("latency_ms", 0))
            llm_tokens.setdefault(llm, []).append(call.get("total_tokens", 0))

    llm_stats = {}
    for llm in llm_latencies:
        lats = llm_latencies[llm]
        toks = llm_tokens[llm]
        llm_stats[llm] = {
            "avg_latency_ms": round(sum(lats) / len(lats)),
            "max_latency_ms": max(lats),
            "avg_tokens": round(sum(toks) / len(toks)),
            "total_tokens": sum(toks),
        }

    # Classification accuracy
    domain_correct = sum(
        1 for r in results
        if r.get("quality_checks", {}).get("domain_correct")
    )
    familiarity_correct = sum(
        1 for r in results
        if r.get("quality_checks", {}).get("familiarity_correct")
    )
    intent_correct = sum(
        1 for r in results
        if r.get("quality_checks", {}).get("intent_correct")
    )
    scored = total - errors

    # Per-check pass rates
    check_names = [
        "domain_correct",
        "branch_correct",
        "familiarity_correct",
        "intent_correct",
        "highlights_min_8",
        "few_shot_has_all_dimensions",
        "few_shot_min_2_per_dimension",
        "has_example_text",
        "example_text_min_length",
    ]
    check_pass_rates = {}
    for check in check_names:
        values = [
            r["quality_checks"].get(check)
            for r in results
            if r.get("quality_checks") and check in r["quality_checks"]
        ]
        if values:
            check_pass_rates[check] = f"{sum(values)}/{len(values)}"

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_test_cases": total,
        "passed": passed,
        "partial": partial,
        "errors": errors,
        "pass_rate": f"{passed}/{total}",
        "classification_accuracy": {
            "domain": f"{domain_correct}/{scored}",
            "familiarity": f"{familiarity_correct}/{scored}",
            "intent": f"{intent_correct}/{scored}",
        },
        "total_run_ms": total_ms,
        "avg_latency_ms": avg_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "llm_stats": llm_stats,
        "check_pass_rates": check_pass_rates,
    }


def main():
    parser = argparse.ArgumentParser(description="Run self-assessment eval suite")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--cases", default=DEFAULT_CASES)
    args = parser.parse_args()

    cases_path = os.path.join(os.path.dirname(__file__), args.cases)
    with open(cases_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = os.path.join(results_dir, f"run_{run_id}.jsonl")
    summary_path = os.path.join(results_dir, f"run_{run_id}_summary.json")

    print(f"\n{'='*60}")
    print(f"  Self-Assessment Eval Run: {run_id}")
    print(f"  Test cases: {len(test_cases)}")
    print(f"  Target: {args.url}{ENDPOINT}")
    print(f"  Output: {results_path}")
    print(f"{'='*60}\n")

    results = []
    run_start = time.time()

    with httpx.Client() as client:
        for case in test_cases:
            result = run_test_case(client, args.url, case, run_id)
            results.append(result)
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

    total_ms = round((time.time() - run_start) * 1000)

    summary = build_summary(results, run_id, total_ms)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  Run complete: {run_id}")
    print(f"  Results: {summary['passed']} passed / {summary['partial']} partial / {summary['errors']} errors")
    print(f"  Classification accuracy:")
    print(f"    Domain:      {summary['classification_accuracy']['domain']}")
    print(f"    Familiarity: {summary['classification_accuracy']['familiarity']}")
    print(f"    Intent:      {summary['classification_accuracy']['intent']}")
    print(f"  Avg latency: {summary['avg_latency_ms']}ms")
    print(f"  LLM breakdown:")
    for llm, stats in summary.get("llm_stats", {}).items():
        print(f"    {llm}: avg {stats['avg_latency_ms']}ms / avg {stats['avg_tokens']} tokens")
    print(f"  Summary saved: {summary_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()