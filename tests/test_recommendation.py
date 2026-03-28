from ollama_env_audit.domain import (
    DockerInfo,
    OllamaInfo,
    ProbeStatus,
    RuntimeMode,
    WindowsInfo,
    WSLInfo,
)
from ollama_env_audit.domain.models import GPUInfo
from ollama_env_audit.recommendation import RecommendationEngine



def test_recommendation_prefers_windows_when_gpu_is_explicit() -> None:
    engine = RecommendationEngine()
    assessments = engine.assess_modes(
        windows=WindowsInfo(status=ProbeStatus.OK, gpus=[GPUInfo(name="Radeon 780M", vendor="AMD")]),
        wsl=WSLInfo(status=ProbeStatus.OK, is_wsl=True, gpu_support_likely=False),
        docker=DockerInfo(status=ProbeStatus.OK, engine_reachable=True, gpu_support_likely=False),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
    )
    recommendation = engine.recommend(assessments)

    assert recommendation.recommended_mode == RuntimeMode.WINDOWS_NATIVE



def test_recommendation_prefers_wsl_when_windows_is_unavailable() -> None:
    engine = RecommendationEngine()
    assessments = engine.assess_modes(
        windows=WindowsInfo(status=ProbeStatus.UNAVAILABLE),
        wsl=WSLInfo(status=ProbeStatus.OK, is_wsl=True, gpu_support_likely=True),
        docker=DockerInfo(status=ProbeStatus.OK, engine_reachable=True, gpu_support_likely=False),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
    )
    recommendation = engine.recommend(assessments)

    assert recommendation.recommended_mode == RuntimeMode.WSL_NATIVE
