"""WSL probe implementation."""

from __future__ import annotations

import os
import platform
import re
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
        tool_details: dict[str, str] = {}
        vulkan_device_name: str | None = None
        vulkan_driver_name: str | None = None
        vulkan_uses_cpu: bool | None = None
        if tools["vulkaninfo"]:
            vulkan_result = self._executor.execute(["vulkaninfo", "--summary"], timeout=self._config.commands.timeout_seconds)
            vulkan_output = vulkan_result.stdout.strip() or vulkan_result.stderr.strip()
            tool_details["vulkaninfo"] = self._summarize_output(vulkan_output)
            vulkan_device_name, vulkan_driver_name, vulkan_uses_cpu = self._parse_vulkan_summary(vulkan_output)
        for name in ("rocminfo", "rocm-smi"):
            if tools[name]:
                tool_details[name] = self._tool_summary(name)

        wsl_lib_directory_present = Path("/usr/lib/wsl/lib").exists()
        dzn_icd_present = Path("/usr/share/vulkan/icd.d/dzn_icd.json").exists()
        wsl_dozen_ready = bool(
            is_wsl
            and devices.get("/dev/dxg", False)
            and wsl_lib_directory_present
            and dzn_icd_present
            and vulkan_driver_name
            and vulkan_driver_name.lower() == "dozen"
            and vulkan_device_name
            and "microsoft direct3d12" in vulkan_device_name.lower()
        )

        gpu_evidence: list[str] = []
        for path, exists in devices.items():
            if exists:
                gpu_evidence.append(f"Device node detected: {path}")
        for name, summary in tool_details.items():
            gpu_evidence.append(f"Tool available: {name} ({summary})")
        if wsl_lib_directory_present:
            gpu_evidence.append("WSL shared graphics libraries detected: /usr/lib/wsl/lib")
        if dzn_icd_present:
            gpu_evidence.append("Dozen Vulkan ICD detected: /usr/share/vulkan/icd.d/dzn_icd.json")
        if vulkan_driver_name:
            gpu_evidence.append(f"Vulkan driver detected: {vulkan_driver_name}")
        if vulkan_device_name:
            gpu_evidence.append(f"Vulkan device detected: {vulkan_device_name}")

        gpu_support_likely = bool(
            is_wsl
            and any(devices.values())
            and (
                wsl_dozen_ready
                or any(name in tools and tools[name] for name in ("rocminfo", "rocm-smi"))
                or any(tools.values())
            )
        )
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
        if is_wsl and devices.get("/dev/dxg", False) and not dzn_icd_present:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="WSL sees /dev/dxg, but the Dozen Vulkan ICD is missing.",
                    evidence="Install a Mesa build with Dozen support, for example ppa:kisak/kisak-mesa on Ubuntu 24.04.",
                )
            )
        if is_wsl and devices.get("/dev/dxg", False) and vulkan_uses_cpu:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="Vulkan is falling back to llvmpipe/CPU despite visible WSL GPU devices.",
                    evidence="A Dozen-enabled Mesa build is likely required before Linux or Docker Ollama can use the AMD GPU.",
                )
            )
        if wsl_dozen_ready:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="WSL Vulkan is using Mesa Dozen over Microsoft Direct3D12.",
                    evidence=vulkan_device_name,
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
            vulkan_device_name=vulkan_device_name,
            vulkan_driver_name=vulkan_driver_name,
            vulkan_uses_cpu=vulkan_uses_cpu,
            wsl_lib_directory_present=wsl_lib_directory_present,
            dzn_icd_present=dzn_icd_present,
            wsl_dozen_ready=wsl_dozen_ready,
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
    def _summarize_output(output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines[0][:180] if lines else "no output"

    @staticmethod
    def _parse_vulkan_summary(raw: str) -> tuple[str | None, str | None, bool | None]:
        normalized = raw.replace("\r", "")
        device_match = re.search(r"deviceName\s*=\s*(.+)", normalized)
        driver_match = re.search(r"driverName\s*=\s*(.+)", normalized)
        device_type_match = re.search(r"deviceType\s*=\s*(.+)", normalized)
        device_name = device_match.group(1).strip() if device_match else None
        driver_name = driver_match.group(1).strip() if driver_match else None
        device_type = device_type_match.group(1).strip().lower() if device_type_match else None
        uses_cpu = None
        if device_type is not None:
            uses_cpu = "cpu" in device_type
        elif device_name is not None:
            uses_cpu = "llvmpipe" in device_name.lower()
        return device_name, driver_name, uses_cpu

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
