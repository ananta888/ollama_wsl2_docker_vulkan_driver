"""Ollama probe implementation."""

from __future__ import annotations

import re
from collections.abc import Iterable

import httpx

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import ProbeStatus, Severity
from ollama_env_audit.domain.models import Observation, OllamaInfo, OllamaProcessInfo
from ollama_env_audit.domain.protocols import CommandExecutor

from .base import BaseProbe


class OllamaProbe(BaseProbe):
    name = "ollama"

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        super().__init__(executor, config)

    def run(self) -> OllamaInfo:
        observations: list[Observation] = []
        version_result = self._executor.execute(["ollama", "--version"], timeout=self._config.commands.timeout_seconds)
        binary_available = version_result.succeeded
        version = self._extract_version(version_result.stdout) if binary_available else None
        if not binary_available:
            observations.append(
                Observation(
                    severity=Severity.WARNING,
                    message="Ollama binary is not available in the current environment.",
                    evidence=version_result.stderr.strip() or version_result.error_type,
                )
            )

        api_reachable = None
        try:
            response = httpx.get(
                f"{self._config.ollama.base_url.rstrip('/')}/api/tags",
                timeout=self._config.ollama.timeout_seconds,
            )
            api_reachable = response.status_code == 200
        except httpx.HTTPError as exc:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="Ollama API endpoint is not reachable.",
                    evidence=str(exc),
                )
            )
            api_reachable = False

        running_models: list[OllamaProcessInfo] = []
        accelerator_indicators: list[str] = []
        ps_result = self._executor.execute(["ollama", "ps"], timeout=self._config.commands.timeout_seconds)
        if ps_result.succeeded:
            running_models = parse_ollama_ps(ps_result.stdout)
            accelerator_indicators = [
                process.processor
                for process in running_models
                if process.processor and "gpu" in process.processor.lower()
            ]
        elif binary_available:
            observations.append(
                Observation(
                    severity=Severity.INFO,
                    message="Unable to inspect running Ollama processes.",
                    evidence=ps_result.stderr.strip() or None,
                )
            )

        status = ProbeStatus.OK if binary_available or api_reachable else ProbeStatus.UNAVAILABLE
        return OllamaInfo(
            status=status,
            binary_available=binary_available,
            version=version,
            api_reachable=api_reachable,
            running_models=running_models,
            accelerator_indicators=accelerator_indicators,
            observations=observations,
        )

    @staticmethod
    def _extract_version(raw: str) -> str | None:
        match = re.search(r"(\d+\.\d+\.\d+)", raw)
        return match.group(1) if match else raw.strip() or None


def parse_ollama_ps(raw: str) -> list[OllamaProcessInfo]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if len(lines) < 2:
        return []

    header = re.split(r"\s{2,}", lines[0].strip())
    if "NAME" not in header:
        return []

    results: list[OllamaProcessInfo] = []
    for line in lines[1:]:
        columns = re.split(r"\s{2,}", line.strip())
        if len(columns) < 2:
            continue
        row = dict(zip(header, columns, strict=False))
        results.append(
            OllamaProcessInfo(
                name=row.get("NAME", columns[0]),
                processor=row.get("PROCESSOR"),
                size=row.get("SIZE"),
                until=row.get("UNTIL"),
            )
        )
    return results
