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
        wsl=WSLInfo(status=ProbeStatus.OK, is_wsl=True, gpu_support_likely=True, gpu_evidence=["Device node detected: /dev/dxg"]),
        docker=DockerInfo(status=ProbeStatus.OK, engine_reachable=True, gpu_support_likely=False),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
    )
    recommendation = engine.recommend(assessments)

    assert recommendation.recommended_mode == RuntimeMode.WSL_NATIVE


def test_recommendation_marks_docker_wsl_gpu_ready_with_dozen() -> None:
    engine = RecommendationEngine()
    assessments = engine.assess_modes(
        windows=WindowsInfo(status=ProbeStatus.UNAVAILABLE),
        wsl=WSLInfo(
            status=ProbeStatus.OK,
            is_wsl=True,
            devices={"/dev/dxg": True},
            gpu_support_likely=True,
            vulkan_device_name="Microsoft Direct3D12 (AMD Radeon(TM) 780M)",
            vulkan_driver_name="Dozen",
            vulkan_uses_cpu=False,
            wsl_lib_directory_present=True,
            dzn_icd_present=True,
            wsl_dozen_ready=True,
            gpu_evidence=["Vulkan driver detected: Dozen"],
        ),
        docker=DockerInfo(
            status=ProbeStatus.OK,
            engine_reachable=True,
            can_run_containers=True,
            gpu_support_likely=False,
        ),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
    )
    docker_assessment = next(item for item in assessments if item.mode == RuntimeMode.DOCKER_WSL)

    assert docker_assessment.supports_gpu is True
    assert any("Mesa Dozen" in reason for reason in docker_assessment.reasons)


def test_recommendation_warns_about_missing_dozen_when_llvmpipe_detected() -> None:
    engine = RecommendationEngine()
    assessments = engine.assess_modes(
        windows=WindowsInfo(status=ProbeStatus.UNAVAILABLE),
        wsl=WSLInfo(
            status=ProbeStatus.OK,
            is_wsl=True,
            devices={"/dev/dxg": True},
            gpu_support_likely=True,
            vulkan_device_name="llvmpipe (LLVM 20.1.2, 256 bits)",
            vulkan_driver_name="llvmpipe",
            vulkan_uses_cpu=True,
            wsl_lib_directory_present=True,
            dzn_icd_present=False,
            wsl_dozen_ready=False,
        ),
        docker=DockerInfo(status=ProbeStatus.OK, engine_reachable=True, can_run_containers=True),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
    )
    wsl_assessment = next(item for item in assessments if item.mode == RuntimeMode.WSL_NATIVE)

    assert wsl_assessment.supports_gpu is False
    assert any("kisak" in risk.lower() or "dozen" in risk.lower() for risk in wsl_assessment.risks)
