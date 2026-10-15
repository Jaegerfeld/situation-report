# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       15.10.2026
# Geändert:       15.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests der Datenminimierung ab Quelle (R1): Allowlist der Issue-Felder,
#   Changelog bleibt vollständig (jede Historie, jedes Item) mit anonymi-
#   siertem Autor, maskierten Personen-Items und geleerten Textwerten;
#   Report zählt; --keep nur für Nicht-Personenfelder; idempotent; die
#   Pipeline liefert aus roh und minimiert identische Kennzahlen (Contract);
#   REST-Abruf minimiert immer; check warnt vor Personendaten; CLI minimise
#   schreibt <name>_min.json und lässt das Original stehen.
# =============================================================================

from __future__ import annotations

import copy
import json
from unittest.mock import patch

import pytest

from get_data.cli import main as cli_main
from get_data.client import DEFAULT_FIELDS, JiraConfig, fetch_to_file
from get_data.minimise import (
    ANONYMISED,
    check_keep,
    default_output,
    minimise_export,
    minimise_file,
    person_field_hits,
)
from get_data.validate import validate_export

_AUTHOR = {"self": "u", "name": "jdoe", "key": "jdoe", "emailAddress": "j.doe@example.com",
           "displayName": "Jane Doe", "avatarUrls": {"48x48": "x"}, "active": True,
           "timeZone": "Europe/Berlin"}


def _issue(key: str = "A-1") -> dict:
    return {
        "id": "1", "key": key, "self": "https://j/rest/api/3/issue/1", "expand": "changelog",
        "fields": {
            "project": {"id": "9", "key": "A", "name": "Alpha", "projectTypeKey": "software"},
            "issuetype": {"id": "3", "name": "Story", "iconUrl": "x"},
            "status": {"id": "5", "name": "Done", "statusCategory": {"name": "Done"}},
            "created": "2025-01-01T09:00:00.000+0000",
            "resolution": {"name": "Done", "id": "1"},
            "components": [{"id": "7", "name": "Core"}],
            "summary": "Fix login for Jane Doe", "description": "long text",
            "assignee": copy.deepcopy(_AUTHOR), "reporter": copy.deepcopy(_AUTHOR),
            "creator": copy.deepcopy(_AUTHOR), "labels": ["x"],
            "comment": {"comments": [{"author": _AUTHOR, "body": "hi"}]},
            "customfield_11404": "sprint 3",
        },
        "changelog": {"startAt": 0, "maxResults": 3, "total": 3, "histories": [
            {"id": "h1", "author": copy.deepcopy(_AUTHOR), "created": "2025-01-02T09:00:00.000+0000",
             "items": [{"field": "status", "fieldtype": "jira", "from": "1", "fromString": "To Do",
                        "to": "3", "toString": "In Progress"}]},
            {"id": "h2", "author": copy.deepcopy(_AUTHOR), "created": "2025-01-03T09:00:00.000+0000",
             "items": [{"field": "assignee", "fieldtype": "jira", "from": None, "fromString": None,
                        "to": "jdoe", "toString": "Jane Doe"},
                       {"field": "description", "fieldtype": "jira", "fromString": "old text",
                        "toString": "new text with a name"}]},
            {"id": "h3", "author": copy.deepcopy(_AUTHOR), "created": "2025-01-04T09:00:00.000+0000",
             "items": [{"field": "status", "fieldtype": "jira", "from": "3", "fromString": "In Progress",
                        "to": "5", "toString": "Done"}]},
        ]},
    }


