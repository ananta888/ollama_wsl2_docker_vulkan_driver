"""Application services that orchestrate probes and recommendations."""

from __future__ import annotations

from ollama_env_audit import __version__
from ollama_env_audit.domain.models import AuditReport
from ollama_env_audit.domain.protocols import Probe
from ollama_env_audit.recommendation import RecommendationEngine


class InspectionService:
    """Collects probe results and builds a unified audit report."""

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
