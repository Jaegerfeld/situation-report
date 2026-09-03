# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   CSV-Provider für SLOs — zugleich die lebende Lösung des Tutorials
#   „Eine eigene Datenquelle anbinden": bewusst klein und gut kommentiert,
#   damit ein Entwickler ohne Vorerfahrung daran das Provider-Muster
#   nachvollziehen kann. Fachlich nützlich für die Excel-/CSV-Welt: Teams
#   pflegen ihre SLO-Werte in einer Tabelle, dieser Provider übersetzt sie
#   in normierte SloRecords.
# =============================================================================

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sources.base import KIND_SLO, Record, SloRecord

#: Required CSV columns (header row). Optional: sli_pct, window.
_REQUIRED_COLUMNS = ("service", "slo", "target_pct")


class CsvSloSource:
    """
    Reads SLO records from a CSV file.

    Expected header: service,slo,target_pct[,sli_pct][,window]
    Decimal commas (99,9) are accepted — the file often comes from Excel.
    """

    # 1) Under this id the provider appears in configs and `providers`.
    provider_id = "csv"
    # 2) What it can deliver — the CLI validates requests against this.
    kinds = (KIND_SLO,)

    # 3) fetch() translates the foreign format into normalised records.
    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Load SLO records from ``config["path"]``.

        Raises:
            RuntimeError: When the file is missing or a required column
                          is absent — with the expected header named.
        """
        path = Path(str(config.get("path", "")))
        if not str(path) or not path.is_file():
            raise RuntimeError(
                f"CSV source: '{path}' does not exist — expected a CSV with "
                f"header {','.join(_REQUIRED_COLUMNS)}[,sli_pct][,window].")

        fetched_at = datetime.now().isoformat(timespec="seconds")
        records: list[Record] = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=_sniff_delimiter(path))
            missing = [c for c in _REQUIRED_COLUMNS
                       if c not in (reader.fieldnames or [])]
            if missing:
                raise RuntimeError(
                    f"CSV source: column(s) {', '.join(missing)} missing — "
                    f"expected header "
                    f"{','.join(_REQUIRED_COLUMNS)}[,sli_pct][,window].")
            for row in reader:
                records.append(SloRecord(
                    service=str(row.get("service", "")).strip(),
                    slo=str(row.get("slo", "")).strip(),
                    target_pct=_num(row.get("target_pct")),
                    sli_pct=(_num(row["sli_pct"])
                             if str(row.get("sli_pct", "")).strip() else None),
                    window=str(row.get("window", "") or "30d").strip(),
                    source=f"csv:{path.name}",
                    fetched_at=fetched_at,
                ))
        log(f"  csv: {len(records)} slo records from {path.name}")
        return records


def _sniff_delimiter(path: Path) -> str:
    """Semicolon CSVs are the German-Excel default — accept both."""
    head = path.read_text(encoding="utf-8-sig").splitlines()[0]
    return ";" if head.count(";") > head.count(",") else ","


def _num(value: Any) -> float:
    """Parse a number, accepting the decimal comma (Excel exports)."""
    return float(str(value).strip().replace(",", "."))


# 4) This single object is what the auto-discovery looks for.
PROVIDER = CsvSloSource()
