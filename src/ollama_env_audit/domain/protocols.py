"""Core protocols for dependency inversion."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol, Sequence, TypeVar

from .models import AuditReport, CommandResult

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


class Probe(Protocol[T_co]):
    name: str

    def run(self) -> T_co:
        """Execute the probe and return its typed result."""


class ReportRenderer(Protocol):
    def render(self, report: AuditReport) -> str:
        """Render a report into a string representation."""
