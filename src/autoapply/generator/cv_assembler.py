from __future__ import annotations

from autoapply.errors import UnknownCvBlockError
from autoapply.generator.blocks import BlockCatalog


SECTION_ORDER = ("header", "summary", "experience", "skills", "education", "languages", "other")


class CvAssembler:
    """Concatenate pre-authored blocks. Never rewrites their text."""

    def __init__(self, catalog: BlockCatalog):
        self.catalog = catalog

    def assemble(self, selected_ids: list[str]) -> str:
        ids = self.catalog.filter_allowed(selected_ids)
        if not ids:
            raise UnknownCvBlockError("No CV blocks selected")
        grouped: dict[str, list[str]] = {}
        for block_id in ids:
            block = self.catalog.get(block_id)
            grouped.setdefault(block.section, []).append(block.content.strip())
        parts: list[str] = []
        for section in SECTION_ORDER:
            chunks = grouped.pop(section, [])
            if chunks:
                parts.append("\n\n".join(chunks))
        for leftover in grouped.values():
            parts.append("\n\n".join(leftover))
        return "\n\n".join(parts).strip() + "\n"
