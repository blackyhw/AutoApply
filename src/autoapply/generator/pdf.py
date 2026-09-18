from __future__ import annotations

import logging
from pathlib import Path

logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset").setLevel(logging.WARNING)

from autoapply.logging import get_logger

log = get_logger("generator.pdf")

_FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
)


def render_cv_pdf(text: str, path: Path) -> Path:
    """Write a simple text CV to PDF. Blocks are already trusted content."""
    from fpdf import FPDF

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font_path = next((candidate for candidate in _FONT_CANDIDATES if candidate.exists()), None)
    if font_path:
        pdf.add_font("CvSans", "", str(font_path))
        pdf.set_font("CvSans", size=11)
        body = text
    else:
        pdf.set_font("Helvetica", size=11)
        body = text.encode("latin-1", errors="replace").decode("latin-1")
        log.warning("pdf_core_font_fallback", path=str(path))
    pdf.multi_cell(0, 6, body)
    pdf.output(str(path))
    return path
