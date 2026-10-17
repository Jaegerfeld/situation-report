# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       17.10.2026
# Geändert:       17.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des KI-Kompetenz-Logs (R4, Art. 4): Schema und Pflichtfelder,
#   Personenfelder abgelehnt, Freitext gekapselt, Status je Team mit
#   Fälligkeit (aktuell · fällig · keine Maßnahme), Monatsarithmetik,
#   Bedarfsbild aus dem Nachweis (Zweck → Thema, Lücken), Beispiel-Log läuft
#   durch den Bericht, CLI-Rückgabewerte und --example.
# =============================================================================

from __future__ import annotations

import json
from datetime import date

import pytest

from llm.cli import main as llm_main
from llm.literacy import (
    KINDS,
    TOPICS,
    _add_months,
    covered_topics,
    example_log,
    needed_topics,
    parse_log,
    report_markdown,
    run_literacy,
    team_status,
    usage_from_audit,
)

AS_OF = date(2026, 10, 17)


def _log(**over):
    data = {"schema": 1, "operator": "Stab Demo", "refresh_months": 12,
            "teams": ["Stab", "ART A", "ART B"],
            "measures": [
                {"id": "KM-1", "date": "2025-06-01", "title": "Einführung", "kind": "briefing",
                 "participants": 10, "teams": ["ART A"], "scope": ["labeling", "limits"]},
                {"id": "KM-2", "date": "2026-09-01", "title": "Befragen [S1/x]\n# Heading", "kind": "workshop",
                 "duration_h": 3, "participants": 6, "teams": ["Stab"],
                 "scope": ["labeling", "citation", "prompting"], "attendance_ref": "HR #1"},
            ]}
    data.update(over)
    return data


class TestParse:
    def test_valid_log_sorted_and_encapsulated(self) -> None:
        log = parse_log(_log())
        assert [m.measure_id for m in log.measures] == ["KM-1", "KM-2"] and log.teams == ["Stab", "ART A", "ART B"]
        assert log.measures[1].title == "Befragen (S1/x) ＃ Heading" and log.measures[1].attendance_ref == "HR #1"
        assert log.measures[0].duration_h is None and log.measures[1].duration_h == 3.0

    def test_teams_from_measures_are_added(self) -> None:
        log = parse_log(_log(teams=[]))
        assert log.teams == ["ART A", "Stab"]

    @pytest.mark.parametrize("bad, msg", [
        ({"schema": 2}, "schema"),
        ({"measures": [{"id": "X", "date": "2026-01-01", "title": "t", "kind": "lecture", "teams": ["a"]}]}, "kind"),
        ({"measures": [{"id": "X", "date": "2026-01-01", "title": "t", "kind": "briefing", "teams": ["a"], "scope": ["magic"]}]}, "scope"),
        ({"measures": [{"id": "X", "date": "01.01.2026", "title": "t", "kind": "briefing", "teams": ["a"]}]}, "ISO"),
        ({"measures": [{"id": "X", "date": "2026-01-01", "kind": "briefing", "teams": ["a"]}]}, "'title' is required"),
        ({"measures": [{"id": "X", "date": "2026-01-01", "title": "t", "kind": "briefing", "teams": ["a"], "participants": "acht"}]}, "count"),
    ])
    def test_invalid_logs(self, bad, msg) -> None:
        with pytest.raises(ValueError, match=msg):
            parse_log(_log(**bad))

    def test_person_fields_are_refused(self) -> None:
        with pytest.raises(ValueError, match="Person fields"):
            parse_log(_log(measures=[{"id": "X", "date": "2026-01-01", "title": "t", "kind": "briefing",
                                      "teams": ["a"], "names": ["Jane Doe"]}]))
        with pytest.raises(ValueError, match="Person fields"):
            parse_log(_log(attendees=["x"]))
        assert set(KINDS) == {"workshop", "training", "briefing", "self_study", "pilot"} and len(TOPICS) == 7


class TestStatus:
    def test_months_and_status(self) -> None:
        assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
        assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29) and _add_months(date(2026, 11, 15), 2) == date(2027, 1, 15)
        st = {s.team: s for s in team_status(parse_log(_log()), AS_OF)}
        assert st["Stab"].status == "current" and st["Stab"].due == date(2027, 9, 1) and st["Stab"].topics == {"labeling", "citation", "prompting"}
        assert st["ART A"].status == "due" and st["ART A"].due == date(2026, 6, 1) and st["ART A"].measures == 1
        assert st["ART B"].status == "none" and st["ART B"].last is None

    def test_future_measures_do_not_count_and_per_measure_refresh(self) -> None:
        data = _log()
        data["measures"][0]["refresh_months"] = 24
        data["measures"].append({"id": "KM-9", "date": "2027-01-01", "title": "später", "kind": "training", "teams": ["ART B"]})
        st = {s.team: s for s in team_status(parse_log(data), AS_OF)}
        assert st["ART A"].status == "current" and st["ART A"].due == date(2027, 6, 1)
        assert st["ART B"].status == "none"


