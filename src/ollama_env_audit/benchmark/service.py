"""Benchmark service scaffold."""

from __future__ import annotations

from ollama_env_audit.domain.enums import ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import BenchmarkResult


class BenchmarkService:
    """MVP scaffold for reproducible runtime benchmarks."""

    def benchmark(self, mode: RuntimeMode) -> BenchmarkResult:
        return BenchmarkResult(
            mode=mode,
            status=ProbeStatus.SKIPPED,
            note="TODO: implement reproducible Ollama startup and inference benchmarks.",
        )
