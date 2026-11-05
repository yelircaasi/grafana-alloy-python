from __future__ import annotations

import enum
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any


class Status(enum.Enum):
    SUCCESS = 0
    FAILURE = 1

    def __bool__(self) -> bool:
        return self == Status.SUCCESS

    @classmethod
    def from_completed(cls, result: CompletedProcess) -> Status:
        return cls.SUCCESS if result.returncode == 0 else cls.FAILURE


class AlloyError(Exception):
    """Custom exception raised for Alloy wrapper errors."""


def _get_binary_path() -> str:
    """Dynamically resolves and verifies the path to the platform-specific binary."""
    binary_path = os.environ.get("ALLOY_PATH") or shutil.which("alloy")

    if not binary_path:
        return ""

    if not (binary_path := Path(binary_path)).exists():
        return ""

    return str(binary_path)


ALLOY_BINARY = _get_binary_path()


def is_available() -> bool:
    return bool(ALLOY_BINARY)


def _make_command(command: Iterable[Any]) -> list[str]:
    return [ALLOY_BINARY, *map(str, command)]


def print_stdout_and_stderr(result: CompletedProcess[str]) -> None:
    print("=" * 37 + " ALLOY " + "=" * 36)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print("=" * 80)


def alloy_run_path(
    command: Iterable[Any], verbose: bool = True, **kwargs
) -> tuple[Status, CompletedProcess[str]]:
    result = subprocess.run(_make_command(command), capture_output=True, text=True)  # noqa: PLW1510

    if verbose:
        print_stdout_and_stderr(result)

    status = Status.from_completed(result)
    return status, result


def alloy_run_text(
    command: Iterable[Any], text: str, verbose: bool = True, **kwargs
) -> tuple[str, Status, CompletedProcess[str]]:
    tmp_path = Path(tempfile.mkstemp(suffix=".alloy")[1])
    tmp_path.write_text(text)
    status, result = alloy_run_path((*command, tmp_path), verbose=verbose, **kwargs)

    return (tmp_path.read_text() if status else ""), status, result


def run_verbatim(command: Iterable[Any], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(_make_command(command), **kwargs)  # noqa: PLW1510
