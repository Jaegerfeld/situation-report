# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.04.2026
# Geändert:       15.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für export.py. pio.write_image wird gemockt, da kaleido einen
#   externen Browser-Prozess benötigt. Geprüft wird die Steuerlogik: korrekte
#   Dateinamen, Verzeichniserstellung, Fehlerbehandlung bei leerer Liste sowie
#   das Fallback-Verhalten für mehrere Figures ohne pypdf.
# =============================================================================

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import plotly.graph_objects as go
import pytest

from build_reports.export import export_pdf, export_png


@pytest.fixture
def simple_figure() -> go.Figure:
    return go.Figure(go.Scatter(x=[1, 2, 3], y=[1, 4, 9]))


@pytest.fixture
def two_figures(simple_figure) -> list[go.Figure]:
    return [simple_figure, go.Figure(go.Bar(x=["a"], y=[1]))]


class TestExportPdf:
    def test_raises_on_empty_list(self, tmp_path):
        with pytest.raises(ValueError, match="No figures"):
            export_pdf([], tmp_path / "out.pdf")

    def test_single_figure_calls_write_image(self, tmp_path, simple_figure):
        out = tmp_path / "report.pdf"
        with patch("build_reports.export.pio.write_image") as mock_write:
            export_pdf([simple_figure], out)
        mock_write.assert_called_once_with(
            simple_figure, str(out), format="pdf", width=1400, height=700
        )

    def test_creates_parent_dirs(self, tmp_path, simple_figure):
        out = tmp_path / "subdir" / "nested" / "report.pdf"
        with patch("build_reports.export.pio.write_image"):
            export_pdf([simple_figure], out)
        assert out.parent.exists()

    def test_multiple_figures_fallback_without_pypdf(self, tmp_path, two_figures):
        """Without pypdf, separate numbered PDFs are created."""
        out = tmp_path / "multi.pdf"
        with patch("build_reports.export.pio.write_image") as mock_write, \
             patch.dict("sys.modules", {"pypdf": None}):
            export_pdf(two_figures, out)
        assert mock_write.call_count == 2
        called_paths = [Path(c.args[1]) for c in mock_write.call_args_list]
        assert any("page1" in p.name for p in called_paths)
        assert any("page2" in p.name for p in called_paths)

    def test_custom_dimensions(self, tmp_path, simple_figure):
        out = tmp_path / "report.pdf"
        with patch("build_reports.export.pio.write_image") as mock_write:
            export_pdf([simple_figure], out, width=800, height=600)
        mock_write.assert_called_once_with(
            simple_figure, str(out), format="pdf", width=800, height=600
        )


class TestExportPng:
    def test_calls_write_image_with_png_format(self, tmp_path, simple_figure):
        out = tmp_path / "chart.png"
        with patch("build_reports.export.pio.write_image") as mock_write:
            export_png(simple_figure, out)
        mock_write.assert_called_once_with(
            simple_figure, str(out), format="png", width=1400, height=700
        )

    def test_creates_parent_dirs(self, tmp_path, simple_figure):
        out = tmp_path / "imgs" / "chart.png"
        with patch("build_reports.export.pio.write_image"):
            export_png(simple_figure, out)
        assert out.parent.exists()
