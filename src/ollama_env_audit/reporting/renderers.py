"""Report renderer implementations."""

from __future__ import annotations

import json
from html import escape

from ollama_env_audit.domain.models import AuditReport, BenchmarkResult, Observation


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
            "## Headline findings",
            "",
        ]
        lines.extend(f"- {item}" for item in self._headline_findings(report))
        lines.extend(["", "## Recommendation rationale", ""])
        lines.extend(f"- {item}" for item in report.recommendation.rationale or ["No recommendation rationale available."])
        if report.recommendation.warnings:
            lines.extend(["", "## Recommendation warnings", ""])
            lines.extend(f"- {item}" for item in report.recommendation.warnings)
        if report.risks:
            lines.extend(["", "## Global risks", ""])
            lines.extend(f"- {item}" for item in report.risks)
        remediation = self._wsl_vulkan_remediation(report)
        if remediation:
            lines.extend(["", "## AMD WSL2 Vulkan remediation", ""])
            lines.extend(f"- {item}" for item in remediation)
        lines.extend(["", "## Probes", ""])
        lines.extend(self._section("Windows", report.windows.status.value, report.windows.observations))
        lines.extend(self._section("WSL", report.wsl.status.value, report.wsl.observations, report.wsl.gpu_evidence))
        lines.extend(self._section("Docker", report.docker.status.value, report.docker.observations, report.docker.gpu_evidence))
        lines.extend(self._section("Ollama", report.ollama.status.value, report.ollama.observations, report.ollama.models_available))
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
        if report.benchmarks:
            lines.extend(["## Benchmarks", ""])
            for benchmark in report.benchmarks:
                lines.extend(self._benchmark_section(benchmark))
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _section(title: str, status: str, observations: list[Observation], evidence: list[str] | None = None) -> list[str]:
        lines = [f"### {title}", "", f"- Status: `{status}`"]
        if observations:
            lines.extend(f"- {item.severity.value}: {item.message}" for item in observations)
        if evidence:
            lines.extend(f"- Evidence: {item}" for item in evidence)
        return lines + [""]

    @staticmethod
    def _benchmark_section(benchmark: BenchmarkResult) -> list[str]:
        lines = [f"### Benchmark {benchmark.mode.value}", "", f"- Status: `{benchmark.status.value}`", f"- Note: {benchmark.note}"]
        if benchmark.model:
            lines.append(f"- Model: `{benchmark.model}`")
        if benchmark.endpoint:
            lines.append(f"- Endpoint: `{benchmark.endpoint}`")
        for key, value in benchmark.metrics.items():
            lines.append(f"- {key}: `{value}`")
        for observation in benchmark.observations:
            lines.append(f"- Observation: {observation}")
        lines.append("")
        return lines

    @staticmethod
    def _headline_findings(report: AuditReport) -> list[str]:
        findings: list[str] = []
        if report.wsl.wsl_dozen_ready:
            findings.append("WSL Vulkan is GPU-backed via `Dozen` on `Microsoft Direct3D12`.")
        elif report.wsl.vulkan_uses_cpu:
            findings.append("WSL Vulkan is currently falling back to `llvmpipe`/CPU.")
        if report.wsl.vulkan_device_name:
            findings.append(f"WSL Vulkan device: `{report.wsl.vulkan_device_name}`")
        if report.wsl.vulkan_driver_name:
            findings.append(f"WSL Vulkan driver: `{report.wsl.vulkan_driver_name}`")
        if report.docker.can_run_containers and report.wsl.wsl_dozen_ready:
            findings.append("`docker-wsl` can reuse the validated WSL Vulkan path when the container image includes Mesa Dozen support.")
        return findings or ["No standout GPU findings were captured."]

    @staticmethod
    def _wsl_vulkan_remediation(report: AuditReport) -> list[str]:
        if not report.wsl.is_wsl or not report.wsl.devices.get("/dev/dxg", False):
            return []
        if report.wsl.wsl_dozen_ready:
            return [
                "Use a container image with `mesa-vulkan-drivers` from `ppa:kisak/kisak-mesa`.",
                "Mount `/usr/lib/wsl:/usr/lib/wsl:ro` into the container.",
                "Set `OLLAMA_VULKAN=1` and `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/dzn_icd.json`.",
            ]
        if report.wsl.vulkan_uses_cpu or not report.wsl.dzn_icd_present:
            return [
                "Install a Dozen-enabled Mesa build in Ubuntu, for example `ppa:kisak/kisak-mesa` on Ubuntu 24.04.",
                "Verify `/usr/share/vulkan/icd.d/dzn_icd.json` exists after the Mesa upgrade.",
                "Re-run `vulkaninfo --summary` until the device changes from `llvmpipe` to `Microsoft Direct3D12 (...)` with driver `Dozen`.",
                "Only then expect Ollama in Docker-on-WSL to reach the AMD GPU.",
            ]
        return []


class HtmlReportRenderer:
    def render(self, report: AuditReport) -> str:
        headline_findings = "".join(
            f"<li>{escape(item)}</li>" for item in MarkdownReportRenderer._headline_findings(report)
        )
        recommendation_warnings = "".join(
            f"<li>{escape(item)}</li>" for item in report.recommendation.warnings
        )
        remediation = "".join(
            f"<li>{escape(item)}</li>" for item in MarkdownReportRenderer._wsl_vulkan_remediation(report)
        )
        assessments = "".join(
            f"<li><strong>{escape(assessment.mode.value)}</strong> - available={assessment.available}, gpu={assessment.supports_gpu}, confidence={escape(assessment.confidence.value)}<ul>"
            + "".join(f"<li>{escape(reason)}</li>" for reason in assessment.reasons)
            + "".join(f"<li>Risk: {escape(risk)}</li>" for risk in assessment.risks)
            + "</ul></li>"
            for assessment in report.runtime_assessments
        )
        benchmarks = "".join(
            f"<li><strong>{escape(item.mode.value)}</strong> - {escape(item.note)}<ul>"
            + "".join(f"<li>{escape(str(key))}: {escape(str(value))}</li>" for key, value in item.metrics.items())
            + "</ul></li>"
            for item in report.benchmarks
        ) or "<li>No benchmarks recorded yet.</li>"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ollama-env-audit</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; max-width: 1000px; }}
    code {{ background: #f2f2f2; padding: 0.1rem 0.3rem; }}
    .card {{ border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>ollama-env-audit</h1>
  <p>Generated at <code>{escape(report.generated_at.isoformat())}</code></p>
  <div class="card">
    <h2>Recommendation</h2>
    <p>Mode: <code>{escape(report.recommendation.recommended_mode.value if report.recommendation.recommended_mode else 'none')}</code></p>
    <p>Confidence: <code>{escape(report.recommendation.confidence.value)}</code></p>
    <ul>{''.join(f'<li>{escape(item)}</li>' for item in report.recommendation.rationale)}</ul>
  </div>
  <div class="card">
    <h2>Headline findings</h2>
    <ul>{headline_findings}</ul>
  </div>
  {f'<div class="card"><h2>Recommendation warnings</h2><ul>{recommendation_warnings}</ul></div>' if recommendation_warnings else ''}
  {f'<div class="card"><h2>AMD WSL2 Vulkan remediation</h2><ul>{remediation}</ul></div>' if remediation else ''}
  <div class="card">
    <h2>Runtime assessments</h2>
    <ul>{assessments}</ul>
  </div>
  <div class="card">
    <h2>Benchmarks</h2>
    <ul>{benchmarks}</ul>
  </div>
  <p><a href="/report.json">JSON report</a></p>
</body>
</html>
"""
