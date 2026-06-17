"""The end-to-end runner: dataset + model client -> BenchmarkResult."""

from .adapter import run_case
from .client import ModelClient
from .models import BenchmarkResult, GoldRecord
from .scorer import score_case


def run_benchmark(dataset: list[GoldRecord], client: ModelClient) -> BenchmarkResult:
    outcomes = [score_case(record, run_case(record, client)) for record in dataset]
    return BenchmarkResult(outcomes=outcomes)
