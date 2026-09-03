# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für den CSV-SLO-Provider (die lebende Tutorial-Lösung):
#   Komma- und Semikolon-CSV (deutsches Excel), Dezimalkomma, optionale
#   Spalten, BOM, Fehlerbilder mit benanntem erwartetem Header.
# =============================================================================

from __future__ import annotations

import pytest

from sources.base import KIND_SLO
from sources.providers.csv_slo import PROVIDER


def _fetch(path):
    return PROVIDER.fetch(KIND_SLO, {"path": str(path)}, lambda m: None)


class TestCsvSloProvider:
    def test_comma_csv_with_optional_columns(self, tmp_path) -> None:
        path = tmp_path / "slos.csv"
        path.write_text(
            "service,slo,target_pct,sli_pct,window\n"
            "Order API,availability,99.9,99.95,30d\n"
            "Search,p99 < 800 ms,99.0,,7d\n", encoding="utf-8")
        records = _fetch(path)
        assert [r.service for r in records] == ["Order API", "Search"]
        assert records[0].sli_pct == 99.95
        assert records[1].sli_pct is None          # leere Zelle = kein SLI
        assert records[1].window == "7d"
        assert records[0].source == "csv:slos.csv"

    def test_german_excel_semicolon_and_decimal_comma_and_bom(self, tmp_path) -> None:
        path = tmp_path / "slos_de.csv"
        path.write_bytes(
            "service;slo;target_pct;sli_pct\n"
            "Checkout;Verfügbarkeit;99,5;99,55\n".encode("utf-8-sig"))
        [record] = _fetch(path)
        assert record.target_pct == 99.5
        assert record.sli_pct == 99.55

    def test_missing_file_and_missing_column_name_expected_header(self, tmp_path) -> None:
        with pytest.raises(RuntimeError, match="does not exist"):
            _fetch(tmp_path / "nope.csv")
        bad = tmp_path / "bad.csv"
        bad.write_text("service,slo\nA,x\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="target_pct"):
            _fetch(bad)
