# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.05.2026
# Geändert:       12.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für testdata_generator.cli: _parse_date, _parse_issue_types,
#   run_generate (Pipeline-Steuerung, Fehlerbehandlung) und main()
#   (Argument-Parsing). Externe I/O-Aufrufe werden gemockt.
# =============================================================================

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from testdata_generator.cli import _parse_date, _parse_issue_types, run_generate


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid_date(self):
        assert _parse_date("2025-06-15") == date(2025, 6, 15)

    def test_invalid_format_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
            _parse_date("15.06.2025")

    def test_invalid_date_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid date"):
            _parse_date("2025-13-01")


# ---------------------------------------------------------------------------
# _parse_issue_types
# ---------------------------------------------------------------------------

class TestParseIssueTypes:
    def test_valid_single_entry(self):
        result = _parse_issue_types(["Feature:0.6"])
        assert result == {"Feature": 0.6}

    def test_valid_multiple_entries(self):
        result = _parse_issue_types(["Feature:0.6", "Bug:0.3", "Enabler:0.1"])
        assert result == {"Feature": 0.6, "Bug": 0.3, "Enabler": 0.1}

    def test_malformed_entry_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="TypeName:weight"):
            _parse_issue_types(["FeatureOnly"])

    def test_invalid_weight_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be a number"):
            _parse_issue_types(["Feature:not_a_number"])

    def test_negative_weight_raises(self):
        with pytest.raises(argparse.ArgumentTypeError, match="non-negative"):
            _parse_issue_types(["Feature:-0.5"])


# ---------------------------------------------------------------------------
# run_generate — pipeline orchestration
# ---------------------------------------------------------------------------

class TestRunGenerate:
    def test_date_order_error_is_logged_and_returns(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n<First>Funnel\n<Closed>Done\n")
        out = tmp_path / "out.json"
        logged = []
        run_generate(
            workflow=wf,
            output=out,
            from_date=date(2025, 12, 31),
            to_date=date(2025, 1, 1),
            log=logged.append,
        )
        assert any("ERROR" in m for m in logged)
        assert not out.exists()

    def test_run_generate_success(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n<First>Funnel\n<Closed>Done\n")
        out = tmp_path / "out.json"
        logged = []
        run_generate(
            workflow=wf,
            output=out,
            issue_count=5,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31),
            seed=42,
            log=logged.append,
        )
        assert out.exists()
        assert any("Done" in m for m in logged)


# ---------------------------------------------------------------------------
# main() — argparse integration
# ---------------------------------------------------------------------------

class TestMain:
    def _run_main(self, argv: list[str]) -> MagicMock:
        from testdata_generator.cli import main
        with patch("sys.argv", ["prog"] + argv), \
             patch("testdata_generator.cli.run_generate") as mock_run:
            main()
        return mock_run

    def test_minimal_invocation(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n<First>Funnel\n<Closed>Done\n")
        mock = self._run_main(["--workflow", str(wf)])
        assert mock.called
        assert mock.call_args[1]["workflow"] == wf

    def test_issue_count_forwarded(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n")
        mock = self._run_main(["--workflow", str(wf), "--issues", "42"])
        assert mock.call_args[1]["issue_count"] == 42

    def test_project_key_forwarded(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n")
        mock = self._run_main(["--workflow", str(wf), "--project", "ART_A"])
        assert mock.call_args[1]["project_key"] == "ART_A"

    def test_seed_forwarded(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n")
        mock = self._run_main(["--workflow", str(wf), "--seed", "99"])
        assert mock.call_args[1]["seed"] == 99

    def test_issue_types_parsed_and_forwarded(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n")
        mock = self._run_main(
            ["--workflow", str(wf), "--issue-types", "Feature:0.7", "Bug:0.3"]
        )
        assert mock.call_args[1]["issue_types"] == {"Feature": 0.7, "Bug": 0.3}

    def test_invalid_issue_types_exits(self, tmp_path):
        wf = tmp_path / "wf.txt"
        wf.write_text("Funnel\nDone\n")
        from testdata_generator.cli import main
        with patch("sys.argv", ["prog", "--workflow", str(wf), "--issue-types", "bad"]), \
             pytest.raises(SystemExit):
            main()
