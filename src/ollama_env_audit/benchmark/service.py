"""Benchmark service for reproducible Ollama API measurements."""

from __future__ import annotations

import time
from collections.abc import Mapping

import httpx

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import BenchmarkResult
from ollama_env_audit.domain.protocols import RuntimeLauncher


class BenchmarkService:
    """Execute deterministic inference benchmarks against an Ollama endpoint."""

    def __init__(self, config: AppConfig, launchers: Mapping[RuntimeMode, RuntimeLauncher]) -> None:
        self._config = config
        self._launchers = dict(launchers)

    def benchmark(self, mode: RuntimeMode, *, model: str | None = None, prompt: str | None = None) -> BenchmarkResult:
        launcher = self._launchers[mode]
        endpoint = launcher.endpoint.rstrip("/")
        selected_model = model or self._config.benchmark.default_model
        selected_prompt = prompt or self._config.benchmark.prompt
        payload = {
            "model": selected_model,
            "prompt": selected_prompt,
            "stream": False,
            "options": {"num_predict": self._config.benchmark.num_predict},
        }

        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{endpoint}/api/generate",
                json=payload,
                timeout=self._config.benchmark.request_timeout_seconds,
            )
            wall_clock = time.perf_counter() - started
        except httpx.HTTPError as exc:
            return BenchmarkResult(
                mode=mode,
                status=ProbeStatus.UNAVAILABLE,
                note="Benchmark could not reach the Ollama API endpoint.",
                model=selected_model,
                endpoint=endpoint,
                observations=[str(exc)],
            )

        if response.status_code != 200:
            return BenchmarkResult(
                mode=mode,
                status=ProbeStatus.WARNING,
                note="Ollama API responded, but the benchmark request did not complete successfully.",
                model=selected_model,
                endpoint=endpoint,
                observations=[response.text[:300]],
                metrics={"http_status": response.status_code},
            )

        try:
            payload = response.json()
        except ValueError:
            return BenchmarkResult(
                mode=mode,
                status=ProbeStatus.ERROR,
                note="Ollama API returned a non-JSON benchmark response.",
                model=selected_model,
                endpoint=endpoint,
                observations=[response.text[:300]],
            )

        eval_count = payload.get("eval_count")
        eval_duration = payload.get("eval_duration")
        total_duration = payload.get("total_duration")
        load_duration = payload.get("load_duration")
        prompt_eval_count = payload.get("prompt_eval_count")
        prompt_eval_duration = payload.get("prompt_eval_duration")
        tokens_per_second = None
        if isinstance(eval_count, int) and isinstance(eval_duration, int) and eval_duration > 0:
            tokens_per_second = round(eval_count / (eval_duration / 1_000_000_000), 2)

        metrics = {
            "wall_clock_seconds": round(wall_clock, 3),
            "tokens_per_second": tokens_per_second,
            "eval_count": eval_count,
            "eval_duration_seconds": _ns_to_seconds(eval_duration),
            "total_duration_seconds": _ns_to_seconds(total_duration),
            "load_duration_seconds": _ns_to_seconds(load_duration),
            "prompt_eval_count": prompt_eval_count,
            "prompt_eval_duration_seconds": _ns_to_seconds(prompt_eval_duration),
            "runtime_classification": _classify_runtime(tokens_per_second),
        }
        note = "Benchmark completed successfully."
        observations = []
        if payload.get("done_reason"):
            observations.append(f"done_reason={payload['done_reason']}")
        if payload.get("response"):
            observations.append(f"sample_response={str(payload['response'])[:120]}")
        return BenchmarkResult(
            mode=mode,
            status=ProbeStatus.OK,
            note=note,
            model=selected_model,
            endpoint=endpoint,
            metrics=metrics,
            observations=observations,
        )


def _ns_to_seconds(value: object) -> float | None:
    if isinstance(value, int):
        return round(value / 1_000_000_000, 6)
    return None


def _classify_runtime(tokens_per_second: float | None) -> str:
    if tokens_per_second is None:
        return "unknown"
    if tokens_per_second >= 40:
        return "fast"
    if tokens_per_second >= 15:
        return "moderate"
    return "slow"
