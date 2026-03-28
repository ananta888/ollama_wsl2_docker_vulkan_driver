"""Rule-based recommendation engine."""

from __future__ import annotations

from ollama_env_audit.domain.enums import ConfidenceLevel, ProbeStatus, RuntimeMode
from ollama_env_audit.domain.models import (
    DockerInfo,
    OllamaInfo,
    Recommendation,
    RuntimeAssessment,
    WindowsInfo,
    WSLInfo,
)


class RecommendationEngine:
    """Build transparent runtime assessments and a final recommendation."""

    def assess_modes(
        self,
        windows: WindowsInfo,
        wsl: WSLInfo,
        docker: DockerInfo,
        ollama: OllamaInfo,
    ) -> list[RuntimeAssessment]:
        assessments = [
            self._assess_windows_native(windows, ollama),
            self._assess_wsl_native(wsl, ollama),
            self._assess_docker_wsl(docker, wsl),
        ]
        return assessments

    def recommend(self, assessments: list[RuntimeAssessment]) -> Recommendation:
        scored = [(assessment, self._score(assessment)) for assessment in assessments if assessment.available]
        if not scored:
            return Recommendation(
                recommended_mode=None,
                confidence=ConfidenceLevel.LOW,
                rationale=["No runtime mode is currently verifiable from the collected evidence."],
                warnings=["The toolkit could not verify a safe Ollama execution path."],
            )

        scored.sort(key=lambda item: item[1], reverse=True)
        best, best_score = scored[0]
        next_score = scored[1][1] if len(scored) > 1 else 0
        confidence = ConfidenceLevel.HIGH if best_score >= 60 and (best_score - next_score) >= 10 else ConfidenceLevel.MEDIUM if best_score >= 35 else ConfidenceLevel.LOW
        rationale = list(best.reasons)
        if best.supports_gpu is True:
            rationale.insert(0, "This mode has the strongest explicit GPU evidence in the current inspection.")
        elif best.supports_gpu is False:
            rationale.insert(0, "This mode is usable, but current evidence points to CPU-only execution.")
        warnings = list(best.risks)
        return Recommendation(
            recommended_mode=best.mode,
            confidence=confidence,
            rationale=rationale,
            warnings=warnings,
        )

    def _assess_windows_native(self, windows: WindowsInfo, ollama: OllamaInfo) -> RuntimeAssessment:
        available = windows.status != ProbeStatus.UNAVAILABLE
        supports_gpu = bool(windows.gpus) if available else None
        reasons = []
        risks = [obs.message for obs in windows.observations]
        if windows.gpus:
            reasons.append(f"Windows host reported {len(windows.gpus)} GPU adapter(s).")
        else:
            reasons.append("No explicit Windows GPU evidence was collected.")
        if ollama.accelerator_indicators:
            reasons.append("Current Ollama process list includes GPU-labelled processors.")
        confidence = ConfidenceLevel.HIGH if supports_gpu else ConfidenceLevel.MEDIUM if available else ConfidenceLevel.LOW
        return RuntimeAssessment(
            mode=RuntimeMode.WINDOWS_NATIVE,
            available=available,
            supports_gpu=supports_gpu,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
        )

    def _assess_wsl_native(self, wsl: WSLInfo, ollama: OllamaInfo) -> RuntimeAssessment:
        available = wsl.status != ProbeStatus.UNAVAILABLE and wsl.is_wsl
        supports_gpu = wsl.gpu_support_likely if available else None
        reasons = []
        risks = [obs.message for obs in wsl.observations]
        if available and wsl.gpu_support_likely:
            reasons.append("WSL exposes GPU-relevant devices and at least one supporting user-space tool.")
        elif available:
            reasons.append("WSL is present, but GPU support is incomplete or unverified.")
        else:
            reasons.append("The current Linux environment does not provide verified WSL2 evidence.")
        if ollama.binary_available:
            reasons.append("Ollama is installed in the current Linux environment.")
        confidence = ConfidenceLevel.HIGH if supports_gpu else ConfidenceLevel.MEDIUM if available else ConfidenceLevel.LOW
        return RuntimeAssessment(
            mode=RuntimeMode.WSL_NATIVE,
            available=available,
            supports_gpu=supports_gpu,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
        )

    def _assess_docker_wsl(self, docker: DockerInfo, wsl: WSLInfo) -> RuntimeAssessment:
        available = bool(docker.engine_reachable)
        supports_gpu = docker.gpu_support_likely if available else None
        reasons = []
        risks = [obs.message for obs in docker.observations]
        if available and docker.can_run_containers:
            reasons.append("Docker engine is reachable and a local smoke container completed successfully.")
        elif available:
            reasons.append("Docker engine is reachable, but container execution is only partially verified.")
        else:
            reasons.append("Docker engine is not reachable from the current environment.")
        if supports_gpu:
            reasons.append("Docker metadata exposed at least one GPU-related signal.")
        else:
            reasons.append("No explicit Docker GPU evidence was collected; GPU use is treated as unverified.")
        if wsl.is_wsl and not wsl.gpu_support_likely:
            risks.append("WSL GPU prerequisites are incomplete, which weakens docker-wsl viability.")
        confidence = ConfidenceLevel.MEDIUM if available else ConfidenceLevel.LOW
        return RuntimeAssessment(
            mode=RuntimeMode.DOCKER_WSL,
            available=available,
            supports_gpu=supports_gpu,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
        )

    @staticmethod
    def _score(assessment: RuntimeAssessment) -> int:
        if not assessment.available:
            return 0
        score = 20
        if assessment.supports_gpu is True:
            score += 45
        elif assessment.supports_gpu is False:
            score += 10
        else:
            score += 5
        score += {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 10, ConfidenceLevel.HIGH: 20}[assessment.confidence]
        score -= min(len(assessment.risks) * 5, 20)
        return score
