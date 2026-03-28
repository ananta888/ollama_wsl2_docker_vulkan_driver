"""Configuration models and loading helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from ollama_env_audit.domain.exceptions import ConfigError


class CommandSettings(BaseModel):
    timeout_seconds: float = Field(default=10.0, gt=0)
    long_timeout_seconds: float = Field(default=30.0, gt=0)


class OllamaSettings(BaseModel):
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = Field(default=3.0, gt=0)


class DockerSettings(BaseModel):
    smoke_test_image: str = "hello-world"
    allow_image_pull: bool = False
    run_smoke_test: bool = True
    runtime_image: str = "ollama/ollama:latest"
    container_name: str = "ollama-env-audit"
    published_port: int = Field(default=11434, ge=1, le=65535)


class BenchmarkSettings(BaseModel):
    default_model: str = "llama3.2:3b"
    prompt: str = "Summarize the current machine in one sentence."
    request_timeout_seconds: float = Field(default=90.0, gt=0)
    num_predict: int = Field(default=64, ge=1)


class RuntimeSettings(BaseModel):
    windows_base_url: str = "http://127.0.0.1:11434"
    wsl_base_url: str = "http://127.0.0.1:11434"
    docker_base_url: str = "http://127.0.0.1:11434"


class WebSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)


class AppConfig(BaseModel):
    commands: CommandSettings = Field(default_factory=CommandSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    docker: DockerSettings = Field(default_factory=DockerSettings)
    benchmark: BenchmarkSettings = Field(default_factory=BenchmarkSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    web: WebSettings = Field(default_factory=WebSettings)

    @classmethod
    def from_path(cls, path: Path) -> "AppConfig":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"Configuration file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Configuration file is not valid JSON: {path}") from exc

        try:
            if hasattr(cls, "model_validate"):
                return cls.model_validate(raw)
            return cls.parse_obj(raw)
        except ValidationError as exc:
            raise ConfigError(f"Configuration validation failed: {exc}") from exc
