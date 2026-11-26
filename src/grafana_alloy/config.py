"""AlloyConfig: a single Alloy configuration file."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from . import render
from .block import Block

if TYPE_CHECKING:
    import pulumi


class _Comment:
    def __init__(self, text: str) -> None:
        self.text = text


class AlloyConfig:
    """An ordered collection of top-level blocks that renders to one Alloy file."""

    def __init__(self, blocks: Iterable[Block] = ()) -> None:
        self._items: list[Block | _Comment] = []
        self._ids: set[tuple[str, str]] = set()
        for blk in blocks:
            self.add(blk)

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
                segments.extend(render.block(item))
            previous = item
        return _join(segments)

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


def _join(segments: list[Any]) -> str | pulumi.Output[str]:
    if not any(render.is_output(s) for s in segments):
        return "".join(segments)
    import pulumi

    return pulumi.Output.all(*segments).apply("".join)
