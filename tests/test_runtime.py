from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


def test_docker_launcher_builds_wsl_vulkan_command() -> None:
    launcher = DockerWSLLauncher(FakeExecutor(), AppConfig())

    def fake_exists(path: Path) -> bool:
        normalized = str(path).replace("\\", "/")
        return normalized in {"/usr/lib/wsl", "/dev/dxg"}

    with patch.object(Path, "exists", autospec=True, side_effect=fake_exists):
        command = launcher.build_command()

    assert "-v" in command
    assert "/usr/lib/wsl:/usr/lib/wsl:ro" in command
    assert "LD_LIBRARY_PATH=/usr/lib/wsl/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64" in command
    assert "OLLAMA_VULKAN=1" in command
    assert "VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/dzn_icd.json" in command
    assert "--device" in command
    assert "/dev/dxg" in command
    assert command[-1] == "ollama-wsl-amd:latest"
