from __future__ import annotations

from ollama_env_audit.benchmark.service import BenchmarkService
from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import RuntimeRunResult


class DummyLauncher:
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self.mode = RuntimeMode.WSL_NATIVE

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def build_command(self) -> list[str]:
        return ["ollama", "serve"]

    def launch(self, *, dry_run: bool = True) -> RuntimeRunResult:
        return RuntimeRunResult(mode=self.mode, status=ProbeStatus.SKIPPED, note="unused")


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload



def test_benchmark_computes_tokens_per_second(monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        return FakeResponse(
            200,
            {
                "eval_count": 120,
                "eval_duration": 4_000_000_000,
                "total_duration": 5_000_000_000,
                "load_duration": 1_000_000_000,
                "prompt_eval_count": 10,
                "prompt_eval_duration": 500_000_000,
                "response": "ok",
                "done_reason": "stop",
            },
        )

    monkeypatch.setattr("ollama_env_audit.benchmark.service.httpx.post", fake_post)
    service = BenchmarkService(AppConfig(), {RuntimeMode.WSL_NATIVE: DummyLauncher("http://127.0.0.1:11434")})

    result = service.benchmark(RuntimeMode.WSL_NATIVE, model="phi4")

    assert result.status == ProbeStatus.OK
    assert result.metrics["tokens_per_second"] == 30.0
    assert result.model == "phi4"