class TestNeeds:
    def test_usage_and_gaps(self, tmp_path) -> None:
        audit = tmp_path / "llm_audit.jsonl"
        recs = [{"ts": "2026-10-01T10:00:00", "purpose": "d3_question", "provider": "mock", "deployment_class": "mock"},
                {"ts": "2026-10-02T10:00:00", "purpose": "d3_question", "provider": "export", "deployment_class": "export"},
                {"ts": "2026-10-03T10:00:00", "purpose": "approval"},
                {"ts": "2025-01-01T10:00:00", "purpose": "d5_red_team"},
                "not json"]
        audit.write_text("\n".join(json.dumps(r) if isinstance(r, dict) else r for r in recs), encoding="utf-8")
        usage = usage_from_audit(audit, since=date(2026, 1, 1))
        assert usage == {"d3_question": 2, "export": 1, "approval": 1}
        needed = needed_topics(usage)
        assert needed == {"labeling", "citation", "prompting", "limits", "export", "approval"}
        log = parse_log(_log())
        assert covered_topics(log, AS_OF) == {"labeling", "limits", "citation", "prompting"}
        md = report_markdown(log, AS_OF, usage, date(2026, 1, 1), "de")
        assert "Genutzte KI-Zwecke seit 2026-01-01: approval (1), d3_question (2), export (1)" in md
        assert "von keiner Maßnahme abgedeckt" in md and "approval —" in md and "export —" in md
        assert "citation" not in md.split("abgedeckt")[1].split("\n")[0]
        assert usage_from_audit(tmp_path / "missing.jsonl") == {}

    def test_report_without_audit_and_english(self) -> None:
        log = parse_log(_log())
        de = report_markdown(log, AS_OF, None, None, "de")
        assert de.startswith("# KI-Kompetenz-Nachweis (Art. 4 KI-VO) — Stab Demo") and "kein Nachweis übergeben" in de
        assert "| ART B | 0 | - | - | - | **keine Maßnahme** |" in de and "**auffrischen fällig**" in de
        assert "Einschätzung, keine Rechtsberatung" in de and "Teilnahmen: 16" in de
        en = report_markdown(log, AS_OF, None, None, "en")
        assert "AI literacy record" in en and "**refresh due**" in en and "Offer per topic" in en


class TestCli:
    def test_example_report_and_exit_codes(self, tmp_path, capsys) -> None:
        log = tmp_path / "ai_literacy.json"
        assert llm_main(["literacy", str(log), "--example"]) == 0
        assert llm_main(["literacy", str(log), "--example"]) == 1            # exists, no --force
        assert "--force" in capsys.readouterr().err
        assert llm_main(["literacy", str(log), "--example", "--force"]) == 0
        data = json.loads(log.read_text(encoding="utf-8"))
        assert data == example_log(date.today()) and "names" not in json.dumps(data)
        out = tmp_path / "report.md"
        rc = llm_main(["literacy", str(log), "--output", str(out), "--as-of", date.today().isoformat()])
        assert rc == 2                                                       # KM-1 is 15 months old -> due
        text = out.read_text(encoding="utf-8")
        assert "auffrischen fällig" in text and "Prüfsumme des Logs" in text
        assert "is due or has no measure" in capsys.readouterr().out
        # printed report, all current when as-of is right after the old measure
        early = (date.fromisoformat(data["measures"][0]["date"])).isoformat()
        assert llm_main(["literacy", str(log), "--as-of", early, "--lang", "en"]) == 2   # Stab has no measure yet
        assert "no measure" in capsys.readouterr().out

    def test_cli_errors(self, tmp_path, capsys) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"schema": 1, "measures": [{"id": "X", "names": ["a"]}]}', encoding="utf-8")
        assert llm_main(["literacy", str(bad)]) == 1 and "ERROR" in capsys.readouterr().err
        assert llm_main(["literacy", str(tmp_path / "none.json")]) == 1
        good = tmp_path / "good.json"
        good.write_text(json.dumps(_log()), encoding="utf-8")
        text, rc = run_literacy(good, as_of=AS_OF, output=tmp_path / "r" / "out.md")
        assert rc == 2 and (tmp_path / "r" / "out.md").read_text(encoding="utf-8") == text
