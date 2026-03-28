"""Pydantic domain models shared across layers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import ConfidenceLevel, ProbeStatus, RuntimeMode, Severity


class CommandResult(BaseModel):
    command: list[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False
    error_type: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error_type is None


class Observation(BaseModel):
    severity: Severity
    message: str
    evidence: str | None = None


class GPUInfo(BaseModel):
    name: str
    vendor: str | None = None
    driver_version: str | None = None
    adapter_type: str | None = None


class WindowsInfo(BaseModel):
    status: ProbeStatus = ProbeStatus.UNAVAILABLE
    version: str | None = None
    build: str | None = None
    cpu: str | None = None
    ram_gb: float | None = None
    gpus: list[GPUInfo] = Field(default_factory=list)
    wsl_installed: bool | None = None
    docker_installed: bool | None = None
    observations: list[Observation] = Field(default_factory=list)


class WSLInfo(BaseModel):
    status: ProbeStatus = ProbeStatus.UNAVAILABLE
    distribution: str | None = None
    kernel: str | None = None
    is_wsl: bool = False
    devices: dict[str, bool] = Field(default_factory=dict)
    tools: dict[str, bool] = Field(default_factory=dict)
    gpu_support_likely: bool | None = None
    observations: list[Observation] = Field(default_factory=list)


class DockerInfo(BaseModel):
    status: ProbeStatus = ProbeStatus.UNAVAILABLE
    version: str | None = None
    engine_reachable: bool | None = None
    can_run_containers: bool | None = None
    gpu_support_likely: bool | None = None
    observations: list[Observation] = Field(default_factory=list)


class OllamaProcessInfo(BaseModel):
    name: str
    processor: str | None = None
    size: str | None = None
    until: str | None = None


class OllamaInfo(BaseModel):
    status: ProbeStatus = ProbeStatus.UNAVAILABLE
    binary_available: bool = False
    version: str | None = None
    api_reachable: bool | None = None
    running_models: list[OllamaProcessInfo] = Field(default_factory=list)
    accelerator_indicators: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)


class RuntimeAssessment(BaseModel):
    mode: RuntimeMode
    available: bool
    supports_gpu: bool | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    recommended_mode: RuntimeMode | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    rationale: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BenchmarkResult(BaseModel):
    mode: RuntimeMode
    status: ProbeStatus
    note: str
    metrics: dict[str, float | int | str | None] = Field(default_factory=dict)


class AuditReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_version: str
    windows: WindowsInfo
    wsl: WSLInfo
    docker: DockerInfo
    ollama: OllamaInfo
    runtime_assessments: list[RuntimeAssessment]
    recommendation: Recommendation
    benchmarks: list[BenchmarkResult] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(mode="json")
        return json.loads(self.json())
