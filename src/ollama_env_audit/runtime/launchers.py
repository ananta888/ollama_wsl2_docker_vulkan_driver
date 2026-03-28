"""Runtime launcher implementations."""

from __future__ import annotations

from pathlib import Path

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import RuntimeRunResult
from ollama_env_audit.domain.protocols import CommandExecutor


class BaseRuntimeLauncher:
    mode: RuntimeMode

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        self._executor = executor
        self._config = config

    @property
    def endpoint(self) -> str:
        raise NotImplementedError

    def build_command(self) -> list[str]:
        raise NotImplementedError

    def launch(self, *, dry_run: bool = True) -> RuntimeRunResult:
        command = self.build_command()
        if dry_run:
            return RuntimeRunResult(
                mode=self.mode,
                status=ProbeStatus.SKIPPED,
                endpoint=self.endpoint,
                command=command,
                note="Dry-run only. No runtime process was started.",
                details=["Review the generated command before executing it on your machine."],
            )

        launch_result = self._executor.spawn(
            command,
            stdout_path=Path("/tmp") / f"ollama-env-audit-{self.mode.value}.log",
        )
        if launch_result.succeeded:
            return RuntimeRunResult(
                mode=self.mode,
                status=ProbeStatus.OK,
                endpoint=self.endpoint,
                command=command,
                launched=True,
                reference=str(launch_result.pid),
                note="Runtime launch command started in the background.",
                details=[f"Process id: {launch_result.pid}"],
            )
        return RuntimeRunResult(
            mode=self.mode,
            status=ProbeStatus.ERROR,
            endpoint=self.endpoint,
            command=command,
            note="Runtime launch failed before the process could be started.",
            details=[launch_result.error_type or "unknown launch failure"],
        )


class WindowsNativeLauncher(BaseRuntimeLauncher):
    mode = RuntimeMode.WINDOWS_NATIVE

    @property
    def endpoint(self) -> str:
        return self._config.runtime.windows_base_url

    def build_command(self) -> list[str]:
        return ["powershell.exe", "-NoProfile", "-Command", "ollama serve"]


class WSLNativeLauncher(BaseRuntimeLauncher):
    mode = RuntimeMode.WSL_NATIVE

    @property
    def endpoint(self) -> str:
        return self._config.runtime.wsl_base_url

    def build_command(self) -> list[str]:
        return ["ollama", "serve"]


class DockerWSLLauncher(BaseRuntimeLauncher):
    mode = RuntimeMode.DOCKER_WSL

    @property
    def endpoint(self) -> str:
        return self._config.runtime.docker_base_url

    def build_command(self) -> list[str]:
        command = [
            "docker",
            "run",
            "--rm",
            "--detach",
            "--name",
            self._config.docker.container_name,
            "-p",
            f"{self._config.docker.published_port}:11434",
            "-v",
            f"{self._config.docker.model_cache_volume}:/root/.ollama",
        ]
        for device in ("/dev/dxg", "/dev/kfd", "/dev/dri"):
            if Path(device).exists():
                command.extend(["--device", device])
        command.append(self._config.docker.runtime_image)
        return command

    def launch(self, *, dry_run: bool = True) -> RuntimeRunResult:
        command = self.build_command()
        if dry_run:
            return RuntimeRunResult(
                mode=self.mode,
                status=ProbeStatus.SKIPPED,
                endpoint=self.endpoint,
                command=command,
                note="Dry-run only. No Docker container was started.",
                details=[
                    "Device pass-through flags are included only when host device nodes are visible from Linux.",
                    f"Model cache volume: {self._config.docker.model_cache_volume}",
                ],
            )

        result = self._executor.execute(command, timeout=self._config.commands.long_timeout_seconds)
        if result.succeeded:
            return RuntimeRunResult(
                mode=self.mode,
                status=ProbeStatus.OK,
                endpoint=self.endpoint,
                command=command,
                note="Docker container launch command completed successfully.",
                launched=True,
                reference=result.stdout.strip() or None,
                details=[
                    f"Model cache volume: {self._config.docker.model_cache_volume}",
                    "Validate actual GPU use from inside the container before trusting acceleration.",
                ],
            )
        return RuntimeRunResult(
            mode=self.mode,
            status=ProbeStatus.ERROR,
            endpoint=self.endpoint,
            command=command,
            note="Docker runtime launch failed.",
            details=[result.stderr.strip() or result.error_type or "unknown launch failure"],
        )
