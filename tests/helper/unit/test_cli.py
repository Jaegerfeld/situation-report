# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.05.2026
# Geändert:       12.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für helper.cli: run_merge (Fehlerbehandlung, Erfolgsfall)
#   und main() (Argument-Parsing). Externe Aufrufe werden gemockt.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from helper.cli import run_merge


# ---------------------------------------------------------------------------
# run_merge — error branches
# ---------------------------------------------------------------------------

class TestRunMerge:
    def _write_jira_json(self, path: Path, issues: list[dict]) -> None:
        data = {"expand": "schema", "startAt": 0, "maxResults": len(issues),
                "total": len(issues), "issues": issues}
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_missing_input_file_logs_error_and_returns(self, tmp_path):
        missing = tmp_path / "missing.json"
        out = tmp_path / "out.json"
        logged = []
        run_merge(inputs=[missing], output=out, log=logged.append)
        assert any("ERROR" in m for m in logged)
        assert not out.exists()

    def test_value_error_from_merger_is_logged(self, tmp_path):
        f = tmp_path / "f.json"
        f.write_text("{}")  # invalid format → merger raises ValueError
        out = tmp_path / "out.json"
        logged = []
        run_merge(inputs=[f], output=out, log=logged.append)
        assert any("ERROR" in m for m in logged)

    def test_success_creates_output(self, tmp_path):
        f = tmp_path / "a.json"
        self._write_jira_json(f, [{"id": "1", "key": "T-1"}])
        out = tmp_path / "out.json"
        logged = []
        run_merge(inputs=[f], output=out, log=logged.append)
        assert out.exists()
        assert any("Done" in m for m in logged)


# ---------------------------------------------------------------------------
# main() — argparse integration
# ---------------------------------------------------------------------------

class TestMain:
    def _run_main(self, argv: list[str]) -> None:
        from helper.cli import main
        with patch("sys.argv", ["prog"] + argv), \
             patch("helper.cli.run_merge") as mock_run:
            main()
        return mock_run

    def test_inputs_and_output_forwarded(self, tmp_path):
        f1 = tmp_path / "a.json"
        f1.touch()
        out = tmp_path / "out.json"
        mock = self._run_main([str(f1), "--output", str(out)])
        assert mock.called
        assert mock.call_args[1]["output"] == out
        assert f1 in mock.call_args[1]["inputs"]

    def test_dedup_enabled_by_default(self, tmp_path):
        f1 = tmp_path / "a.json"
        f1.touch()
        out = tmp_path / "out.json"
        mock = self._run_main([str(f1), "--output", str(out)])
        assert mock.call_args[1]["deduplicate"] is True

    def test_no_dedup_flag_disables_dedup(self, tmp_path):
        f1 = tmp_path / "a.json"
        f1.touch()
        out = tmp_path / "out.json"
        mock = self._run_main([str(f1), "--output", str(out), "--no-dedup"])
        assert mock.call_args[1]["deduplicate"] is False
