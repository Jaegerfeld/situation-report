# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für helper.merger.merge_json_files(). Prüfen die technische
#   Korrektheit der Merge-Logik: Envelope-Felder, Deduplizierung, Edge Cases.
# =============================================================================

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helper.merger import merge_json_files


def _write_json(path: Path, issues: list[dict], expand: str = "schema,names") -> Path:
    """Write a minimal Jira-API-format JSON file to path."""
    data = {
        "expand": expand,
        "startAt": 0,
        "maxResults": len(issues),
        "total": len(issues),
        "issues": issues,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_issues(start_id: int, count: int) -> list[dict]:
    """Create count minimal issue dicts with unique numeric ids."""
    return [{"id": str(start_id + i), "key": f"TEST-{start_id + i}"} for i in range(count)]


class TestMergeBasic:
    def test_two_files_combined(self, tmp_path: Path) -> None:
        """Issues from two files are combined into one list."""
        f1 = _write_json(tmp_path / "a.json", _make_issues(1, 3))
        f2 = _write_json(tmp_path / "b.json", _make_issues(4, 3))
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out)
        result = json.loads(out.read_text())
        assert len(result["issues"]) == 6

    def test_single_file_passthrough(self, tmp_path: Path) -> None:
        """A single input file produces identical issues in the output."""
        issues = _make_issues(1, 5)
        f1 = _write_json(tmp_path / "a.json", issues)
        out = tmp_path / "merged.json"
        merge_json_files([f1], out)
        result = json.loads(out.read_text())
        assert result["issues"] == issues

    def test_envelope_fields(self, tmp_path: Path) -> None:
        """Output envelope has startAt=0, total=n, maxResults=n."""
        f1 = _write_json(tmp_path / "a.json", _make_issues(1, 4))
        f2 = _write_json(tmp_path / "b.json", _make_issues(5, 3))
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out)
        result = json.loads(out.read_text())
        assert result["startAt"] == 0
        assert result["total"] == 7
        assert result["maxResults"] == 7


class TestDeduplication:
    def test_duplicate_by_id_removed(self, tmp_path: Path) -> None:
        """Issues with the same id appear only once in the output."""
        shared = [{"id": "99", "key": "TEST-99"}]
        f1 = _write_json(tmp_path / "a.json", shared + _make_issues(1, 2))
        f2 = _write_json(tmp_path / "b.json", shared + _make_issues(3, 2))
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out, deduplicate=True)
        result = json.loads(out.read_text())
        ids = [i["id"] for i in result["issues"]]
        assert ids.count("99") == 1
        assert result["total"] == 5

    def test_dedup_logs_warning(self, tmp_path: Path) -> None:
        """A duplicate issue triggers a warning log message."""
        shared = [{"id": "42", "key": "TEST-42"}]
        f1 = _write_json(tmp_path / "a.json", shared)
        f2 = _write_json(tmp_path / "b.json", shared)
        out = tmp_path / "merged.json"
        messages: list[str] = []
        merge_json_files([f1, f2], out, deduplicate=True, log=messages.append)
        assert any("42" in m and "WARNING" in m for m in messages)

    def test_no_dedup_keeps_duplicates(self, tmp_path: Path) -> None:
        """With deduplicate=False, all issues including duplicates are kept."""
        shared = [{"id": "99", "key": "TEST-99"}]
        f1 = _write_json(tmp_path / "a.json", shared)
        f2 = _write_json(tmp_path / "b.json", shared)
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out, deduplicate=False)
        result = json.loads(out.read_text())
        assert result["total"] == 2


class TestEdgeCases:
    def test_empty_issues_array(self, tmp_path: Path) -> None:
        """A file with an empty issues array is handled without error."""
        f1 = _write_json(tmp_path / "a.json", [])
        f2 = _write_json(tmp_path / "b.json", _make_issues(1, 2))
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out)
        result = json.loads(out.read_text())
        assert result["total"] == 2

    def test_missing_issues_key_raises(self, tmp_path: Path) -> None:
        """A file missing the 'issues' key raises ValueError."""
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"total": 0}), encoding="utf-8")
        out = tmp_path / "merged.json"
        with pytest.raises(ValueError, match="issues"):
            merge_json_files([bad], out)

    def test_output_dir_created(self, tmp_path: Path) -> None:
        """The output directory is created automatically if it does not exist."""
        f1 = _write_json(tmp_path / "a.json", _make_issues(1, 1))
        out = tmp_path / "subdir" / "nested" / "merged.json"
        merge_json_files([f1], out)
        assert out.exists()

    def test_expand_from_first_file(self, tmp_path: Path) -> None:
        """The expand value in the output is taken from the first input file."""
        f1 = _write_json(tmp_path / "a.json", _make_issues(1, 1), expand="custom,expand")
        f2 = _write_json(tmp_path / "b.json", _make_issues(2, 1), expand="other")
        out = tmp_path / "merged.json"
        merge_json_files([f1, f2], out)
        result = json.loads(out.read_text())
        assert result["expand"] == "custom,expand"

    def test_no_inputs_raises(self, tmp_path: Path) -> None:
        """An empty inputs list raises ValueError."""
        with pytest.raises(ValueError):
            merge_json_files([], tmp_path / "out.json")
