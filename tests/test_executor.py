from __future__ import annotations

import sys
import time

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



def test_subprocess_executor_can_spawn_process(tmp_path) -> None:
    executor = SubprocessExecutor()
    log_path = tmp_path / "spawn.log"
    result = executor.spawn([sys.executable, "-c", "import time; time.sleep(0.2)"], stdout_path=log_path)

    assert result.succeeded is True
    assert result.pid is not None
