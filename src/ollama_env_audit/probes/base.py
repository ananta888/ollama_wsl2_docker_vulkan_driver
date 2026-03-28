"""Base helpers for probes."""

from __future__ import annotations

from ollama_env_audit.config import AppConfig
from ollama_env_audit.domain.protocols import CommandExecutor


class BaseProbe:
    name = "base"

    def __init__(self, executor: CommandExecutor, config: AppConfig) -> None:
        self._executor = executor
        self._config = config
