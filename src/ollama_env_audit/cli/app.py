"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ollama_env_audit.application import InspectionService, LocalWebService, RuntimeService, ServiceContainer
from ollama_env_audit.benchmark import BenchmarkService
from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.enums import RuntimeMode
from ollama_env_audit.infrastructure import SubprocessExecutor, configure_logging
from ollama_env_audit.probes import DockerProbe, OllamaProbe, WindowsProbe, WSLProbe
from ollama_env_audit.recommendation import RecommendationEngine
from ollama_env_audit.reporting import HtmlReportRenderer, JsonReportRenderer, MarkdownReportRenderer
from ollama_env_audit.runtime import DockerWSLLauncher, WindowsNativeLauncher, WSLNativeLauncher

ServiceFactory = Callable[[AppConfig], ServiceContainer]
console = Console()


def _wsl_status_summary(report) -> str:
    if report.wsl.wsl_dozen_ready:
        return "Dozen on Microsoft Direct3D12"
    if report.wsl.vulkan_uses_cpu:
        return "llvmpipe / CPU fallback"
    if report.wsl.vulkan_driver_name:
        return report.wsl.vulkan_driver_name
    return ", ".join(obs.message for obs in report.wsl.observations) or "n/a"


def _docker_status_summary(report) -> str:
    if report.wsl.wsl_dozen_ready and report.docker.engine_reachable:
        return "Ready with Dozen-enabled image"
    return ", ".join(obs.message for obs in report.docker.observations) or "n/a"


def _remediation_lines(report) -> list[str]:
    if not report.wsl.is_wsl or not report.wsl.devices.get("/dev/dxg", False):
        return []
    if report.wsl.wsl_dozen_ready:
        return [
            "WSL Vulkan already uses Dozen.",
            "For Docker keep /usr/lib/wsl mounted read-only and use a Dozen-enabled image.",
        ]
    if report.wsl.vulkan_uses_cpu or not report.wsl.dzn_icd_present:
        return [
            "Install Dozen-enabled Mesa in Ubuntu, e.g. ppa:kisak/kisak-mesa.",
            "Re-check vulkaninfo until Dozen replaces llvmpipe.",
            "Then rebuild the Docker image with mesa-vulkan-drivers inside the container.",
        ]
    return []


def create_default_services(config: AppConfig) -> ServiceContainer:
    executor = SubprocessExecutor()
    inspection = InspectionService(
        windows_probe=WindowsProbe(executor, config),
        wsl_probe=WSLProbe(executor, config),
        docker_probe=DockerProbe(executor, config),
        ollama_probe=OllamaProbe(executor, config),
        recommendation_engine=RecommendationEngine(),
    )
    launchers = {
        RuntimeMode.WINDOWS_NATIVE: WindowsNativeLauncher(executor, config),
        RuntimeMode.WSL_NATIVE: WSLNativeLauncher(executor, config),
        RuntimeMode.DOCKER_WSL: DockerWSLLauncher(executor, config),
    }
    return ServiceContainer(
        inspection=inspection,
        runtime=RuntimeService(launchers),
        benchmark=BenchmarkService(config, launchers),
    )


