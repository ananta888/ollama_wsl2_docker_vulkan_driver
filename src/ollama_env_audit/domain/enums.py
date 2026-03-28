"""Domain enums used across the application."""

from enum import Enum


class ProbeStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"


class RuntimeMode(str, Enum):
    WINDOWS_NATIVE = "windows-native"
    WSL_NATIVE = "wsl-native"
    DOCKER_WSL = "docker-wsl"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
