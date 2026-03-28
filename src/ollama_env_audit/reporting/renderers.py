"""Report renderer implementations."""

from __future__ import annotations

import json

from ollama_env_audit.domain.models import AuditReport, Observation


class JsonReportRenderer:
    def render(self, report: AuditReport) -> str:
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)


class MarkdownReportRenderer:
    def render(self, report: AuditReport) -> str:
        lines = [
            "# Ollama Environment Audit",
            "",
            f"- Generated at: `{report.generated_at.isoformat()}`",
            f"- Recommended mode: `{report.recommendation.recommended_mode.value if report.recommendation.recommended_mode else 'none'}`",
            f"- Confidence: `{report.recommendation.confidence.value}`",
            "",
            "## Recommendation rationale",
            "",
        ]
        lines.extend(f"- {item}" for item in report.recommendation.rationale or ["No recommendation rationale available."])
        if report.recommendation.warnings:
            lines.extend(["", "## Recommendation warnings", ""])
            lines.extend(f"- {item}" for item in report.recommendation.warnings)
        lines.extend(["", "## Probes", ""])
        lines.extend(self._section("Windows", report.windows.status.value, report.windows.observations))
        lines.extend(self._section("WSL", report.wsl.status.value, report.wsl.observations))
        lines.extend(self._section("Docker", report.docker.status.value, report.docker.observations))
        lines.extend(self._section("Ollama", report.ollama.status.value, report.ollama.observations))
        lines.extend(["", "## Runtime assessments", ""])
        for assessment in report.runtime_assessments:
            lines.append(f"### {assessment.mode.value}")
            lines.append("")
            lines.append(f"- Available: `{assessment.available}`")
            lines.append(f"- GPU support: `{assessment.supports_gpu}`")
            lines.append(f"- Confidence: `{assessment.confidence.value}`")
            lines.extend(f"- {item}" for item in assessment.reasons)
            if assessment.risks:
                lines.extend(f"- Risk: {item}" for item in assessment.risks)
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _section(title: str, status: str, observations: list[Observation]) -> list[str]:
        lines = [f"### {title}", "", f"- Status: `{status}`"]
        if observations:
            lines.extend(f"- {item.severity.value}: {item.message}" for item in observations)
        return lines + [""]
