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

from build_reports.export import export_pdf, export_png, write_zero_day_excel
from build_reports.loader import IssueRecord


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


def _make_record(key: str, project: str = "ART") -> IssueRecord:
    from datetime import datetime
    return IssueRecord(
        project=project, key=key, issuetype="Feature", status="Done",
        created=datetime(2025, 1, 1), component="",
        first_date=datetime(2025, 1, 5), implementation_date=None,
        closed_date=datetime(2025, 1, 5),
        stage_minutes={}, resolution="Done",
    )


class TestWriteZeroDayExcel:
    def test_creates_file(self, tmp_path):
        path = tmp_path / "zero_day.xlsx"
        write_zero_day_excel([_make_record("A-1")], path)
        assert path.exists()

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "zero_day.xlsx"
        write_zero_day_excel([_make_record("A-1")], path)
        assert path.exists()

    def test_file_contains_header_and_data(self, tmp_path):
        from openpyxl import load_workbook
        path = tmp_path / "zero_day.xlsx"
        write_zero_day_excel([_make_record("A-1"), _make_record("A-2")], path)
        wb = load_workbook(path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0][0] == "Project"  # header
        keys = [r[1] for r in rows[1:]]
        assert "A-1" in keys
        assert "A-2" in keys

    def test_records_sorted_by_project_then_key(self, tmp_path):
        from openpyxl import load_workbook
        path = tmp_path / "sorted.xlsx"
        records = [
            _make_record("B-2", project="ARTB"),
            _make_record("A-1", project="ARTA"),
            _make_record("A-2", project="ARTA"),
        ]
        write_zero_day_excel(records, path)
        wb = load_workbook(path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        keys = [r[1] for r in rows[1:]]
        assert keys == ["A-1", "A-2", "B-2"]

    def test_empty_records_writes_header_only(self, tmp_path):
        from openpyxl import load_workbook
        path = tmp_path / "empty.xlsx"
        write_zero_day_excel([], path)
        wb = load_workbook(path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert len(rows) == 1  # header only
        assert rows[0][0] == "Project"


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
