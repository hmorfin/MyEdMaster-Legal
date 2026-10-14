
import argparse
import sys
import os

_AI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_DIR not in sys.path:
    sys.path.insert(0, _AI_DIR)

from benchmark.dataset import BENCHMARK_DATASET
from benchmark.runner import BenchmarkRunner
from benchmark.metrics import aggregate
from benchmark.reporter import print_report, save_json


def main():
    parser = argparse.ArgumentParser(description="Run all benchmark cases")
    parser.add_argument("--no-save", action="store_true", help="Do not save results to JSON")
    args = parser.parse_args()

    n = len(BENCHMARK_DATASET)
    print(f"\n[BENCHMARK] {n} cases")

    runner = BenchmarkRunner()
    runner.setup()

    results = []
    for i, case in enumerate(BENCHMARK_DATASET, 1):
        print(f"  [{i:02d}/{n:02d}] {case.id} — {case.description[:55]}", end="", flush=True)
        result = runner.run(case)
        status = f"  {result.total_latency_ms:.0f}ms"
        if result.has_error:
            status += f"  ERROR: {result.error_msg[:40]}"
        print(status)
        results.append(result)

    stats = aggregate(results, tag="run")
    print_report(results, stats)

    if not args.no_save:
        save_json(results, tag="run")


if __name__ == "__main__":
    main()
