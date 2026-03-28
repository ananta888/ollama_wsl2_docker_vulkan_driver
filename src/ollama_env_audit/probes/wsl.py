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
        device_details = {path: self._describe_path(Path(path)) for path in devices}
        tools = {name: shutil.which(name) is not None for name in ("rocminfo", "rocm-smi", "vulkaninfo")}
        tool_details = {
            name: self._tool_summary(name)
            for name, available in tools.items()
            if available
        }

        gpu_evidence: list[str] = []
        for path, exists in devices.items():
            if exists:
                gpu_evidence.append(f"Device node detected: {path}")
        for name, summary in tool_details.items():
            gpu_evidence.append(f"Tool available: {name} ({summary})")

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
        if is_wsl and gpu_support_likely:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="WSL exposes both GPU-related devices and at least one supporting user-space tool.",
                )
            )

        return WSLInfo(
            status=status,
            distribution=distribution,
            kernel=kernel,
            is_wsl=is_wsl,
            devices=devices,
            device_details=device_details,
            tools=tools,
            tool_details=tool_details,
            gpu_support_likely=gpu_support_likely,
            gpu_evidence=gpu_evidence,
            observations=observations,
        )

    def _tool_summary(self, executable: str) -> str:
        if executable == "vulkaninfo":
            result = self._executor.execute([executable, "--summary"], timeout=self._config.commands.timeout_seconds)
        elif executable == "rocm-smi":
            result = self._executor.execute([executable, "--showproductname"], timeout=self._config.commands.timeout_seconds)
        else:
            result = self._executor.execute([executable], timeout=self._config.commands.timeout_seconds)

        if result.stdout.strip():
            return result.stdout.strip().splitlines()[0][:180]
        if result.stderr.strip():
            return result.stderr.strip().splitlines()[0][:180]
        return "no output"

    @staticmethod
    def _describe_path(path: Path) -> str:
        if not path.exists():
            return "missing"
        try:
            stat = path.stat()
        except OSError:
            return "present"
        return f"present mode={oct(stat.st_mode & 0o777)}"

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
