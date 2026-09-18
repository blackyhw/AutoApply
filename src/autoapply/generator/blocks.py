from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from autoapply.errors import UnknownCvBlockError


class CvBlock(BaseModel):
    id: str
    section: str
    content: str
    tags: list[str] = Field(default_factory=list)
    always_include: bool = False


class BlockCatalog:
    def __init__(self, blocks: list[CvBlock]):
        self._blocks = {block.id: block for block in blocks}
        if len(self._blocks) != len(blocks):
            raise UnknownCvBlockError("Duplicate CV block ids")

    @classmethod
    def from_yaml(cls, path: Path) -> "BlockCatalog":
        payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        blocks = [CvBlock.model_validate(item) for item in payload.get("blocks", [])]
        return cls(blocks)

    def get(self, block_id: str) -> CvBlock:
        try:
            return self._blocks[block_id]
        except KeyError as exc:
            raise UnknownCvBlockError(f"Unknown CV block: {block_id}") from exc

    def always_include_ids(self) -> list[str]:
        return [block.id for block in self._blocks.values() if block.always_include]

    def filter_allowed(self, requested: list[str]) -> list[str]:
        allowed = []
        seen: set[str] = set()
        for block_id in [*self.always_include_ids(), *requested]:
            if block_id in seen:
                continue
            if block_id not in self._blocks:
                continue
            seen.add(block_id)
            allowed.append(block_id)
        return allowed

    def as_prompt_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": block.id,
                "section": block.section,
                "tags": block.tags,
                "always_include": block.always_include,
                "preview": block.content.strip().splitlines()[0][:180],
            }
            for block in self._blocks.values()
        ]

    def blocks(self):
        return list(self._blocks.values())

    @property
    def ids(self) -> set[str]:
        return set(self._blocks)
