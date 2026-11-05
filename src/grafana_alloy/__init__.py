__all__ = [
    "ALLOY_BINARY",
    "format_path",
    "format_source",
    "is_available",
    "run_verbatim",
    "validate_path",
    "validate_source",
]

import shutil
import subprocess
from pathlib import Path

from .utils import ALLOY_BINARY, Status, alloy_run_path, alloy_run_text, run_verbatim


def is_available() -> bool:
    if ALLOY_BINARY == "alloy":
        return bool(shutil.which("alloy"))
    return True


def format_source(
    text: str, verbose: bool = True
) -> tuple[str, Status, subprocess.CompletedProcess[str]]:

    return alloy_run_text(("fmt", "-"), text)


def format_path(
    path: Path, verbose: bool = True
) -> tuple[Status, subprocess.CompletedProcess[str]]:
    return alloy_run_path(("fmt", path))


def validate_source(
    text: str, verbose: bool = True
) -> tuple[str, Status, subprocess.CompletedProcess[str]]:
    output, status, result = alloy_run_text(["validate", "-"], text, verbose=verbose)

    if verbose:
        print("TODO")

    return (output if status else ""), status, result


def validate_path(
    path: Path, verbose: bool = True
) -> tuple[Status, subprocess.CompletedProcess[str]]:
    return alloy_run_path(("validate", path))
