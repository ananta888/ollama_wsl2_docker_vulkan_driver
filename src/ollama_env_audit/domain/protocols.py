"""Core protocols for dependency inversion."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol, Sequence, TypeVar

from .enums import RuntimeMode
from .models import AuditReport, BenchmarkResult, CommandResult, ProcessLaunchResult, RuntimeRunResult

T_co = TypeVar("T_co", covariant=True)


class CommandExecutor(Protocol):
    def execute(
        self,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        """Execute a command and return a structured result."""

    def spawn(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        stdout_path: Path | None = None,
    ) -> ProcessLaunchResult:
        """Start a background process and return launch metadata."""


class Probe(Protocol[T_co]):
    name: str

    def run(self) -> T_co:
        """Execute the probe and return its typed result."""


class ReportRenderer(Protocol):
    def render(self, report: AuditReport) -> str:
        """Render a report into a string representation."""


class RuntimeLauncher(Protocol):
    mode: RuntimeMode

    @property
    def endpoint(self) -> str:
        """Return the endpoint that should be used for this runtime."""

    def build_command(self) -> list[str]:
        """Return the command used to launch the runtime."""

    def launch(self, *, dry_run: bool = True) -> RuntimeRunResult:
        """Launch or describe launching the runtime."""


class BenchmarkRunner(Protocol):
    def benchmark(self, mode: RuntimeMode, *, model: str | None = None, prompt: str | None = None) -> BenchmarkResult:
        """Execute a benchmark for the selected runtime mode."""
