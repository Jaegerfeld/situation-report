# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Datei-Provider (C1/C2, „Weg 1"): liest Records aus einer JSON-Datei im
#   normierten Record-Schema. Damit ist JEDES fremde System sofort
#   anbindbar — ein Team exportiert/erzeugt die Datei mit eigenen Mitteln
#   (Skript, Cron, Hand), ohne auf eine API-Freigabe zu warten. Zugleich
#   ist dies die Referenz dafür, wie wenig eine neue Quelle braucht:
#   PROVIDER-Objekt mit provider_id, kinds und fetch().
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sources.base import KINDS, Record, record_from_dict


class FileSource:
    """Reads normalised records of any kind from a JSON file."""

    provider_id = "file"
    kinds = KINDS

    def fetch(self, kind: str, config: dict[str, Any],
              log: Callable[[str], None]) -> list[Record]:
        """
        Load records from ``config["path"]``.

        The file holds either {"records": [...]} or a bare list — each entry
        a dict in the record schema of ``kind``.
        """
        path = Path(str(config.get("path", "")))
        if not str(path) or not path.is_file():
            raise RuntimeError(
                f"File source: '{path}' does not exist — expected a JSON "
                f"file with normalised {kind} records.")
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = raw.get("records") if isinstance(raw, dict) else raw
        if not isinstance(entries, list):
            raise RuntimeError(
                "File source: expected {\"records\": [...]} or a bare list.")
        records = [record_from_dict(kind, dict(e)) for e in entries]
        for record in records:
            if not record.source:
                record.source = f"file:{path.name}"
        log(f"  file: {len(records)} {kind} records from {path.name}")
        return records


PROVIDER = FileSource()