class TestMinimise:
    def test_allowlist_keeps_pipeline_fields_only(self) -> None:
        out, rep = minimise_export({"total": 1, "startAt": 0, "issues": [_issue()]})
        f = out["issues"][0]["fields"]
        assert set(f) == {"project", "issuetype", "status", "created", "resolution", "components"}
        assert f["project"] == {"key": "A", "name": "Alpha"} and f["issuetype"] == {"name": "Story"}
        assert f["components"] == [{"name": "Core"}] and f["created"].startswith("2025-01-01")
        assert set(out["issues"][0]) == {"id", "key", "fields", "changelog"}
        assert out["total"] == 1 and rep.issues == 1
        assert rep.person_fields == {"assignee": 1, "reporter": 1, "creator": 1, "comment": 1}
        assert "summary" in rep.dropped_fields and "customfield_11404" in rep.dropped_fields

    def test_changelog_stays_complete_with_persons_anonymised(self) -> None:
        out, rep = minimise_export([_issue()])
        hist = out[0]["changelog"]["histories"]
        assert [h["id"] for h in hist] == ["h1", "h2", "h3"] and out[0]["changelog"]["total"] == 3
        assert all(h["author"] == {"displayName": ANONYMISED} for h in hist)
        assert [len(h["items"]) for h in hist] == [1, 2, 1]                 # no item dropped
        assert hist[0]["items"][0]["toString"] == "In Progress"             # status untouched
        assignee = hist[1]["items"][0]
        assert assignee["field"] == "assignee" and assignee["toString"] == ANONYMISED
        assert assignee["to"] == ANONYMISED and assignee["fromString"] == ANONYMISED
        desc = hist[1]["items"][1]
        assert desc["field"] == "description" and "fromString" not in desc and "toString" not in desc
        assert rep.authors == 3 and rep.person_items == {"assignee": 1} and rep.text_items == {"description": 1}
        text = json.dumps(out)
        assert "Jane" not in text and "example.com" not in text and "jdoe" not in text

    def test_idempotent_and_report_lines(self) -> None:
        once, rep1 = minimise_export([_issue()])
        twice, rep2 = minimise_export(copy.deepcopy(once))
        assert twice == once and not rep2.changed and rep2.persons_total == 0
        assert "nothing to remove" in " ".join(rep2.lines())
        lines = " ".join(rep1.lines())
        assert "authors anonymised: 3" in lines and "assignee (1 issues)" in lines
        assert rep1.persons_total == 4 + 3 + 1

    def test_keep_allows_non_person_fields_only(self) -> None:
        out, rep = minimise_export([_issue()], keep=("summary", "labels"))
        assert out[0]["fields"]["summary"].startswith("Fix login") and out[0]["fields"]["labels"] == ["x"]
        assert rep.kept_extra == ("summary", "labels")
        with pytest.raises(ValueError, match="Person fields cannot be kept"):
            check_keep(("summary", "assignee"))
        with pytest.raises(ValueError, match="Not a Jira export"):
            minimise_export({"foo": 1})

    def test_person_hits_find_raw_and_not_minimised(self) -> None:
        raw = [_issue()]
        hits = person_field_hits(raw)
        assert hits["fields.assignee"] == 1 and hits["changelog.author"] == 3
        assert hits["changelog.items.assignee"] == 1
        assert person_field_hits(minimise_export(raw)[0]) == {}

    def test_real_testdata_pipeline_contract(self, ata_json, ata_workflow, tmp_path) -> None:
        from datetime import UTC, datetime

        from transform_data.transform import process_issues
        from transform_data.workflow import parse_workflow
        raw = json.loads(ata_json.read_text(encoding="utf-8"))
        slim, rep = minimise_export(copy.deepcopy(raw))
        assert rep.authors > 0 and "customfield_11404" in rep.dropped_fields
        slim_path = tmp_path / "ART_A_min.json"
        slim_path.write_text(json.dumps(slim), encoding="utf-8")
        wf = parse_workflow(ata_workflow)
        ref = datetime(2026, 1, 1, tzinfo=UTC)
        before = process_issues(ata_json, wf, reference_dt=ref)
        after = process_issues(slim_path, wf, reference_dt=ref)
        assert before == after
        assert slim_path.stat().st_size < ata_json.stat().st_size


class TestWiring:
    def test_fetch_always_minimises(self, tmp_path) -> None:
        envelope = {"expand": "changelog", "startAt": 0, "maxResults": 1, "total": 1,
                    "issues": [_issue()]}
        logs: list[str] = []
        with patch("get_data.client.fetch_issues", return_value=envelope):
            n = fetch_to_file(JiraConfig(base_url="https://j", token="t", project="A",
                                         email="e@x"), tmp_path / "o.json", log=logs.append)
        data = json.loads((tmp_path / "o.json").read_text(encoding="utf-8"))
        assert n == 1 and "assignee" not in data["issues"][0]["fields"]
        assert data["issues"][0]["changelog"]["histories"][0]["author"] == {"displayName": ANONYMISED}
        assert any("authors anonymised" in line for line in logs)
        assert "summary" not in DEFAULT_FIELDS and "components" in DEFAULT_FIELDS

    def test_fetch_keep_extends_fields_and_rejects_persons(self, tmp_path, monkeypatch, capsys) -> None:
        monkeypatch.setenv("JIRA_TOKEN", "tok")
        with patch("get_data.cli.fetch_to_file", return_value=1) as m:
            assert cli_main(["fetch", "--url", "https://j", "--project", "A", "--output",
                             str(tmp_path / "o.json"), "--keep", "summary", "labels"]) == 0
        assert m.call_args.args[0].fields[-2:] == ("summary", "labels")
        assert m.call_args.kwargs["keep"] == ("summary", "labels")
        assert cli_main(["fetch", "--url", "https://j", "--project", "A", "--output",
                         str(tmp_path / "o.json"), "--keep", "reporter"]) == 1
        assert "Person fields cannot be kept" in capsys.readouterr().err

    def test_check_warns_about_persons(self) -> None:
        check = validate_export({"issues": [_issue()]})
        assert check.ok and any("person data" in w and "minimise" in w for w in check.warnings)
        assert not any("person data" in w for w in validate_export(minimise_export([_issue()])[0]).warnings)

    def test_cli_minimise_writes_new_file_and_keeps_original(self, tmp_path, capsys) -> None:
        src = tmp_path / "ART_A.json"
        src.write_text(json.dumps({"issues": [_issue()]}), encoding="utf-8")
        assert default_output(src) == tmp_path / "ART_A_min.json"
        assert cli_main(["minimise", str(src)]) == 0
        out = capsys.readouterr().out
        assert "ART_A_min.json" in out and "still holds person data" in out
        assert "Jane" in src.read_text(encoding="utf-8")
        assert "Jane" not in (tmp_path / "ART_A_min.json").read_text(encoding="utf-8")
        target, rep = minimise_file(src, tmp_path / "x" / "slim.json", ("labels",))
        assert target.is_file() and rep.kept_extra == ("labels",)
        assert cli_main(["minimise", str(tmp_path / "missing.json")]) == 1
        assert cli_main(["minimise", str(src), "--keep", "author"]) == 1
