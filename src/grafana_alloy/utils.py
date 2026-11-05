from __future__ import annotations

import enum
import importlib.resources
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


def _get_binary_path() -> str:
    """Dynamically resolves the path to the platform-specific binary package."""
    if sys.platform.startswith("linux"):
        package_name = "alloy_wrapper_linux_amd64"
        bin_name = "alloy"
    elif sys.platform == "darwin":
        package_name = "alloy_wrapper_darwin_arm64"
        bin_name = "alloy"
    elif sys.platform == "win32":
        package_name = "alloy_wrapper_windows_amd64"
        bin_name = "alloy.exe"
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")

    binary_path = importlib.resources.files(package_name).joinpath("bin", bin_name)
    path_ = Path(str(binary_path))
    if not path_.exists():
        msg = f"Path not found: {path_}"
        raise OSError(msg)
    return str(path_)


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
