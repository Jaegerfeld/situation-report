# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Exportiert eine oder mehrere plotly-Figures als PDF-Datei. Jede Figure
#   wird auf einer eigenen Seite ausgegeben. Der Export nutzt kaleido für
#   die Konvertierung zu PNG-Seiten, die anschließend zu einem mehrseitigen
#   PDF zusammengefügt werden. Alternativ kann jede Figure einzeln als PNG
#   exportiert werden.
# =============================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio


def export_pdf(figures: list[Any], output_path: Path, width: int = 1400, height: int = 700) -> None:
    """
    Export a list of plotly Figures to a single multi-page PDF file.

    Each figure is rendered as one page. Uses kaleido for rasterization.
    Pages are written sequentially; the PDF is created even if only one
    figure is provided.

    Args:
        figures:     List of plotly Figure objects to export.
        output_path: Destination path for the PDF file (e.g. 'report.pdf').
        width:       Page width in pixels (default 1400).
        height:      Page height in pixels (default 700).

    Raises:
        ValueError:  If figures list is empty.
        ImportError: If kaleido is not installed.
    """
    if not figures:
        raise ValueError("No figures provided for PDF export.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # kaleido supports direct PDF export for single figures;
    # for multiple pages we write individual PDFs then merge via pypdf if available,
    # otherwise fall back to one PDF per figure.
    if len(figures) == 1:
        pio.write_image(figures[0], str(output_path), format="pdf",
                        width=width, height=height)
        return

    # Try to merge multiple figures into one PDF using pypdf
    try:
        from pypdf import PdfWriter  # optional dependency
        _export_merged_pdf(figures, output_path, width, height)
    except ImportError:
        # Fallback: export one PDF per figure with numeric suffix
        stem = output_path.stem
        for i, fig in enumerate(figures, start=1):
            page_path = output_path.with_name(f"{stem}_page{i}.pdf")
            pio.write_image(fig, str(page_path), format="pdf",
                            width=width, height=height)


def _export_merged_pdf(
    figures: list[Any], output_path: Path, width: int, height: int
) -> None:
    """
    Merge multiple figures into one PDF using pypdf.

    Each figure is written to a temporary single-page PDF, then all pages
    are combined into the final output file.

    Args:
        figures:     List of plotly Figure objects.
        output_path: Final merged PDF path.
        width:       Page width in pixels.
        height:      Page height in pixels.
    """
    import tempfile
    from pypdf import PdfWriter

    writer = PdfWriter()
    tmp_paths: list[Path] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, fig in enumerate(figures):
            tmp_path = Path(tmpdir) / f"page_{i}.pdf"
            pio.write_image(fig, str(tmp_path), format="pdf",
                            width=width, height=height)
            tmp_paths.append(tmp_path)
            writer.append(str(tmp_path))

        with open(output_path, "wb") as f:
            writer.write(f)


def export_png(figure: Any, output_path: Path, width: int = 1400, height: int = 700) -> None:
    """
    Export a single plotly Figure as a PNG image.

    Args:
        figure:      A plotly Figure object.
        output_path: Destination path for the PNG file.
        width:       Image width in pixels (default 1400).
        height:      Image height in pixels (default 700).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pio.write_image(figure, str(output_path), format="png", width=width, height=height)
