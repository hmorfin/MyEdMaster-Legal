import sys
import os
from dataclasses import dataclass, fields as dc_fields
from pathlib import Path

_AI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

from benchmark.runner import BenchmarkResult
from benchmark.metrics import RunStats, CategoryStats, aggregate
from benchmark.reporter import load_json

@dataclass
class MetricDiff:
    metric: str
    baseline: float
    new: float
    delta_pct: float      # (new - baseline) / baseline * 100
    direction: str        # "better" | "worse" | "neutral"


def _delta(metric: str, baseline: float, new: float, lower_is_better: bool = True) -> MetricDiff:
    delta = 0.0 if baseline == 0 else (new - baseline) / baseline * 100
    if lower_is_better:
        direction = "better" if delta < -1 else ("worse" if delta > 1 else "neutral")
    else:
        direction = "better" if delta > 1 else ("worse" if delta < -1 else "neutral")
    return MetricDiff(
        metric=metric,
        baseline=round(baseline, 3),
        new=round(new, 3),
        delta_pct=round(delta, 1),
        direction=direction,
    )


def _diff_stats(b: CategoryStats, n: CategoryStats) -> list[MetricDiff]:
    rows = [
        _delta("latency_p50_ms",              b.latency_p50,                n.latency_p50),
        _delta("latency_p95_ms",              b.latency_p95,                n.latency_p95),
        _delta("latency_mean_ms",             b.latency_mean,               n.latency_mean),
        _delta("mean_cost_usd",               b.mean_cost_usd,              n.mean_cost_usd),
        _delta("mean_chunks_above_threshold", b.mean_chunks_above_threshold, n.mean_chunks_above_threshold, False),
        _delta("mean_chunk_score",            b.mean_chunk_score,           n.mean_chunk_score,            False),
        _delta("error_rate",                  b.error_rate,                 n.error_rate),
    ]

    if b.mean_faithfulness >= 0 or n.mean_faithfulness >= 0:
        rows += [
            _delta("mean_faithfulness",     max(b.mean_faithfulness, 0),     max(n.mean_faithfulness, 0),     False),
            _delta("mean_answer_relevance", max(b.mean_answer_relevance, 0), max(n.mean_answer_relevance, 0), False),
        ]

    all_nodes = set(list(b.node_means.keys()) + list(n.node_means.keys()))
    for node in sorted(all_nodes):
        rows.append(_delta(f"node_{node}_ms", b.node_means.get(node, 0.0), n.node_means.get(node, 0.0)))

    return rows


def diff_runs(baseline: RunStats, new: RunStats) -> dict[str, list[MetricDiff]]:
    cats = set(list(baseline.by_category.keys()) + list(new.by_category.keys()) + ["overall"])
    diffs = {}
    for cat in cats:
        b_stats = baseline.by_category.get(cat) or baseline.overall
        n_stats = new.by_category.get(cat) or new.overall
        if b_stats and n_stats:
            diffs[cat] = _diff_stats(b_stats, n_stats)
    return diffs

def _print_diff(diffs: dict[str, list[MetricDiff]], baseline_tag: str, new_tag: str) -> None:
    W = 80
    SYMBOL = {"better": "v better", "worse": "^ WORSE ", "neutral": ". same  "}
    hr = "-" * W

    print()
    print(hr)
    print(f"  DIFF REPORT  baseline: {baseline_tag}  ->  new: {new_tag}")
    print(hr)

    for cat, rows in diffs.items():
        print(f"\n  [{cat.upper()}]")
        print(f"  {'Metric':<35} {'Baseline':>10} {'New':>10} {'Delta%':>8} {'':>10}")
        print("  " + "-" * (W - 2))
        for d in rows:
            print(
                f"  {d.metric:<35} "
                f"{d.baseline:>10.3f} "
                f"{d.new:>10.3f} "
                f"{d.delta_pct:>+8.1f}% "
                f"{SYMBOL.get(d.direction, ''):>10}"
            )

    print()
    print(hr)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _load(path: Path):
    tag, raw_list = load_json(path)
    valid_keys = {f.name for f in dc_fields(BenchmarkResult)}
    results = [BenchmarkResult(**{k: v for k, v in d.items() if k in valid_keys}) for d in raw_list]
    return tag, results


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m benchmark.compare <baseline.json> <new.json>")
        sys.exit(1)

    b_path, n_path = Path(sys.argv[1]), Path(sys.argv[2])
    print(f"[BENCHMARK] Comparing:\n  baseline → {b_path}\n  new      → {n_path}")

    b_tag, b_results = _load(b_path)
    n_tag, n_results = _load(n_path)

    diffs = diff_runs(aggregate(b_results, tag=b_tag), aggregate(n_results, tag=n_tag))
    _print_diff(diffs, b_tag, n_tag)


if __name__ == "__main__":
    main()