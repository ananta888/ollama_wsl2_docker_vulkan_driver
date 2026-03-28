from __future__ import annotations

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import CommandResult, ProcessLaunchResult
from ollama_env_audit.runtime.launchers import DockerWSLLauncher, WSLNativeLauncher


class FakeExecutor:
    def execute(self, command, *, timeout=None, cwd=None, env=None):
        return CommandResult(command=list(command), exit_code=0, stdout="container123\n")

    def spawn(self, command, *, cwd=None, env=None, stdout_path=None):
        return ProcessLaunchResult(command=list(command), pid=4242)



def test_wsl_launcher_dry_run_returns_plan() -> None:
    launcher = WSLNativeLauncher(FakeExecutor(), AppConfig())

    result = launcher.launch(dry_run=True)

    assert result.status == ProbeStatus.SKIPPED
    assert result.command == ["ollama", "serve"]



def test_docker_launcher_execute_returns_reference() -> None:
    launcher = DockerWSLLauncher(FakeExecutor(), AppConfig())

    result = launcher.launch(dry_run=False)

    assert result.status == ProbeStatus.OK
    assert result.reference == "container123"