def create_app(service_factory: Optional[ServiceFactory] = None) -> typer.Typer:
    service_builder = service_factory or create_default_services
    app = typer.Typer(help="Audit Ollama runtimes across Windows, WSL2, and Docker.")

    def load_services(config_path: Optional[Path]) -> ServiceContainer:
        config = AppConfig.from_path(config_path) if config_path else AppConfig()
        return service_builder(config)

    @app.command()
    def inspect(
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
        output_json: bool = typer.Option(False, "--json", help="Render the full report as JSON."),
    ) -> None:
        report = load_services(config_path).inspection.inspect()
        if output_json:
            console.print(JsonReportRenderer().render(report))
            return
        table = Table(title="ollama-env-audit inspection")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Notes")
        table.add_row("Windows", report.windows.status.value, ", ".join(obs.message for obs in report.windows.observations) or "n/a")
        table.add_row("WSL", report.wsl.status.value, _wsl_status_summary(report))
        table.add_row("Docker", report.docker.status.value, _docker_status_summary(report))
        table.add_row("Ollama", report.ollama.status.value, ", ".join(obs.message for obs in report.ollama.observations) or "n/a")
        console.print(table)
        console.print(f"Recommended mode: [bold]{report.recommendation.recommended_mode.value if report.recommendation.recommended_mode else 'none'}[/bold]")
        if report.wsl.vulkan_device_name or report.wsl.vulkan_driver_name:
            console.print(
                f"WSL Vulkan: device={report.wsl.vulkan_device_name or 'n/a'} | driver={report.wsl.vulkan_driver_name or 'n/a'}"
            )
        remediation = _remediation_lines(report)
        if remediation:
            console.print(Panel("\n".join(f"- {item}" for item in remediation), title="AMD WSL2 Vulkan", expand=False))

    @app.command()
    def recommend(config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file.")) -> None:
        report = load_services(config_path).inspection.inspect()
        recommendation = report.recommendation
        console.print(f"Mode: [bold]{recommendation.recommended_mode.value if recommendation.recommended_mode else 'none'}[/bold]")
        console.print(f"Confidence: {recommendation.confidence.value}")
        for item in recommendation.rationale:
            console.print(f"- {item}")
        for item in recommendation.warnings:
            console.print(f"! {item}")
        remediation = _remediation_lines(report)
        if remediation:
            console.print(Panel("\n".join(f"- {item}" for item in remediation), title="AMD WSL2 Vulkan", expand=False))

    @app.command()
    def report(
        format: str = typer.Option("markdown", "--format", help="markdown, json, or html"),
        output: Optional[Path] = typer.Option(None, "--output", help="Optional file output path."),
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
    ) -> None:
        report_obj = load_services(config_path).inspection.inspect()
        if format == "json":
            renderer = JsonReportRenderer()
        elif format == "html":
            renderer = HtmlReportRenderer()
        else:
            renderer = MarkdownReportRenderer()
        rendered = renderer.render(report_obj)
        if output:
            output.write_text(rendered, encoding="utf-8")
            console.print(f"Report written to {output}")
            return
        console.print(rendered)

    @app.command()
    def benchmark(
        mode: RuntimeMode = typer.Option(..., "--mode", help="Runtime mode to benchmark."),
        model: Optional[str] = typer.Option(None, "--model", help="Override the default Ollama model."),
        prompt: Optional[str] = typer.Option(None, "--prompt", help="Override the default benchmark prompt."),
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
    ) -> None:
        result = load_services(config_path).benchmark.benchmark(mode, model=model, prompt=prompt)
        console.print(f"Benchmark mode: [bold]{mode.value}[/bold]")
        console.print(f"Status: {result.status.value}")
        console.print(result.note)
        for key, value in result.metrics.items():
            console.print(f"- {key}: {value}")
        for item in result.observations:
            console.print(f"- {item}")

    @app.command()
    def run(
        mode: RuntimeMode = typer.Option(..., "--mode", help="Runtime mode to launch."),
        dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Only print the launch plan unless --execute is passed."),
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
    ) -> None:
        result = load_services(config_path).runtime.launch(mode, dry_run=dry_run)
        console.print(f"Run mode: [bold]{mode.value}[/bold]")
        console.print(f"Status: {result.status.value}")
        console.print(f"Endpoint: {result.endpoint}")
        console.print(f"Command: {' '.join(result.command)}")
        console.print(result.note)
        for detail in result.details:
            console.print(f"- {detail}")
        if result.reference:
            console.print(f"Reference: {result.reference}")

    @app.command("serve-web")
    def serve_web(
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host for the local web UI."),
        port: int = typer.Option(8765, "--port", help="Bind port for the local web UI."),
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
    ) -> None:
        services = load_services(config_path)
        console.print(f"Serving web UI on http://{host}:{port}")
        LocalWebService(services.inspection).serve(host, port)

    return app


app = create_app()


def main() -> None:
    configure_logging()
    app()


if __name__ == "__main__":
    main()
