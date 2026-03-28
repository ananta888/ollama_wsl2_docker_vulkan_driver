"""Concrete command execution infrastructure."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence

from ollama_env_audit.domain.models import CommandResult, ProcessLaunchResult


class SubprocessExecutor:
    """Safe subprocess-based command executor."""

    def execute(
        self,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        started = time.perf_counter()
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            completed = subprocess.run(
                list(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
                env=merged_env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            return CommandResult(
                command=list(command),
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                duration_seconds=duration,
                timed_out=True,
                error_type="timeout",
            )
        except FileNotFoundError as exc:
            duration = time.perf_counter() - started
            return CommandResult(
                command=list(command),
                exit_code=127,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
                error_type="not-found",
            )
        except OSError as exc:
            duration = time.perf_counter() - started
            return CommandResult(
                command=list(command),
                exit_code=126,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
                error_type=exc.__class__.__name__,
            )

        duration = time.perf_counter() - started
        return CommandResult(
            command=list(command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=duration,
        )

    def spawn(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        stdout_path: Path | None = None,
    ) -> ProcessLaunchResult:
        started = time.perf_counter()
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        stdout_handle = None
        try:
            if stdout_path is not None:
                stdout_path.parent.mkdir(parents=True, exist_ok=True)
                stdout_handle = stdout_path.open("a", encoding="utf-8")
            process = subprocess.Popen(
                list(command),
                cwd=str(cwd) if cwd else None,
                env=merged_env,
                stdout=stdout_handle or subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            return ProcessLaunchResult(
                command=list(command),
                duration_seconds=time.perf_counter() - started,
                error_type="not-found",
            )
        except OSError as exc:
            return ProcessLaunchResult(
                command=list(command),
                duration_seconds=time.perf_counter() - started,
                error_type=exc.__class__.__name__,
            )
        finally:
            if stdout_handle is not None:
                stdout_handle.close()

        return ProcessLaunchResult(
            command=list(command),
            pid=process.pid,
            duration_seconds=time.perf_counter() - started,
        )
