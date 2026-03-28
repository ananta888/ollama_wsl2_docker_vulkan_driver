"""Runtime mode catalog."""

from __future__ import annotations

from pydantic import BaseModel

from ollama_env_audit.domain.enums import RuntimeMode


class RuntimeDescriptor(BaseModel):
    mode: RuntimeMode
    label: str
    description: str


RUNTIME_CATALOG: tuple[RuntimeDescriptor, ...] = (
    RuntimeDescriptor(
        mode=RuntimeMode.WINDOWS_NATIVE,
        label="Windows native",
        description="Ollama running directly on the Windows host.",
    ),
    RuntimeDescriptor(
        mode=RuntimeMode.WSL_NATIVE,
        label="WSL native",
        description="Ollama installed directly inside WSL2.",
    ),
    RuntimeDescriptor(
        mode=RuntimeMode.DOCKER_WSL,
        label="Docker in WSL",
        description="Ollama running inside Docker from a WSL2 environment.",
    ),
)
