from __future__ import annotations

from typer.testing import CliRunner

from ollama_env_audit.application import InspectionService, RuntimeService, ServiceContainer
from ollama_env_audit.benchmark import BenchmarkService
from ollama_env_audit.cli.app import create_app
from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain import (
    BenchmarkResult,
    DockerInfo,
    OllamaInfo,
    ProbeStatus,
    RuntimeRunResult,
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


class StaticLauncher:
    def __init__(self, mode: RuntimeMode) -> None:
        self.mode = mode

    @property
    def endpoint(self) -> str:
        return "http://127.0.0.1:11434"

    def build_command(self) -> list[str]:
        return ["ollama", "serve"]

    def launch(self, *, dry_run: bool = True) -> RuntimeRunResult:
        return RuntimeRunResult(mode=self.mode, status=ProbeStatus.SKIPPED if dry_run else ProbeStatus.OK, command=self.build_command(), note="planned")


def build_services(_config):
    inspection = InspectionService(
        windows_probe=StaticProbe(WindowsInfo(status=ProbeStatus.OK)),
        wsl_probe=StaticProbe(
            WSLInfo(
                status=ProbeStatus.OK,
                is_wsl=True,
                devices={"/dev/dxg": True},
                vulkan_device_name="llvmpipe (LLVM 20.1.2, 256 bits)",
                vulkan_driver_name="llvmpipe",
                vulkan_uses_cpu=True,
                dzn_icd_present=False,
            )
        ),
        docker_probe=StaticProbe(DockerInfo(status=ProbeStatus.WARNING, engine_reachable=True)),
        ollama_probe=StaticProbe(OllamaInfo(status=ProbeStatus.OK, binary_available=True)),
        recommendation_engine=RecommendationEngine(),
    )
    launchers = {mode: StaticLauncher(mode) for mode in RuntimeMode}
    return ServiceContainer(
        inspection=inspection,
        runtime=RuntimeService(launchers),
        benchmark=BenchmarkService(AppConfig(), launchers),
    )


def test_recommend_command_outputs_mode() -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_services)

    result = runner.invoke(app, ["recommend"])

    assert result.exit_code == 0
    assert "Mode:" in result.stdout
    assert "AMD WSL2 Vulkan" in result.stdout


def test_report_command_writes_json_output(tmp_path) -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_services)
    output = tmp_path / "report.json"

    result = runner.invoke(app, ["report", "--format", "json", "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "recommended_mode" in output.read_text(encoding="utf-8")


def test_run_command_prints_launch_plan() -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_services)

    result = runner.invoke(app, ["run", "--mode", "wsl-native"])

    assert result.exit_code == 0
    assert "Command:" in result.stdout


def test_inspect_command_shows_wsl_vulkan_summary() -> None:
    runner = CliRunner()
    app = create_app(service_factory=build_services)

    result = runner.invoke(app, ["inspect"])

    assert result.exit_code == 0
    assert "WSL Vulkan:" in result.stdout
    assert "AMD WSL2 Vulkan" in result.stdout
