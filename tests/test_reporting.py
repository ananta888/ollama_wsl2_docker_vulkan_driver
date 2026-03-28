from ollama_env_audit.domain import (
    AuditReport,
    ConfidenceLevel,
    DockerInfo,
    OllamaInfo,
    ProbeStatus,
    Recommendation,
    RuntimeAssessment,
    RuntimeMode,
    WindowsInfo,
    WSLInfo,
)
from ollama_env_audit.reporting import JsonReportRenderer, MarkdownReportRenderer



def make_report() -> AuditReport:
    return AuditReport(
        tool_version="0.1.0",
        windows=WindowsInfo(status=ProbeStatus.OK),
        wsl=WSLInfo(status=ProbeStatus.OK, is_wsl=True),
        docker=DockerInfo(status=ProbeStatus.WARNING, engine_reachable=True),
        ollama=OllamaInfo(status=ProbeStatus.OK, binary_available=True),
        runtime_assessments=[
            RuntimeAssessment(
                mode=RuntimeMode.WINDOWS_NATIVE,
                available=True,
                supports_gpu=False,
                confidence=ConfidenceLevel.MEDIUM,
                reasons=["CPU-only evidence"],
            )
        ],
        recommendation=Recommendation(
            recommended_mode=RuntimeMode.WINDOWS_NATIVE,
            confidence=ConfidenceLevel.MEDIUM,
            rationale=["Most stable path"],
        ),
    )



def test_json_renderer_includes_recommendation() -> None:
    rendered = JsonReportRenderer().render(make_report())

    assert '"recommended_mode": "windows-native"' in rendered



def test_markdown_renderer_includes_sections() -> None:
    rendered = MarkdownReportRenderer().render(make_report())

    assert "# Ollama Environment Audit" in rendered
    assert "## Runtime assessments" in rendered
    assert "windows-native" in rendered
