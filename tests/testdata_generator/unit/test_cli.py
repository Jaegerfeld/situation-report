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
from datetime import date
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


class TestRunContinue:
    """0.39.0: the CLI path of the continuation — file in, second extract out."""

    def _first(self, tmp_path):
        from pathlib import Path as _P
        wf = _P(__file__).resolve().parents[3] / "testdata_generator" / "workflow_ART_A.txt"
        out = tmp_path / "first.json"
        run_generate(wf, out, project_key="ART", issue_count=60, from_date=date(2025, 7, 1),
                     to_date=date(2026, 1, 1), seed=3, realism=0.5, log=lambda m: None)
        return wf, out

    def test_writes_next_to_the_source_and_logs_counts(self, tmp_path):
        from testdata_generator.cli import run_continue
        wf, first = self._first(tmp_path)
        lines: list[str] = []
        written = run_continue(first, wf, date(2026, 3, 1), log=lines.append)
        assert written == tmp_path / "first_2026-03-01.json" and written.exists()
        assert any("Issues before:   60" in li for li in lines)
        assert any("New issues:" in li for li in lines)

    def test_explicit_output_count_and_realism_override(self, tmp_path):
        import json

        from testdata_generator.cli import run_continue
        from testdata_generator.continuation import read_meta
        wf, first = self._first(tmp_path)
        target = tmp_path / "out" / "second.json"
        written = run_continue(first, wf, date(2026, 2, 1), output=target,
                               new_issue_count=5, realism=0.9, log=lambda m: None)
        data = json.loads(written.read_text(encoding="utf-8"))
        assert len(data["issues"]) == 65
        assert read_meta(data)["config"]["realism"] == 0.9

    def test_errors_are_logged_not_raised(self, tmp_path):
        from testdata_generator.cli import run_continue
        wf, first = self._first(tmp_path)
        lines: list[str] = []
        assert run_continue(first, wf, date(2025, 12, 1), log=lines.append) is None
        assert any("must lie after" in li for li in lines)
        assert run_continue(tmp_path / "nope.json", wf, date(2026, 3, 1),
                            log=lines.append) is None
        assert any("cannot read" in li for li in lines)

    def test_main_dispatches_continue(self, tmp_path, monkeypatch, capsys):
        import sys

        from testdata_generator.cli import main
        wf, first = self._first(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "testdata_generator", "--workflow", str(wf), "--continue", str(first),
            "--to-date", "2026-03-01", "--issues", "4"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "New issues:      4" in out
        assert (tmp_path / "first_2026-03-01.json").exists()

    def test_main_continue_needs_to_date(self, tmp_path, monkeypatch, capsys):
        import sys

        from testdata_generator.cli import main
        wf, first = self._first(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "testdata_generator", "--workflow", str(wf), "--continue", str(first)])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2
        assert "needs --to-date" in capsys.readouterr().err
