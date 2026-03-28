"""Custom exceptions for the toolkit."""


class AuditError(Exception):
    """Base exception for the project."""


class ConfigError(AuditError):
    """Raised when configuration loading or validation fails."""


class CommandExecutionError(AuditError):
    """Raised when command execution fails in a non-recoverable way."""


class ProbeExecutionError(AuditError):
    """Raised when a probe encounters an unexpected fatal condition."""
