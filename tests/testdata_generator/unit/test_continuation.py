# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests der Fortschreibung (Schritt 2 der Generator-Überarbeitung): die
#   Vergangenheit bis T1 bleibt byteidentisch, geschlossene Vorgänge bleiben
#   unberührt, offene laufen weiter (nur Übergänge nach T1, keine nach T2),
#   neue Vorgänge kommen mit fortlaufenden Schlüsseln, Rate und Anzahl,
#   Determinismus je (Seed, T2), Metadaten im Envelope, Fehlerpfade, und
#   transform_data verarbeitet das Ergebnis ohne unbekannte Status.
# =============================================================================

from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from testdata_generator.continuation import (
    META_KEY,
    ContinuationError,
    config_from_meta,
    continue_generation,
    cut_timestamp,
    latest_timestamp,
    read_meta,
)
from testdata_generator.generator import GeneratorConfig, generate
from testdata_generator.workflow_parser import parse_workflow

WORKFLOW = Path(__file__).resolve().parents[3] / "testdata_generator" / "workflow_ART_A.txt"
T1 = date(2026, 1, 1)
T2 = date(2026, 3, 1)


@pytest.fixture(scope="module")
def wf():
    return parse_workflow(WORKFLOW)


@pytest.fixture(scope="module")
def first(wf):
    cfg = GeneratorConfig(project_key="ART", issue_count=120, from_date=date(2025, 7, 1),
                          to_date=T1, seed=5, realism=0.6, completion_rate=0.6)
    return generate(wf, cfg)


@pytest.fixture(scope="module")
def second(wf, first):
    return continue_generation(copy.deepcopy(first), wf, T2)


def _parse(ts: str) -> datetime:
    from testdata_generator.continuation import _parse_dt
    return _parse_dt(ts)


class TestMeta:
    def test_generate_writes_the_record(self, first, wf) -> None:
        meta = read_meta(first)
        assert meta is not None
        assert meta["to_date"] == T1.isoformat() and meta["seed"] == 5
        assert meta["stages"] == wf.stages and meta["continued_from"] == []
        cfg = config_from_meta(meta)
        assert cfg.realism == 0.6 and cfg.to_date == T1 and cfg.project_key == "ART"

    def test_continuation_updates_the_record(self, second) -> None:
        meta = read_meta(second)
        assert meta["to_date"] == T2.isoformat()
        assert meta["continued_from"] == [T1.isoformat()]
        assert meta["from_date"] == "2025-07-01"          # the first window's start survives

    def test_transform_data_ignores_the_record(self, second, wf, tmp_path) -> None:
        from transform_data.processor import process_issues
        raw = tmp_path / "second.json"
        raw.write_text(json.dumps(second), encoding="utf-8")
        records, unmapped = process_issues(
            raw, wf, reference_dt=datetime(2026, 3, 2, tzinfo=UTC))
        assert len(records) == len(second["issues"]) and not unmapped


class TestPastIsUntouchable:
    def test_every_old_issue_keeps_key_creation_and_history_up_to_t1(self, first, second) -> None:
        old = {i["key"]: i for i in first["issues"]}
        cut = cut_timestamp(T1)
        for key, before in old.items():
            after = next(i for i in second["issues"] if i["key"] == key)
            assert after["fields"]["created"] == before["fields"]["created"]
            assert after["fields"]["issuetype"] == before["fields"]["issuetype"]
            n = len(before["changelog"]["histories"])
            assert after["changelog"]["histories"][:n] == before["changelog"]["histories"]
            for h in after["changelog"]["histories"][n:]:
                assert _parse(h["created"]) > cut

    def test_closed_and_final_issues_are_byte_identical(self, first, second, wf) -> None:
        closed_idx = wf.stages.index(wf.closed_stage)
        old = {i["key"]: i for i in first["issues"]}
        touched = 0
        for key, before in old.items():
            if wf.stages.index(before["fields"]["status"]["name"]) >= closed_idx:
                after = next(i for i in second["issues"] if i["key"] == key)
                assert after == before
                touched += 1
        assert touched > 10


class TestOpenIssuesMoveOn:
    def test_some_open_issues_gain_transitions_after_t1_none_after_t2(self, first, second, wf) -> None:
        old = {i["key"]: i for i in first["issues"]}
        moved = 0
        end = cut_timestamp(T2)
        for key, before in old.items():
            after = next(i for i in second["issues"] if i["key"] == key)
            n = len(before["changelog"]["histories"])
            extra = after["changelog"]["histories"][n:]
            if extra:
                moved += 1
                assert all(_parse(h["created"]) <= end for h in extra)
                # the status follows the last transition
                assert after["fields"]["status"]["name"] == extra[-1]["items"][0]["toString"]
                assert after["changelog"]["total"] == len(after["changelog"]["histories"])
        assert moved >= 10

    def test_status_consistent_for_untouched_issues(self, second) -> None:
        for issue in second["issues"]:
            hist = issue["changelog"]["histories"]
            if hist:
                assert issue["fields"]["status"]["name"] == hist[-1]["items"][0]["toString"]


