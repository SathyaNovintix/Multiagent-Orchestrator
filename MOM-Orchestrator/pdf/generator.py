"""
PDF Generator — AgentMesh AI
Uses WeasyPrint to render the MOM HTML template into a PDF byte stream.
Accepts a format definition dict to apply the correct colors/labels.
"""
from __future__ import annotations
import asyncio
import os
from pathlib import Path

from schemas.contracts import MOMDocument
from pdf.template import render_mom_html

PDF_OUTPUT_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "generated_pdfs"))
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def generate_pdf(
    mom: MOMDocument,
    title: str = "Minutes of Meeting",
    fmt: dict | None = None,
) -> Path:
    html_content = render_mom_html(mom, title=title, fmt=fmt)
    output_path = PDF_OUTPUT_DIR / f"MOM_{mom.mom_id}.pdf"

    def _render():
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(str(output_path))

    await asyncio.get_event_loop().run_in_executor(None, _render)
    return output_path


async def generate_pdf_bytes(
    mom: MOMDocument,
    title: str = "Minutes of Meeting",
    fmt: dict | None = None,
) -> bytes:
    html_content = render_mom_html(mom, title=title, fmt=fmt)

    def _render():
        from weasyprint import HTML
        return HTML(string=html_content).write_pdf()

    return await asyncio.get_event_loop().run_in_executor(None, _render)
