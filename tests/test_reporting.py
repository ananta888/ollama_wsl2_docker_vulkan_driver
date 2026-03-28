from ollama_env_audit.domain import (
    AuditReport,
    BenchmarkResult,
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
from ollama_env_audit.reporting import HtmlReportRenderer, JsonReportRenderer, MarkdownReportRenderer



def make_report() -> AuditReport:
    return AuditReport(
        tool_version="0.1.0",
        windows=WindowsInfo(status=ProbeStatus.OK),
        wsl=WSLInfo(status=ProbeStatus.OK, is_wsl=True, gpu_evidence=["Device node detected: /dev/dxg"]),
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
        benchmarks=[
            BenchmarkResult(
                mode=RuntimeMode.WINDOWS_NATIVE,
                status=ProbeStatus.OK,
                note="ok",
                metrics={"tokens_per_second": 12.3},
            )
        ],
    )



def test_json_renderer_includes_recommendation() -> None:
    rendered = JsonReportRenderer().render(make_report())

    assert '"recommended_mode": "windows-native"' in rendered



def test_markdown_renderer_includes_benchmarks() -> None:
    rendered = MarkdownReportRenderer().render(make_report())

    assert "# Ollama Environment Audit" in rendered
    assert "## Benchmarks" in rendered
    assert "windows-native" in rendered



def test_html_renderer_includes_json_link() -> None:
    rendered = HtmlReportRenderer().render(make_report())

    assert "/report.json" in rendered
    assert "ollama-env-audit" in rendered
