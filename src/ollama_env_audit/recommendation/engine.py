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
        return [
            self._assess_windows_native(windows, ollama),
            self._assess_wsl_native(wsl, ollama),
            self._assess_docker_wsl(docker, wsl, ollama),
        ]

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
        if best_score >= 60 and (best_score - next_score) >= 10:
            confidence = ConfidenceLevel.HIGH
        elif best_score >= 35:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        rationale = list(best.reasons)
        if best.supports_gpu is True:
            rationale.insert(0, "This mode has the strongest explicit GPU evidence in the current inspection.")
        elif best.supports_gpu is False:
            rationale.insert(0, "This mode is usable, but current evidence points to CPU-only or unverified acceleration.")
        return Recommendation(
            recommended_mode=best.mode,
            confidence=confidence,
            rationale=rationale,
            warnings=list(best.risks),
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
        if ollama.server_version:
            reasons.append(f"Ollama API responded with server version {ollama.server_version}.")
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
        if available and wsl.vulkan_uses_cpu:
            supports_gpu = False
        if available and wsl.wsl_dozen_ready:
            supports_gpu = True
        reasons = []
        risks = [obs.message for obs in wsl.observations]
        if available and wsl.gpu_evidence:
            reasons.extend(wsl.gpu_evidence[:3])
        if available and wsl.wsl_dozen_ready:
            reasons.append("WSL Vulkan is already using Mesa Dozen over Microsoft Direct3D12.")
        if available and wsl.gpu_support_likely:
            reasons.append("WSL exposes GPU-relevant devices and at least one supporting user-space tool.")
        elif available:
            reasons.append("WSL is present, but GPU support is incomplete or unverified.")
        else:
            reasons.append("The current Linux environment does not provide verified WSL2 evidence.")
        if ollama.binary_available:
            reasons.append("Ollama is installed in the current Linux environment.")
        if available and wsl.devices.get("/dev/dxg", False) and not wsl.dzn_icd_present:
            risks.append(
                "WSL currently has GPU device visibility but no Dozen Vulkan ICD. Install a Dozen-enabled Mesa build such as ppa:kisak/kisak-mesa and re-run vulkaninfo --summary."
            )
        if available and wsl.vulkan_uses_cpu and wsl.devices.get("/dev/dxg", False):
            risks.append(
                "WSL Vulkan is still resolving to llvmpipe/CPU. The validated remediation in this project is Kisak Mesa plus dzn_icd.json on Ubuntu 24.04."
            )
        confidence = ConfidenceLevel.HIGH if supports_gpu else ConfidenceLevel.MEDIUM if available else ConfidenceLevel.LOW
        return RuntimeAssessment(
            mode=RuntimeMode.WSL_NATIVE,
            available=available,
            supports_gpu=supports_gpu,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
        )

    def _assess_docker_wsl(self, docker: DockerInfo, wsl: WSLInfo, ollama: OllamaInfo) -> RuntimeAssessment:
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
        if docker.gpu_evidence:
            reasons.extend(docker.gpu_evidence[:3])
        if available and docker.can_run_containers and wsl.wsl_dozen_ready:
            supports_gpu = True
            reasons.append("WSL has a validated Mesa Dozen Vulkan path that Docker containers can reuse.")
        elif available and wsl.wsl_dozen_ready:
            reasons.append("WSL has a validated Mesa Dozen Vulkan path; Docker should mount /usr/lib/wsl and use a Dozen-enabled image.")
        if ollama.models_available:
            reasons.append(f"Ollama API currently exposes {len(ollama.models_available)} model(s).")
        if not supports_gpu:
            reasons.append("No explicit Docker GPU evidence was collected; acceleration remains unverified.")
        if wsl.is_wsl and not wsl.gpu_support_likely:
            risks.append("WSL GPU prerequisites are incomplete, which weakens docker-wsl viability.")
        if wsl.is_wsl and wsl.devices.get("/dev/dxg", False) and not wsl.wsl_dozen_ready:
            risks.append(
                "Docker-on-WSL will remain CPU-bound until WSL Vulkan stops using llvmpipe and exposes Mesa Dozen."
            )
        if available and wsl.wsl_dozen_ready:
            risks.append(
                "The validated docker-wsl path requires an image with mesa-vulkan-drivers/Dozen inside the container plus the mount /usr/lib/wsl:/usr/lib/wsl:ro."
            )
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
