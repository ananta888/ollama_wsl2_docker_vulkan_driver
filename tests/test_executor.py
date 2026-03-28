from __future__ import annotations

import sys

from ollama_env_audit.infrastructure import SubprocessExecutor



def test_subprocess_executor_runs_command() -> None:
    executor = SubprocessExecutor()
    result = executor.execute([sys.executable, "-c", "print('ok')"], timeout=5)

    assert result.succeeded is True
    assert result.stdout.strip() == "ok"
    assert result.exit_code == 0



def test_subprocess_executor_handles_missing_binary() -> None:
    executor = SubprocessExecutor()
    result = executor.execute(["__definitely_missing_binary__"], timeout=1)

    assert result.succeeded is False
    assert result.error_type == "not-found"
    assert result.exit_code == 127
