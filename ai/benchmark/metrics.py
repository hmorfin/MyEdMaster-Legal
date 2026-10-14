import statistics
from dataclasses import dataclass, field


@dataclass
class CategoryStats:
    category: str
    n: int

    # Latency (ms)
    latency_p50: float
    latency_p95: float
    latency_mean: float

    # Per-node latency means (ms)
    node_means: dict = field(default_factory=dict)

    # Retrieval
    mean_chunks_above_threshold: float = 0.0
    mean_chunk_score: float = 0.0

    # Cost
    mean_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

    # Quality
    error_rate: float = 0.0           # fraction of runs with errors

    # RAGAS scores (-1.0 = no cases were evaluated)
    mean_faithfulness: float = -1.0
    mean_answer_relevance: float = -1.0


@dataclass
class RunStats:
    tag: str
    n_total: int
    n_errors: int
    by_category: dict = field(default_factory=dict)   # {category: CategoryStats}
    overall: CategoryStats | None = None


def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    return round(statistics.quantiles(data, n=100)[int(pct) - 1], 1)


def _safe_mean(data: list[float]) -> float:
    return round(statistics.mean(data), 2) if data else 0.0


def _node_means(results) -> dict:
    """Compute mean latency per node across a list of BenchmarkResults."""
    acc: dict[str, list[float]] = {}
    for r in results:
        for node, ms in r.node_latencies.items():
            acc.setdefault(node, []).append(ms)
    return {node: round(statistics.mean(vals), 1) for node, vals in acc.items()}


def _ragas_mean(results, attr: str) -> float:
    """Mean of a RAGAS score field, ignoring -1.0 sentinel (not evaluated)."""
    vals = [getattr(r, attr) for r in results if getattr(r, attr) >= 0]
    return _safe_mean(vals) if vals else -1.0


def _category_stats(category: str, results) -> CategoryStats:
    latencies = [r.total_latency_ms for r in results]
    return CategoryStats(
        category=category,
        n=len(results),
        latency_p50=_percentile(latencies, 50),
        latency_p95=_percentile(latencies, 95),
        latency_mean=_safe_mean(latencies),
        node_means=_node_means(results),
        mean_chunks_above_threshold=_safe_mean([r.chunks_above_threshold for r in results]),
        mean_chunk_score=_safe_mean([r.mean_chunk_score for r in results]),
        mean_cost_usd=_safe_mean([r.estimated_cost_usd for r in results]),
        total_cost_usd=round(sum(r.estimated_cost_usd for r in results), 6),
        error_rate=round(sum(1 for r in results if r.has_error) / len(results), 3),
        mean_faithfulness=_ragas_mean(results, "faithfulness_score"),
        mean_answer_relevance=_ragas_mean(results, "answer_relevance_score"),
    )


def aggregate(results: list, tag: str = "run") -> RunStats:
    """Compute RunStats from a list of BenchmarkResult objects."""
    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    cat_stats = {cat: _category_stats(cat, rlist) for cat, rlist in by_cat.items()}
    overall = _category_stats("overall", results)

    return RunStats(
        tag=tag,
        n_total=len(results),
        n_errors=sum(1 for r in results if r.has_error),
        by_category=cat_stats,
        overall=overall,
    )


