__all__ = [
    "ALLOY_BINARY",
    "format_path",
    "format_source",
    "is_available",
    "run_verbatim",
    "validate_path",
    "validate_source",
]

from pathlib import Path
from subprocess import CompletedProcess

from .utils import (
    ALLOY_BINARY,
    Status,
    alloy_run_path,
    alloy_run_text,
    is_available,
    run_verbatim,
)


def format_source(
    text: str, verbose: bool = True
) -> tuple[str, Status, CompletedProcess[str]]:
    output, status, result = alloy_run_text(("fmt", "--write"), text, verbose=verbose)

    return output or text, status, result


def format_path(
    path: Path, verbose: bool = True
) -> tuple[Status, CompletedProcess[str]]:
    return alloy_run_path(("fmt", "--write", path))


def validate_source(
    text: str, verbose: bool = True
) -> tuple[str, Status, CompletedProcess[str]]:

    return alloy_run_text(("validate",), text, verbose=verbose)


def validate_path(
    path: Path, verbose: bool = True
) -> tuple[Status, CompletedProcess[str]]:
    return alloy_run_path(("validate", path))
