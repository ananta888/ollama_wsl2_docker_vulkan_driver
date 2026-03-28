"""Windows host probe."""

from __future__ import annotations

import json
from typing import Any

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, Severity
from ollama_env_audit.domain.models import GPUInfo, Observation, WindowsInfo
from ollama_env_audit.domain.protocols import CommandExecutor

from .base import BaseProbe


class WindowsProbe(BaseProbe):
    name = "windows"

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        super().__init__(executor, config)

    def run(self) -> WindowsInfo:
        observations: list[Observation] = []
        os_result = self._run_powershell_json(
            "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber"
        )
        system_result = self._run_powershell_json(
            "Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory"
        )
        cpu_result = self._run_powershell_json(
            "Get-CimInstance Win32_Processor | Select-Object Name"
        )
        gpu_result = self._run_powershell_json(
            "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterCompatibility"
        )
        wsl_status = self._executor.execute(["wsl.exe", "--status"], timeout=self._config.commands.timeout_seconds)
        docker_where = self._executor.execute(["cmd.exe", "/c", "where", "docker"], timeout=self._config.commands.timeout_seconds)

        if os_result is None and cpu_result is None and gpu_result is None:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="Windows host details are not reachable from this environment.",
                    evidence="powershell.exe unavailable or inaccessible",
                )
            )
            return WindowsInfo(status=ProbeStatus.UNAVAILABLE, observations=observations)

        os_info = os_result or {}
        system_info = system_result or {}
        cpu_info = cpu_result or {}
        raw_gpus = gpu_result if isinstance(gpu_result, list) else ([gpu_result] if gpu_result else [])
        gpus = [
            GPUInfo(
                name=item.get("Name", "unknown"),
                vendor=item.get("AdapterCompatibility"),
                driver_version=item.get("DriverVersion"),
            )
            for item in raw_gpus
            if isinstance(item, dict)
        ]

        ram_bytes = system_info.get("TotalPhysicalMemory") if isinstance(system_info, dict) else None
        ram_gb = round(int(ram_bytes) / (1024 ** 3), 2) if isinstance(ram_bytes, (int, str)) else None
        status = ProbeStatus.OK if gpus else ProbeStatus.WARNING
        if not gpus:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="No Windows GPUs were parsed from host telemetry.",
                )
            )
        if not wsl_status.succeeded:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="Unable to verify WSL status from the Windows host.",
                    evidence=wsl_status.stderr.strip() or None,
                )
            )

        return WindowsInfo(
            status=status,
            version=os_info.get("Caption"),
            build=os_info.get("BuildNumber") or os_info.get("Version"),
            cpu=cpu_info.get("Name") if isinstance(cpu_info, dict) else None,
            ram_gb=ram_gb,
            gpus=gpus,
            wsl_installed=wsl_status.succeeded,
            docker_installed=docker_where.succeeded,
            observations=observations,
        )

    def _run_powershell_json(self, script: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        result = self._executor.execute(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"{script} | ConvertTo-Json -Compress",
            ],
            timeout=self._config.commands.timeout_seconds,
        )
        if not result.succeeded or not result.stdout.strip():
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return None