class TestNewIssues:
    def test_keys_continue_and_creation_lies_in_the_new_window(self, first, second) -> None:
        n_old = len(first["issues"])
        new = second["issues"][n_old:]
        assert new, "no new issues"
        numbers = [int(i["key"].rsplit("-", 1)[1]) for i in new]
        assert numbers == list(range(n_old + 1, n_old + 1 + len(new)))
        cut, end = cut_timestamp(T1), cut_timestamp(T2)
        for issue in new:
            assert cut < _parse(issue["fields"]["created"]) <= end
            for h in issue["changelog"]["histories"]:
                assert cut < _parse(h["created"]) <= end
            assert int(issue["id"]) == 100000 + int(issue["key"].rsplit("-", 1)[1]) - 1

    def test_default_count_follows_the_earlier_rate(self, first, second) -> None:
        n_old = len(first["issues"])
        days_before = (T1 - date(2025, 7, 1)).days + 1
        expected = round(n_old / days_before * (T2 - T1).days)
        assert len(second["issues"]) - n_old == expected

    def test_explicit_count_and_rate(self, first, wf) -> None:
        by_count = continue_generation(copy.deepcopy(first), wf, T2, new_issue_count=7)
        assert len(by_count["issues"]) == len(first["issues"]) + 7
        by_rate = continue_generation(copy.deepcopy(first), wf, T2, rate_per_day=0.5)
        assert len(by_rate["issues"]) == len(first["issues"]) + round(0.5 * (T2 - T1).days)
        none = continue_generation(copy.deepcopy(first), wf, T2, new_issue_count=0)
        assert len(none["issues"]) == len(first["issues"])

    def test_ids_are_unique(self, second) -> None:
        keys = [i["key"] for i in second["issues"]]
        ids = [i["id"] for i in second["issues"]]
        hist_ids = [h["id"] for i in second["issues"] for h in i["changelog"]["histories"]]
        assert len(set(keys)) == len(keys) and len(set(ids)) == len(ids)
        assert len(set(hist_ids)) == len(hist_ids)


class TestDeterminism:
    def test_same_t2_same_result(self, first, wf) -> None:
        a = continue_generation(copy.deepcopy(first), wf, T2)
        b = continue_generation(copy.deepcopy(first), wf, T2)
        assert a == b

    def test_other_t2_other_result(self, first, wf) -> None:
        a = continue_generation(copy.deepcopy(first), wf, T2)
        b = continue_generation(copy.deepcopy(first), wf, date(2026, 4, 1))
        assert a["issues"][:5] != b["issues"][:5] or len(a["issues"]) != len(b["issues"])

    def test_chained_continuation_keeps_the_whole_past(self, first, second, wf) -> None:
        third = continue_generation(copy.deepcopy(second), wf, date(2026, 5, 1))
        assert read_meta(third)["continued_from"] == [T1.isoformat(), T2.isoformat()]
        old = {i["key"]: i for i in second["issues"]}
        for key, before in old.items():
            after = next(i for i in third["issues"] if i["key"] == key)
            n = len(before["changelog"]["histories"])
            assert after["changelog"]["histories"][:n] == before["changelog"]["histories"]


class TestWithoutRecord:
    def test_latest_timestamp_defines_t1_and_knobs_must_be_given(self, first, wf) -> None:
        bare = copy.deepcopy(first)
        del bare[META_KEY]
        with pytest.raises(ContinuationError, match="generator record"):
            continue_generation(bare, wf, T2)
        cfg = GeneratorConfig(project_key="ART", from_date=date(2025, 7, 1), to_date=T1, seed=1)
        out = continue_generation(bare, wf, T2, config=cfg)
        t1 = latest_timestamp(first).date()
        assert read_meta(out)["continued_from"] == [t1.isoformat()]
        assert len(out["issues"]) > len(first["issues"])


class TestErrors:
    def test_t2_must_lie_after_t1(self, first, wf) -> None:
        with pytest.raises(ContinuationError, match="must lie after"):
            continue_generation(copy.deepcopy(first), wf, T1)

    def test_workflow_must_match_the_record(self, first, tmp_path) -> None:
        other = tmp_path / "wf.txt"
        other.write_text("A\nB\nC\n<First>A\n<Closed>C\n", encoding="utf-8")
        with pytest.raises(ContinuationError, match="stages differ"):
            continue_generation(copy.deepcopy(first), parse_workflow(other), T2)
