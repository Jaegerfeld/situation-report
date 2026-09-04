# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Hält die drei „Schaufenster“-Modultabellen mit dem gepflegten Modul-Index
#   in Deckung: README (GitHub), Doku-Startseite EN und DE.
#
#   Befund Robert, 04.09.2026: „das readme auf github … scheint veraltet zu
#   sein, das modul getdata steht noch auf planned zum beispiel.“ Die Prüfung
#   ergab drei Tabellen mit drei verschiedenen Wahrheiten — das README ohne
#   get_data/sources/llm, die Startseiten sogar nur mit sechs Modulen und
#   get_data + simulate auf „planned“, obwohl beide ausgeliefert sind.
#   Alle drei wurden von Hand gepflegt und sind unabhängig voneinander
#   gedriftet; der Modul-Index blieb als einziger aktuell und ist deshalb
#   hier die Referenz.
#
#   Verglichen werden Modulnamen und Status — NICHT die Beschreibungstexte:
#   ein Schaufenster darf knapper oder werbender formulieren. Gleiches Muster
#   wie der Packaging-Test für die release.yml-Listen.
# =============================================================================

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

#: Modul-Index (Referenz): | [name](name.md) | Beschreibung | Status |
_INDEX_ROW = re.compile(r"^\|\s*\[(\w+)\]\(\w+\.md\)\s*\|[^|]*\|\s*(.+?)\s*\|$")
#: Schaufenster: | [`name`](…irgendein Link…) | Beschreibung | Status |
_SHOWCASE_ROW = re.compile(r"^\|\s*\[`(\w+)`\]\(\S+?\)\s*\|[^|]*\|\s*(.+?)\s*\|$")

#: (Schaufenster, Referenz-Index) — je Sprachfassung ein Paar.
SHOWCASES = [
    ("README.md", "docs/modules/index.md"),
    ("docs/index.md", "docs/modules/index.md"),
    ("docs/index.de.md", "docs/modules/index.de.md"),
]


def _rows(path: Path, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    """(Modulname, Status) je Tabellenzeile, in Dateireihenfolge."""
    return [(m.group(1), m.group(2))
            for line in path.read_text(encoding="utf-8").splitlines()
            if (m := pattern.match(line.strip()))]


@pytest.fixture(params=SHOWCASES, ids=[s for s, _ in SHOWCASES])
def pair(request) -> tuple[str, list[tuple[str, str]], list[tuple[str, str]]]:
    showcase, index = request.param
    return (showcase,
            _rows(ROOT / showcase, _SHOWCASE_ROW),
            _rows(ROOT / index, _INDEX_ROW))


class TestModuleTablesStayInSync:
    def test_both_tables_were_found(self, pair) -> None:
        """Greift ein Zeilen-Ausdruck ins Leere, prüft der Test nichts mehr."""
        name, showcase, index = pair
        assert len(index) >= 8, "Modul-Index nicht erkannt — Format geändert?"
        assert len(showcase) >= 8, f"{name}: Tabelle nicht erkannt (Format?)"

    def test_no_module_is_missing(self, pair) -> None:
        name, showcase, index = pair
        missing = {m for m, _ in index} - {m for m, _ in showcase}
        assert not missing, (
            f"{name}: es fehlen Module {sorted(missing)} — jedes "
            f"ausgelieferte Modul gehört ins Schaufenster.")

    def test_no_module_is_invented(self, pair) -> None:
        name, showcase, index = pair
        extra = {m for m, _ in showcase} - {m for m, _ in index}
        assert not extra, f"{name}: nennt unbekannte Module {sorted(extra)}"

    def test_status_matches_the_module_index(self, pair) -> None:
        """Der eigentliche Feldbefund: get_data stand auf „planned“,
        während das Modul längst ausgeliefert war."""
        name, showcase, index = pair
        index_status = dict(index)
        drifted = {m: (s, index_status[m])
                   for m, s in showcase if index_status.get(m) != s}
        assert not drifted, (
            f"{name}: Status weicht vom Modul-Index ab (dort, Index): "
            + ", ".join(f"{m}: {a!r} vs {b!r}" for m, (a, b) in drifted.items()))

    def test_every_module_is_linked(self, pair) -> None:
        """get_data war im README als einziges unverlinkt — genau das Modul
        mit dem falschen Status. Ein fehlender Link ist ein Drift-Warnzeichen."""
        name, showcase, index = pair
        text = (ROOT / name).read_text(encoding="utf-8")
        for module, _status in index:
            assert f"{module}.md" in text or f"modules/{module}/" in text, (
                f"{name}: {module} ist nicht verlinkt")
