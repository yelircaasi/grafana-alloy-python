"""Non-literal Alloy expressions: references, function calls and raw text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")


def is_identifier(text: str) -> bool:
    return _IDENT.fullmatch(text) is not None


@dataclass(frozen=True)
class Ref:
    """An unquoted reference such as ``prometheus.remote_write.default.receiver``."""

    path: str

    def __post_init__(self) -> None:
        if not _PATH.fullmatch(self.path):
            raise ValueError(f"invalid Alloy reference: {self.path!r}")

    def __getattr__(self, name: str) -> Ref:
        if name.startswith("_"):
            raise AttributeError(name)
        return Ref(f"{self.path}.{name}")

    def __getitem__(self, index: int | str) -> Raw:
        key = index if isinstance(index, int) else f'"{index}"'
        return Raw(f"{self.path}[{key}]")


@dataclass(frozen=True)
class Raw:
    """Verbatim Alloy text, emitted without quoting or validation."""

    text: str


@dataclass(frozen=True, init=False)
class Call:
    """A function call such as ``sys.env("HOME")``; arguments are rendered as values."""

    function: str
    args: tuple[Any, ...]

    def __init__(self, function: str, *args: Any) -> None:
        if not _PATH.fullmatch(function):
            raise ValueError(f"invalid Alloy function name: {function!r}")
        object.__setattr__(self, "function", function)
        object.__setattr__(self, "args", args)


def sys_env(name: Any) -> Call:
    """``sys.env("NAME")``: read an environment variable at Alloy runtime."""
    return Call("sys.env", name)


def concat(*arrays: Any) -> Call:
    """``array.concat(...)``."""
    return Call("array.concat", *arrays)
