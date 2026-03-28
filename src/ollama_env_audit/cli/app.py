"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console
from rich.table import Table

from ollama_env_audit.application import InspectionService
from ollama_env_audit.config import AppConfig
from ollama_env_audit.infrastructure import SubprocessExecutor, configure_logging
from ollama_env_audit.probes import DockerProbe, OllamaProbe, WindowsProbe, WSLProbe
from ollama_env_audit.recommendation import RecommendationEngine
from ollama_env_audit.reporting import JsonReportRenderer, MarkdownReportRenderer

ServiceFactory = Callable[[AppConfig], InspectionService]
console = Console()


def create_default_service(config: AppConfig) -> InspectionService:
    executor = SubprocessExecutor()
    return InspectionService(
        windows_probe=WindowsProbe(executor, config),
        wsl_probe=WSLProbe(executor, config),
        docker_probe=DockerProbe(executor, config),
        ollama_probe=OllamaProbe(executor, config),
        recommendation_engine=RecommendationEngine(),
    )


def create_app(service_factory: ServiceFactory | None = None) -> typer.Typer:
    service_builder = service_factory or create_default_service
    app = typer.Typer(help="Audit Ollama runtimes across Windows, WSL2, and Docker.")

    def load_service(config_path: Path | None) -> InspectionService:
        config = AppConfig.from_path(config_path) if config_path else AppConfig()
        return service_builder(config)

    @app.command()
    def inspect(
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
        output_json: bool = typer.Option(False, "--json", help="Render the full report as JSON."),
    ) -> None:
        report = load_service(config_path).inspect()
        if output_json:
            console.print(JsonReportRenderer().render(report))
            return
        table = Table(title="ollama-env-audit inspection")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Notes")
        table.add_row("Windows", report.windows.status.value, ", ".join(obs.message for obs in report.windows.observations) or "n/a")
        table.add_row("WSL", report.wsl.status.value, ", ".join(obs.message for obs in report.wsl.observations) or "n/a")
        table.add_row("Docker", report.docker.status.value, ", ".join(obs.message for obs in report.docker.observations) or "n/a")
        table.add_row("Ollama", report.ollama.status.value, ", ".join(obs.message for obs in report.ollama.observations) or "n/a")
        console.print(table)
        if report.recommendation.recommended_mode:
            console.print(f"Recommended mode: [bold]{report.recommendation.recommended_mode.value}[/bold]")
        else:
            console.print("Recommended mode: [bold]none[/bold]")

    @app.command()
    def recommend(config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file.")) -> None:
        report = load_service(config_path).inspect()
        recommendation = report.recommendation
        console.print(f"Mode: [bold]{recommendation.recommended_mode.value if recommendation.recommended_mode else 'none'}[/bold]")
        console.print(f"Confidence: {recommendation.confidence.value}")
        for item in recommendation.rationale:
            console.print(f"- {item}")
        for item in recommendation.warnings:
            console.print(f"! {item}")

    @app.command()
    def report(
        format: str = typer.Option("markdown", "--format", help="markdown or json"),
        output: Optional[Path] = typer.Option(None, "--output", help="Optional file output path."),
        config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a JSON config file."),
    ) -> None:
        report_obj = load_service(config_path).inspect()
        renderer = MarkdownReportRenderer() if format == "markdown" else JsonReportRenderer()
        rendered = renderer.render(report_obj)
        if output:
            output.write_text(rendered, encoding="utf-8")
            console.print(f"Report written to {output}")
            return
        console.print(rendered)

    return app


app = create_app()


def main() -> None:
    configure_logging()
    app()


if __name__ == "__main__":
    main()
