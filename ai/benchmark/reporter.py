import json
import os
from datetime import datetime, timezone
from pathlib import Path

from benchmark.metrics import RunStats, CategoryStats

_RESULTS_DIR = Path(__file__).parent / "results"

def save_json(results: list, tag: str) -> Path:
    """
    Save a list of BenchmarkResult dicts to results/{tag}_{timestamp}.json.
    Returns the path to the saved file.
    """
    _RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = _RESULTS_DIR / f"{tag}_{ts}.json"

    payload = {
        "tag": tag,
        "timestamp": ts,
        "results": [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[BENCHMARK] Results saved → {filename}")
    return filename


def load_json(path: str | Path) -> tuple[str, list]:
    """Load a saved result file. Returns (tag, list_of_result_dicts)."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload["tag"], payload["results"]


def _hr(width: int = 72) -> str:
    return "-" * width


def print_report(results: list, stats: RunStats) -> None:
    """Print a full human-readable benchmark report to stdout."""
    W = 72
    print()
    print(_hr(W))
    print(f"  BENCHMARK REPORT  tag: {stats.tag}")
    print(f"  Cases: {stats.n_total}   Errors: {stats.n_errors}")
    print(_hr(W))

    # Per-case table
    print()
    hdr = f"{'ID':<5} {'Cat':>22} {'Total ms':>9} {'RAG ms':>7} {'Extr ms':>7} {'Rsn ms':>7} {'Chunks':>6} {'Toks-in':>7} {'Cost':>8} {'Faith':>6} {'Relev':>6} {'Err':>4}"
    print(hdr)
    print(_hr(W))

    for r in results:
        nl = r.node_latencies
        err_flag = "Y" if r.has_error else "."
        faith_str = f"{r.faithfulness_score:.3f}" if r.faithfulness_score >= 0 else "  -- "
        relev_str = f"{r.answer_relevance_score:.3f}" if r.answer_relevance_score >= 0 else "  -- "
        row = (
            f"{r.case_id:<5} "
            f"{r.category:>22} "
            f"{r.total_latency_ms:>9.0f} "
            f"{nl.get('rag', 0):>7.0f} "
            f"{nl.get('extraction', 0):>7.0f} "
            f"{nl.get('reasoning', 0):>7.0f} "
            f"{r.chunks_above_threshold:>6} "
            f"{r.estimated_input_tokens:>7} "
            f"${r.estimated_cost_usd:>7.5f} "
            f"{faith_str:>6} "
            f"{relev_str:>6} "
            f"{err_flag:>4}"
        )
        print(row)

    print(_hr(W))

    # Per-category summary
    for cat, cs in stats.by_category.items():
        _print_category_stats(cs)

    # Overall
    if stats.overall:
        _print_category_stats(stats.overall)

    print(_hr(W))
    print()


def _print_category_stats(cs: CategoryStats) -> None:
    print()
    print(f"  [{cs.category.upper()}]  n={cs.n}")
    print(f"    Latency     P50={cs.latency_p50:.0f}ms  P95={cs.latency_p95:.0f}ms  Mean={cs.latency_mean:.0f}ms")

    node_parts = "  ".join(f"{n}={v:.0f}ms" for n, v in sorted(cs.node_means.items()))
    if node_parts:
        print(f"    Nodes       {node_parts}")

    print(f"    Retrieval   above_threshold={cs.mean_chunks_above_threshold:.1f}  mean_score={cs.mean_chunk_score:.3f}")
    print(f"    Cost        mean=${cs.mean_cost_usd:.5f}  total=${cs.total_cost_usd:.5f}")
    print(f"    Error rate  {cs.error_rate:.1%}")
    if cs.mean_faithfulness >= 0 or cs.mean_answer_relevance >= 0:
        faith_str = f"{cs.mean_faithfulness:.3f}" if cs.mean_faithfulness >= 0 else "n/a"
        relev_str = f"{cs.mean_answer_relevance:.3f}" if cs.mean_answer_relevance >= 0 else "n/a"
        print(f"    RAGAS       faithfulness={faith_str}  answer_relevance={relev_str}")

