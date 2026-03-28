from __future__ import annotations

from typer.testing import CliRunner

from ollama_env_audit.application import InspectionService
from ollama_env_audit.cli.app import create_app
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
from ollama_env_audit.recommendation import RecommendationEngine


class StaticProbe:
    name = "static"

    def __init__(self, payload):
        self._payload = payload

    def run(self):
        return self._payload


class StaticInspectionService(InspectionService):
    pass



def build_service(_config):
    return StaticInspectionService(
        windows_probe=StaticProbe(WindowsInfo(status=ProbeStatus.OK)),
        wsl_probe=StaticProbe(WSLInfo(status=ProbeStatus.OK, is_wsl=True)),
        docker_probe=StaticProbe(DockerInfo(status=ProbeStatus.WARNING, engine_reachable=True)),
        ollama_probe=StaticProbe(OllamaInfo(status=ProbeStatus.OK, binary_available=True)),
        recommendation_engine=RecommendationEngine(),
    )



def test_recommend_command_outputs_mode() -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_service)

    result = runner.invoke(app, ["recommend"])

    assert result.exit_code == 0
    assert "Mode:" in result.stdout



def test_report_command_writes_json_output(tmp_path) -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_service)
    output = tmp_path / "report.json"

    result = runner.invoke(app, ["report", "--format", "json", "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "recommended_mode" in output.read_text(encoding="utf-8")
