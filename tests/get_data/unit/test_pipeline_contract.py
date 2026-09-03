# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Contract-Test für C3: Beide Erhebungswege münden im selben Artefakt.
#   Ein (gemockter) REST-Abruf, dessen Seiten aus den ECHTEN Rohdaten des
#   Testdaten-Generators bestehen, schreibt eine Datei, die
#   transform_data.process_issues ohne Sonderbehandlung verarbeitet —
#   identisch zum manuellen Export derselben Daten.
# =============================================================================

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from get_data.client import JiraConfig, fetch_to_file
from transform_data.transform import process_issues
from transform_data.workflow import parse_workflow

_RAW = Path("testdata_generator/ART_A.json")
_WORKFLOW = Path("testdata_generator/workflow_ART_A.txt")


def test_fetched_file_feeds_transform_data_like_a_manual_export(tmp_path) -> None:
    raw = json.loads(_RAW.read_text(encoding="utf-8"))
    issues = raw["issues"]
    half = len(issues) // 2
    pages = [
        {"issues": issues[:half], "isLast": False, "nextPageToken": "t2"},
        {"issues": issues[half:], "isLast": True},
    ]

    calls = []

    def fake_urlopen(req, timeout=0):
        import io

        calls.append(req)

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.close()

        return _Resp(json.dumps(pages[len(calls) - 1]).encode("utf-8"))

    fetched = tmp_path / "ART_A_fetched.json"
    config = JiraConfig(base_url="https://jira.example.com", token="t",
                        project="ART_A", email="u@example.com")
    with patch("get_data.client._urlopen", side_effect=fake_urlopen):
        count = fetch_to_file(config, fetched, log=lambda m: None)
    assert count == len(issues)

    workflow = parse_workflow(_WORKFLOW)
    reference = datetime(2026, 1, 1, tzinfo=UTC)
    records_fetched, unmapped_fetched = process_issues(
        fetched, workflow, reference_dt=reference)
    records_manual, unmapped_manual = process_issues(
        _RAW, workflow, reference_dt=reference)

    assert not unmapped_fetched
    assert unmapped_fetched == unmapped_manual
    assert len(records_fetched) == len(records_manual)
