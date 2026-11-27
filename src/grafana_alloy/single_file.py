"""Build Grafana Alloy configuration files from Python."""

from __future__ import annotations

import math
import os
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pulumi  # type: ignore[import-not-found]


class _Helpers:
    _IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _PATH_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")

    _ESCAPES = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    _INDENT = "  "
    _MAX_INLINE_ITEMS = 4

    @classmethod
    def is_identifier(cls, text: str) -> bool:
        return cls._IDENTIFIER_PATTERN.fullmatch(text) is not None

    @classmethod
    def is_path(cls, text: str) -> bool:
        return cls._PATH_PATTERN.fullmatch(text) is not None

    """Serialization of values and blocks to Alloy syntax.

    Rendering produces a list of segments: plain strings, plus ``pulumi.Output``
    objects when any value is an Output. Segments are joined eagerly when no
    Output is present, and lazily through ``Output.all`` otherwise.
    """

    @classmethod
    def is_output(cls, value: Any) -> bool:
        pulumi = sys.modules.get("pulumi")
        return pulumi is not None and isinstance(value, pulumi.Output)

    @classmethod
    def quote(cls, text: str) -> str:
        out = []
        for ch in text:
            if ch in cls._ESCAPES:
                out.append(cls._ESCAPES[ch])
            elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        return '"' + "".join(out) + '"'

    @classmethod
    def is_multiline(cls, value: Any) -> bool:
        if isinstance(value, Mapping):
            items = list(value.values())
        elif isinstance(value, (list, tuple)):
            items = list(value)
        else:
            return False
        nested = any(isinstance(v, (Mapping, list, tuple)) and len(v) > 0 for v in items)
        return len(items) > cls._MAX_INLINE_ITEMS or (len(items) > 1 and nested)

    @classmethod
    def as_key(cls, key: Any) -> str:
        if not isinstance(key, str):
            raise TypeError(f"object keys must be strings, got {type(key).__name__}")
        return key if cls.is_identifier(key) else cls.quote(key)

    @classmethod
    def render_value(cls, val: Any, level: int = 0) -> list[Any]:
        """Render ``val`` as an Alloy expression at indentation ``level``."""
        if cls.is_output(val):
            return [val.apply(lambda v: "".join(cls.render_value(v, level)))]
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
            return [cls.quote(val)]
        if isinstance(val, Ref):
            return [val.path]
        if isinstance(val, Raw):
            return [val.text]
        if isinstance(val, Call):
            out: list[Any] = [val.function + "("]
            for i, arg in enumerate(val.args):
                if i:
                    out.append(", ")
                out.extend(cls.render_value(arg, level))
            out.append(")")
            return out
        if isinstance(val, Mapping):
            entries = [
                [cls.as_key(k) + " = ", *cls.render_value(v, level + 1)] for k, v in val.items()
            ]
            return cls.wrap("{", "}", entries, cls.is_multiline(val), level)
        if isinstance(val, (list, tuple)):
            entries = [cls.render_value(v, level + 1) for v in val]
            return cls.wrap("[", "]", entries, cls.is_multiline(val), level)
        if isinstance(val, Block):
            raise TypeError("blocks cannot be used as attribute values; use blocks=[...]")
        raise TypeError(f"cannot render {type(val).__name__} as an Alloy value")

    @classmethod
    def wrap(
        cls, open_: str, close: str, entries: list[list[Any]], multiline: bool, level: int
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
        pad = cls._INDENT * (level + 1)
        out = [open_ + "\n"]
        for entry in entries:
            out.append(pad)
            out.extend(entry)
            out.append(",\n")
        out.append(cls._INDENT * level + close)
        return out

    @classmethod
    def render_block(cls, blk: Block, level: int = 0) -> list[Any]:
        """Render a block (and its children) at indentation ``level``."""
        pad = cls._INDENT * level
        head = pad + blk.name + (f" {cls.quote(blk.label)}" if blk.label is not None else "")
        if not blk.attrs and not blk.blocks:
            return [head + " {}\n"]
        out: list[Any] = [head + " {\n"]

        # `alloy fmt` aligns "=" across consecutive single-line attributes.
        attrs = list(blk.attrs.items())
        i = 0
        while i < len(attrs):
            if cls.is_multiline(attrs[i][1]):
                group = [attrs[i]]
            else:
                j = i
                while j < len(attrs) and not cls.is_multiline(attrs[j][1]):
                    j += 1
                group = attrs[i:j]
            width = max(len(k) for k, _ in group)
            for key, val in group:
                out.append(f"{pad}{cls._INDENT}{key.ljust(width)} = ")
                out.extend(cls.render_value(val, level + 1))
                out.append("\n")
            i += len(group)

        for n, child in enumerate(blk.blocks):
            if attrs or n:
                out.append("\n")
            out.extend(cls.render_block(child, level + 1))
        out.append(pad + "}\n")
        return out

    @classmethod
    def join(cls, segments: list[Any]) -> str | pulumi.Output[str]:
        if not any(cls.is_output(s) for s in segments):
            return "".join(segments)
        import pulumi

        return pulumi.Output.all(*segments).apply("".join)


@dataclass(frozen=True)
class Ref:
    """An unquoted reference such as ``prometheus.remote_write.default.receiver``."""

    path: str

    def __post_init__(self) -> None:
        if not _Helpers.is_path(self.path):
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
        if not _Helpers.is_path(function):
            raise ValueError(f"invalid Alloy function name: {function!r}")
        object.__setattr__(self, "function", function)
        object.__setattr__(self, "args", args)


@dataclass(frozen=True, init=False)
class Builtins:
    @staticmethod
    def sys_env(name: Any) -> Call:
        """``sys.env("NAME")``: read an environment variable at Alloy runtime."""
        return Call("sys.env", name)

    @staticmethod
    def concat(*arrays: Any) -> Call:
        """``array.concat(...)``."""
        return Call("array.concat", *arrays)


# BLOCKS


class Block:
    """An Alloy block: The building unit of an Alloy file (components and config blocks).

    Syntax: ``name "label" { attributes...  nested blocks... }``

    Attributes are passed as keyword arguments and nested blocks via ``blocks=``
    or :meth:`add`. Attribute names are emitted verbatim (Alloy uses snake_case).
    """

    def __init__(
        self,
        name: str,
        label: str | None = None,
        /,
        *,
        blocks: Iterable[Block] = (),
        **attrs: Any,
    ) -> None:
        if not all(_Helpers.is_identifier(part) for part in name.split(".")):
            raise ValueError(f"invalid Alloy block name: {name!r}")
        for key in attrs:
            if not _Helpers.is_identifier(key):
                raise ValueError(f"invalid Alloy attribute name: {key!r}")
        self.name = name
        self.label = label
        self.attrs: dict[str, Any] = attrs
        self.blocks: list[Block] = list(blocks)

    def add(self, *blocks: Block) -> Block:
        """Append nested blocks and return ``self`` for chaining."""
        self.blocks.extend(blocks)
        return self

    @property
    def id(self) -> str:
        """Dotted identifier used to reference this block, e.g. ``loki.write.default``."""
        if self.label is None:
            return self.name
        return f"{self.name}.{self.label}"

    def ref(self, *export: str) -> Ref:
        """Reference this block or one of its exports, e.g. ``block.ref("receiver")``."""
        if self.label is None:
            raise ValueError(f"block {self.name!r} has no label and cannot be referenced")
        return Ref(".".join((self.id, *export)))

    def __repr__(self) -> str:
        return f"Block({self.id!r})"


class _Comment:
    def __init__(self, text: str) -> None:
        self.text = text


class AlloyConfig:
    """An ordered collection of top-level blocks that renders to a single Alloy file."""

    def __init__(self, blocks: Iterable[Block] = ()) -> None:
        self._items: list[Block | _Comment] = []
        self._ids: set[tuple[str, str]] = set()
        for block in blocks:
            self.add(block)

    @property
    def blocks(self) -> list[Block]:
        return [i for i in self._items if isinstance(i, Block)]

    def add(self, blk: Block) -> Block:
        """Append a top-level block and return it (handy for ``blk.ref(...)``)."""
        # Labelled components must be unique; unlabelled config blocks
        # (e.g. ``logging``) may only appear once.
        key = (blk.name, blk.label or "")
        if key in self._ids:
            raise ValueError(f"duplicate Alloy block: {blk.id}")
        self._ids.add(key)
        self._items.append(blk)
        return blk

    def comment(self, text: str) -> None:
        """Append a ``//`` comment line (multi-line text becomes several lines)."""
        self._items.append(_Comment(text))

    def render(self) -> str | pulumi.Output[str]:
        """Serialize to Alloy syntax.

        Returns ``str``, or ``pulumi.Output[str]`` if any value is a Pulumi Output.
        """
        segments: list[Any] = []
        previous: Block | _Comment | None = None
        for item in self._items:
            if isinstance(item, _Comment):
                if previous is not None and not isinstance(previous, _Comment):
                    segments.append("\n")
                segments.extend(f"// {line}".rstrip() + "\n" for line in item.text.splitlines())
            else:
                if isinstance(previous, Block):
                    segments.append("\n")
                segments.extend(_Helpers.render_block(item))
            previous = item
        return _Helpers.join(segments)

    def write(self, path: str | os.PathLike[str]) -> None:
        """Write the rendered config to ``path``. Fails if it contains Pulumi Outputs."""
        text = self.render()
        if not isinstance(text, str):
            raise TypeError("config contains Pulumi Outputs; use render() with Output.apply")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def __str__(self) -> str:
        text = self.render()
        if not isinstance(text, str):
            raise TypeError("config contains Pulumi Outputs; use render() instead of str()")
        return text


__all__ = ("AlloyConfig", "Block", "Call", "Raw", "Ref", "Builtins")
