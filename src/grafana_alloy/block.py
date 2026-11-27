"""Blocks: the building unit of an Alloy file (components and config blocks)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .expr import Ref, is_identifier


class Block:
    """An Alloy block: ``name "label" { attributes...  nested blocks... }``.

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
        if not all(is_identifier(part) for part in name.split(".")):
            raise ValueError(f"invalid Alloy block name: {name!r}")
        for key in attrs:
            if not is_identifier(key):
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
