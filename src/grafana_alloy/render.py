"""Serialization of values and blocks to Alloy syntax.

Rendering produces a list of segments: plain strings, plus ``pulumi.Output``
objects when any value is an Output. Segments are joined eagerly when no
Output is present, and lazily through ``Output.all`` otherwise.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from typing import Any

from .block import Block
from .expr import Call, Raw, Ref, is_identifier

INDENT = "  "
_MAX_INLINE_ITEMS = 4

_ESCAPES = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def is_output(value: Any) -> bool:
    pulumi = sys.modules.get("pulumi")
    return pulumi is not None and isinstance(value, pulumi.Output)


def quote(text: str) -> str:
    out = []
    for ch in text:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _is_multiline(value: Any) -> bool:
    if isinstance(value, Mapping):
        items = list(value.values())
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return False
    nested = any(isinstance(v, (Mapping, list, tuple)) and len(v) > 0 for v in items)
    return len(items) > _MAX_INLINE_ITEMS or (len(items) > 1 and nested)


def _key(key: Any) -> str:
    if not isinstance(key, str):
        raise TypeError(f"object keys must be strings, got {type(key).__name__}")
    return key if is_identifier(key) else quote(key)


def value(val: Any, level: int = 0) -> list[Any]:
    """Render ``val`` as an Alloy expression at indentation ``level``."""
    if is_output(val):
        return [val.apply(lambda v: "".join(value(v, level)))]
    if val is None:
        return ["null"]
    if isinstance(val, bool):
        return ["true" if val else "false"]
    if isinstance(val, int):
        return [str(val)]
    if isinstance(val, float):
        if not math.isfinite(val):
            raise ValueError(f"Alloy cannot represent {val!r}")
        return [repr(val)]
    if isinstance(val, str):
        return [quote(val)]
    if isinstance(val, Ref):
        return [val.path]
    if isinstance(val, Raw):
        return [val.text]
    if isinstance(val, Call):
        out: list[Any] = [val.function + "("]
        for i, arg in enumerate(val.args):
            if i:
                out.append(", ")
            out.extend(value(arg, level))
        out.append(")")
        return out
    if isinstance(val, Mapping):
        entries = [[_key(k) + " = ", *value(v, level + 1)] for k, v in val.items()]
        return _wrap("{", "}", entries, _is_multiline(val), level)
    if isinstance(val, (list, tuple)):
        entries = [value(v, level + 1) for v in val]
        return _wrap("[", "]", entries, _is_multiline(val), level)
    if isinstance(val, Block):
        raise TypeError("blocks cannot be used as attribute values; use blocks=[...]")
    raise TypeError(f"cannot render {type(val).__name__} as an Alloy value")


def _wrap(
    open_: str, close: str, entries: list[list[Any]], multiline: bool, level: int
) -> list[Any]:
    if not entries:
        return [open_ + close]
    if not multiline:
        out: list[Any] = [open_]
        for i, entry in enumerate(entries):
            if i:
                out.append(", ")
            out.extend(entry)
        out.append(close)
        return out
    pad = INDENT * (level + 1)
    out = [open_ + "\n"]
    for entry in entries:
        out.append(pad)
        out.extend(entry)
        out.append(",\n")
    out.append(INDENT * level + close)
    return out


def block(blk: Block, level: int = 0) -> list[Any]:
    """Render a block (and its children) at indentation ``level``."""
    pad = INDENT * level
    head = pad + blk.name + (f" {quote(blk.label)}" if blk.label is not None else "")
    if not blk.attrs and not blk.blocks:
        return [head + " {}\n"]
    out: list[Any] = [head + " {\n"]

    # `alloy fmt` aligns "=" across consecutive single-line attributes.
    attrs = list(blk.attrs.items())
    i = 0
    while i < len(attrs):
        if _is_multiline(attrs[i][1]):
            group = [attrs[i]]
        else:
            j = i
            while j < len(attrs) and not _is_multiline(attrs[j][1]):
                j += 1
            group = attrs[i:j]
        width = max(len(k) for k, _ in group)
        for key, val in group:
            out.append(f"{pad}{INDENT}{key.ljust(width)} = ")
            out.extend(value(val, level + 1))
            out.append("\n")
        i += len(group)

    for n, child in enumerate(blk.blocks):
        if attrs or n:
            out.append("\n")
        out.extend(block(child, level + 1))
    out.append(pad + "}\n")
    return out
