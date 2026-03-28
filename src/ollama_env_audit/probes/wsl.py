"""WSL probe implementation."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, Severity
from ollama_env_audit.domain.models import Observation, WSLInfo
from ollama_env_audit.domain.protocols import CommandExecutor

from .base import BaseProbe


class WSLProbe(BaseProbe):
    name = "wsl"

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        super().__init__(executor, config)

    def run(self) -> WSLInfo:
        if platform.system() != "Linux":
            return WSLInfo(
                status=ProbeStatus.UNAVAILABLE,
                observations=[
                    Observation(
                        severity=Severity.WARNING,
                        message="WSL inspection only runs from a Linux environment.",
                    )
                ],
            )

        kernel_result = self._executor.execute(["uname", "-r"], timeout=self._config.commands.timeout_seconds)
        kernel = kernel_result.stdout.strip() if kernel_result.succeeded else None
        is_wsl = bool(os.environ.get("WSL_INTEROP") or (kernel and "microsoft" in kernel.lower()))

        distribution = self._read_distribution()
        devices = {path: Path(path).exists() for path in ("/dev/dxg", "/dev/kfd", "/dev/dri")}
        tools = {name: shutil.which(name) is not None for name in ("rocminfo", "rocm-smi", "vulkaninfo")}
        gpu_support_likely = bool(is_wsl and any(devices.values()) and any(tools.values()))

        observations: list[Observation] = []
        status = ProbeStatus.OK if is_wsl else ProbeStatus.WARNING
        if not is_wsl:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="Current Linux environment does not look like WSL2.",
                    evidence=kernel,
                )
            )
        if is_wsl and not any(devices.values()):
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="No GPU-relevant WSL device nodes were detected.",
                )
            )
        if is_wsl and any(devices.values()) and not any(tools.values()):
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="GPU device nodes exist, but ROCm/Vulkan user-space tools were not found.",
                )
            )

        return WSLInfo(
            status=status,
            distribution=distribution,
            kernel=kernel,
            is_wsl=is_wsl,
            devices=devices,
            tools=tools,
            gpu_support_likely=gpu_support_likely,
            observations=observations,
        )

    @staticmethod
    def _read_distribution() -> str | None:
        os_release = Path("/etc/os-release")
        if not os_release.exists():
            return None
        data: dict[str, str] = {}
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key] = value.strip().strip('"')
        return data.get("PRETTY_NAME") or data.get("NAME")
