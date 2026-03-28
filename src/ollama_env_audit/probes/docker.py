"""Docker probe implementation."""

from __future__ import annotations

import json
from pathlib import Path

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, Severity
from ollama_env_audit.domain.models import DockerInfo, Observation
from ollama_env_audit.domain.protocols import CommandExecutor

from .base import BaseProbe


class DockerProbe(BaseProbe):
    name = "docker"

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        super().__init__(executor, config)

    def run(self) -> DockerInfo:
        observations: list[Observation] = []
        version_result = self._executor.execute(
            ["docker", "version", "--format", "{{json .}}"],
            timeout=self._config.commands.long_timeout_seconds,
        )
        if not version_result.succeeded:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="Docker CLI or engine is not reachable.",
                    evidence=version_result.stderr.strip() or version_result.error_type,
                )
            )
            return DockerInfo(
                status=ProbeStatus.UNAVAILABLE,
                engine_reachable=False,
                observations=observations,
            )

        version_payload = self._safe_json(version_result.stdout)
        client_version = None
        server_version = None
        if isinstance(version_payload, dict):
            client = version_payload.get("Client")
            server = version_payload.get("Server")
            if isinstance(client, dict):
                client_version = client.get("Version")
            if isinstance(server, dict):
                server_version = server.get("Version")

        info_result = self._executor.execute(
            ["docker", "info", "--format", "{{json .}}"],
            timeout=self._config.commands.long_timeout_seconds,
        )
        info_payload = self._safe_json(info_result.stdout) if info_result.succeeded else None
        context_result = self._executor.execute(["docker", "context", "show"], timeout=self._config.commands.timeout_seconds)
        context = context_result.stdout.strip() if context_result.succeeded else None

        can_run_containers: bool | None = None
        if self._config.docker.run_smoke_test:
            inspect_result = self._executor.execute(
                ["docker", "image", "inspect", self._config.docker.smoke_test_image],
                timeout=self._config.commands.timeout_seconds,
            )
            if inspect_result.succeeded:
                run_result = self._executor.execute(
                    ["docker", "run", "--rm", "--pull=never", self._config.docker.smoke_test_image],
                    timeout=self._config.commands.long_timeout_seconds,
                )
                can_run_containers = run_result.succeeded
                if not run_result.succeeded:
                    observations.append(
                        Observation(
                            severity=Severity.WARNING,
                            message="Docker engine is reachable, but the smoke container did not complete successfully.",
                            evidence=run_result.stderr.strip() or None,
                        )
                    )
            else:
                observations.append(
                    Observation(
                        severity=Severity.INFO,
                        message="Docker smoke test was skipped because the local test image is unavailable.",
                        evidence=self._config.docker.smoke_test_image,
                    )
                )

        runtimes: list[str] = []
        gpu_device_candidates = [path for path in ("/dev/dxg", "/dev/kfd", "/dev/dri") if Path(path).exists()]
        gpu_evidence: list[str] = []
        gpu_support_likely = False
        if isinstance(info_payload, dict):
            runtimes_map = info_payload.get("Runtimes") or {}
            if isinstance(runtimes_map, dict):
                runtimes = sorted(str(name) for name in runtimes_map)
            operating_system = str(info_payload.get("OperatingSystem", ""))
            if operating_system:
                gpu_evidence.append(f"Docker operating system: {operating_system}")
            if "Docker Desktop" in operating_system:
                gpu_evidence.append("Docker Desktop detected")
            if runtimes:
                gpu_evidence.append(f"Configured runtimes: {', '.join(runtimes)}")

        for candidate in gpu_device_candidates:
            gpu_evidence.append(f"Host GPU device candidate visible from Linux: {candidate}")

        if gpu_device_candidates and can_run_containers is True:
            gpu_evidence.append("Docker can run local containers while Linux exposes GPU-related device nodes")
            gpu_support_likely = True

        if gpu_support_likely:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="Docker appears capable of container execution with host GPU-related devices present, but actual acceleration remains workload-dependent.",
                )
            )
        else:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="Docker GPU support is treated as unverified until explicit container-level acceleration evidence exists.",
                )
            )

        return DockerInfo(
            status=ProbeStatus.OK if info_result.succeeded else ProbeStatus.WARNING,
            version=client_version,
            server_version=server_version,
            context=context,
            engine_reachable=True,
            can_run_containers=can_run_containers,
            gpu_support_likely=gpu_support_likely,
            runtimes=runtimes,
            gpu_device_candidates=gpu_device_candidates,
            gpu_evidence=gpu_evidence,
            observations=observations,
        )

    @staticmethod
    def _safe_json(raw: str) -> dict | None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
