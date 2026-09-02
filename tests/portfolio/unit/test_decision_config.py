# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.09.2026
# Geändert:       02.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für portfolio.decision_config (B4): Parsen und Validieren
#   eines Decision-/Assumption-Logs, kind-abhängige Status-Validierung,
#   supersedes-Referenzprüfung, Fehlerfälle und der Datei-Roundtrip.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from portfolio.decision_config import (
    ASSUMPTION_OPEN,
    DECISION_ACCEPTED,
    DecisionLog,
    LogEntry,
    decisions_to_dict,
    load_decisions,
    parse_decisions,
    save_decisions,
)


def _entry(entry_id: str = "E-1", **kwargs) -> dict:
    base = {"id": entry_id, "kind": "decision", "title": "Test entry",
            "status": "accepted"}
    base.update(kwargs)
    return base


class TestParseDecisions:
    def test_minimal_valid_log(self) -> None:
        log = parse_decisions({"entries": [_entry()]})
        entry = log.entries[0]
        assert entry.entry_id == "E-1"
        assert entry.kind == "decision"
        assert entry.status == DECISION_ACCEPTED
        assert entry.review_by is None

    def test_empty_log_is_valid(self) -> None:
        assert parse_decisions({"entries": []}) == DecisionLog()

    def test_normalisation_and_full_fields(self) -> None:
        log = parse_decisions({"entries": [
            _entry(),
            _entry(entry_id="E-2", kind="Assumption", status="OPEN",
                   owner=" Team ", logged_on="2025-04-01",
                   review_by="2025-06-01", notes=" n "),
        ]})
        entry = log.entries[1]
        assert entry.kind == "assumption"
        assert entry.status == ASSUMPTION_OPEN
        assert entry.owner == "Team"
        assert entry.logged_on == date(2025, 4, 1)
        assert entry.review_by == date(2025, 6, 1)
        assert entry.notes == "n"

    def test_rejects_non_object_and_missing_list(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            parse_decisions([])
        with pytest.raises(ValueError, match="'entries' list"):
            parse_decisions({"entries": "x"})

    def test_rejects_empty_id_and_title(self) -> None:
        with pytest.raises(ValueError, match="'id'"):
            parse_decisions({"entries": [_entry(entry_id=" ")]})
        with pytest.raises(ValueError, match="'title'"):
            parse_decisions({"entries": [_entry(title="")]})

    def test_rejects_duplicate_id_and_unknown_kind(self) -> None:
        with pytest.raises(ValueError, match="Duplicate entry id"):
            parse_decisions({"entries": [_entry(), _entry()]})
        with pytest.raises(ValueError, match="unknown kind"):
            parse_decisions({"entries": [_entry(kind="note")]})

    def test_status_must_match_kind(self) -> None:
        # "open" gehört zu Annahmen, nicht zu Entscheidungen — und umgekehrt.
        with pytest.raises(ValueError, match="not valid for a decision"):
            parse_decisions({"entries": [_entry(status="open")]})
        with pytest.raises(ValueError, match="not valid for a assumption"):
            parse_decisions({"entries": [
                _entry(kind="assumption", status="accepted")]})

    def test_rejects_bad_dates(self) -> None:
        with pytest.raises(ValueError, match="logged_on"):
            parse_decisions({"entries": [_entry(logged_on="01.04.2025")]})
        with pytest.raises(ValueError, match="review_by"):
            parse_decisions({"entries": [_entry(review_by="bald")]})

    def test_supersedes_must_reference_existing_entry(self) -> None:
        with pytest.raises(ValueError, match="unknown entry"):
            parse_decisions({"entries": [_entry(supersedes="E-9")]})
        with pytest.raises(ValueError, match="supersede itself"):
            parse_decisions({"entries": [_entry(supersedes="E-1")]})
        # Gültige Kette parst.
        log = parse_decisions({"entries": [
            _entry(entry_id="E-0", status="superseded"),
            _entry(supersedes="E-0")]})
        assert log.entries[1].supersedes == "E-0"


class TestRoundtrip:
    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        log = DecisionLog(entries=[
            LogEntry("E-0", "decision", "Old way", "superseded",
                     logged_on=date(2025, 1, 1)),
            LogEntry("E-1", "decision", "New way", "accepted",
                     owner="Team A", logged_on=date(2025, 3, 1),
                     supersedes="E-0", notes="trade-off"),
            LogEntry("A-1", "assumption", "Exports keep coming", "open",
                     review_by=date(2025, 9, 30)),
        ])
        path = tmp_path / "decisions.json"
        save_decisions(path, log)
        assert load_decisions(path) == log

    def test_to_dict_omits_empty_optionals(self) -> None:
        data = decisions_to_dict(DecisionLog(entries=[
            LogEntry("E-1", "decision", "T", "accepted")]))
        entry = data["entries"][0]
        for absent in ("owner", "logged_on", "review_by", "supersedes", "notes"):
            assert absent not in entry
        assert data["schema"] == 1
