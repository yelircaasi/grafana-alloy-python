from __future__ import annotations

import enum
import os
import platform
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class Status(enum.Enum):
    SUCCESS = 0
    FAILURE = 1

    def __bool__(self) -> bool:
        return self == Status.SUCCESS

    @classmethod
    def from_completed(cls, result: subprocess.CompletedProcess) -> Status:
        return cls.SUCCESS if result.returncode == 0 else cls.FAILURE


class AlloyError(Exception):
    """Custom exception raised for Alloy wrapper errors."""



def _get_binary_path() -> str:
    """Dynamically resolves and verifies the path to the platform-specific binary."""
    extension = ".exe" if sys.platform.startswith("win") else ""
    executable_name = f"alloy{extension}"

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch_dir = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch_dir = "arm64"
    else:
        raise AlloyError(f"Unsupported architecture: {machine}")

    # Example path: src/alloy_wrapper/bin/linux-amd64/alloy
    binary_path = (
        Path(__file__).parent / "bin" / f"{sys.platform}-{arch_dir}" / executable_name
    )

    if not binary_path.exists():
        raise FileNotFoundError(f"Embedded Alloy binary not found at: {binary_path}")

    # Ensure executable permissions on Unix systems
    if not sys.platform.startswith("win"):
        os.chmod(binary_path, 0o755)

    return str(binary_path)


ALLOY_BINARY = _get_binary_path()


def _make_command(command: Iterable[Any]) -> list[str]:
    return [ALLOY_BINARY, *map(str, command)]


def alloy_run_text(
    command: Iterable[Any], input_: str, verbose: bool = True, **kwargs
) -> tuple[str, Status, subprocess.CompletedProcess[str]]:
    result = subprocess.run(  # noqa: PLW1510
        _make_command(command),
        input=input_,
        text=True,
        capture_output=True,
    )

    if verbose:
        print("TODO")

    status = Status.from_completed(result)
    return result.stdout, status, result


def alloy_run_path(
    command: Iterable[Any], verbose: bool = True, **kwargs
) -> tuple[Status, subprocess.CompletedProcess[str]]:
    result = subprocess.run(_make_command(command), capture_output=True, text=True)  # noqa: PLW1510

    if verbose:
        print("TODO")

    status = Status.from_completed(result)
    return status, result


def run_verbatim(command: Iterable[Any], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(_make_command(command), **kwargs)  # noqa: PLW1510
