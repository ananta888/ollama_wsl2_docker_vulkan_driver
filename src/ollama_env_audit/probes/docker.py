"""Docker probe implementation."""

from __future__ import annotations

import json

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
        if isinstance(version_payload, dict):
            client = version_payload.get("Client")
            if isinstance(client, dict):
                client_version = client.get("Version")

        info_result = self._executor.execute(
            ["docker", "info", "--format", "{{json .}}"],
            timeout=self._config.commands.long_timeout_seconds,
        )
        info_payload = self._safe_json(info_result.stdout) if info_result.succeeded else None

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

        gpu_support_likely = False
        if isinstance(info_payload, dict):
            security_options = info_payload.get("SecurityOptions") or []
            operating_system = str(info_payload.get("OperatingSystem", ""))
            if "Docker Desktop" in operating_system and any("gpu" in str(item).lower() for item in security_options):
                gpu_support_likely = True

        observations.append(
            Observation(
                severity=Severity.INFO,
                message="Docker GPU support is treated as unverified until explicit container evidence exists.",
            )
        )

        return DockerInfo(
            status=ProbeStatus.OK if info_result.succeeded else ProbeStatus.WARNING,
            version=client_version,
            engine_reachable=True,
            can_run_containers=can_run_containers,
            gpu_support_likely=gpu_support_likely,
            observations=observations,
        )

    @staticmethod
    def _safe_json(raw: str) -> dict | None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None
