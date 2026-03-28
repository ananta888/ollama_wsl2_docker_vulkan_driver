"""Application services that orchestrate probes, recommendation, runtime launching, and benchmarking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ollama_env_audit import __version__
from ollama_env_audit.benchmark import BenchmarkService
from ollama_env_audit.domain.enums import RuntimeMode
from ollama_env_audit.domain.models import AuditReport, BenchmarkResult, RuntimeRunResult
from ollama_env_audit.domain.protocols import Probe, RuntimeLauncher
from ollama_env_audit.recommendation import RecommendationEngine


class InspectionService:
    """Collect probe results and build a unified audit report."""

    def __init__(
        self,
        windows_probe: Probe,
        wsl_probe: Probe,
        docker_probe: Probe,
        ollama_probe: Probe,
        recommendation_engine: RecommendationEngine,
    ) -> None:
        self._windows_probe = windows_probe
        self._wsl_probe = wsl_probe
        self._docker_probe = docker_probe
        self._ollama_probe = ollama_probe
        self._recommendation_engine = recommendation_engine

    def inspect(self) -> AuditReport:
        windows = self._windows_probe.run()
        wsl = self._wsl_probe.run()
        docker = self._docker_probe.run()
        ollama = self._ollama_probe.run()
        runtime_assessments = self._recommendation_engine.assess_modes(windows, wsl, docker, ollama)
        recommendation = self._recommendation_engine.recommend(runtime_assessments)
        risks = sorted({risk for assessment in runtime_assessments for risk in assessment.risks})
        return AuditReport(
            tool_version=__version__,
            windows=windows,
            wsl=wsl,
            docker=docker,
            ollama=ollama,
            runtime_assessments=runtime_assessments,
            recommendation=recommendation,
            risks=risks,
        )


class RuntimeService:
    """Manage mode-specific launcher interactions."""

    def __init__(self, launchers: Mapping[RuntimeMode, RuntimeLauncher]) -> None:
        self._launchers = dict(launchers)

    def launch(self, mode: RuntimeMode, *, dry_run: bool = True) -> RuntimeRunResult:
        return self._launchers[mode].launch(dry_run=dry_run)


@dataclass(frozen=True)
class ServiceContainer:
    inspection: InspectionService
    runtime: RuntimeService
    benchmark: BenchmarkService
