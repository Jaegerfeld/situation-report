# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.10.2026
# Geändert:       14.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Fakten-Index (D3-Provenienz): Pfade in Klammerschreibweise,
#   Kennzahlen, Quell-Konfidenz, Register-Felder, Rekurrenz je Naht, Vorstand
#   und Veränderung, Harmonisierung, Scope, KEINE Personenfelder (Leitplanke
#   b), Freitext als Daten (gekürzt, ohne Steuerzeichen, ohne eckige Klammern),
#   stabile Prüfsumme, Zeilenformat lesbar für den Zitat-Wächter.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from llm.guard import parse_fact_lines
from portfolio.facts import (
    PERSON_FIELDS,
    TEXT_LIMIT,
    Fact,
    build_fact_index,
    sanitize_text,
)
from portfolio.snapshot import Snapshot, load_snapshot

REF = date(2026, 10, 13)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    return build_portfolio_scenario(tmp_path_factory.mktemp("demo"), seed=42, reference=REF,
                                    log=lambda m: None)


@pytest.fixture(scope="module")
def stands(demo):
    return load_snapshot(demo["snapshot_prev"]), load_snapshot(demo["snapshot_now"])


class TestSanitize:
    def test_text_is_data(self) -> None:
        assert sanitize_text("a\x00b\nc  d [x]") == "ab c d (x)"
        long = sanitize_text("x" * 500)
        assert len(long) == TEXT_LIMIT and long.endswith("…")

    def test_fact_line_round_trips_through_the_guard_parser(self) -> None:
        f = Fact("S1/units(ART Alpha-2).open", "41", "open", "2026-10-13", "Alpha")
        assert f.line() == "- [S1/units(ART Alpha-2).open] open = 41 (as of 2026-10-13; Alpha)"
        parsed = parse_fact_lines(f.line())
        assert list(parsed) == ["S1/units(ART Alpha-2).open"] and "41" in parsed[f.path]


class TestIndex:
    def test_metrics_sources_registers_and_seams(self, stands) -> None:
        _, now = stands
        idx = build_fact_index(now)
        paths = idx.paths
        assert "S1/total.median_ct" in paths and "S1/total.items" in paths
        assert any(p.startswith("S1/units(") and p.endswith(").open") for p in paths)
        assert any(p.startswith("S1/sources(") and p.endswith(").confidence") for p in paths)
        assert any(p.startswith("S1/governance.dependencies(") and p.endswith(").status") for p in paths)
        seam = idx.by_path["S1/governance.solution_areas.seams(ART Alpha-1 x ART Alpha-3).recurrence"]
        assert seam.value.startswith("3 (topic: test environment)")
        assert idx.as_of == "2026-10-13" and idx.prev_as_of == "" and len(idx) > 100

    def test_no_person_fields_anywhere(self, stands) -> None:
        _, now = stands
        assert any("owner" in e for e in now.governance["risks"])   # the snapshot has them ...
        idx = build_fact_index(now)
        for f in idx.facts:                                           # ... the index never
            assert f.path.rsplit(".", 1)[-1] not in PERSON_FIELDS, f.path
            assert "owner" not in f.path.lower()

    def test_free_text_marked_as_data_and_bounded(self, stands) -> None:
        _, now = stands
        idx = build_fact_index(now)
        titles = [f for f in idx.facts if f.path.endswith(").title")]
        assert titles and all(f.value.startswith("text: ") for f in titles)
        assert all("[" not in f.value and "\n" not in f.value for f in idx.facts)

    def test_prev_and_delta(self, stands) -> None:
        prev, now = stands
        idx = build_fact_index(now, prev=prev)
        assert "S0/total.median_ct" in idx.paths and "D/total.completed" in idx.paths
        d = idx.by_path["D/total.completed"]
        assert d.value.startswith(("+", "-")) and idx.prev_as_of == prev.as_of.isoformat()
        assert "S0 = stand as of" in idx.to_markdown()

    def test_scopes(self, stands) -> None:
        _, now = stands
        metrics = build_fact_index(now, scope="metrics")
        registers = build_fact_index(now, scope="registers")
        assert all(not p.startswith("S1/governance") for p in metrics.paths)
        assert all(p.startswith("S1/governance") for p in registers.paths)
        with pytest.raises(ValueError, match="scope"):
            build_fact_index(now, scope="everything")

    def test_harmonisation_facts(self, tmp_path) -> None:
        from harmonisation.examples import write_example
        from harmonisation.model import load_workspace
        write_example(tmp_path)
        ws = load_workspace(tmp_path)
        snap = Snapshot(name="S", kind="solution", as_of=REF, created="x", target_ct=90,
                        total={"label": "S", "items": 3, "completed": 2, "open": 1})
        idx = build_fact_index(snap, harmonisation=[("Solution S", ws)])
        h = [f for f in idx.facts if f.path.startswith("H/process(")]
        assert h and any(f.path.endswith(".confidence") for f in h)
        assert all(f.source == "Solution S" for f in h)
        assert "H = harmonisation matrix" in idx.to_markdown()
        assert all(not p.startswith("H/") for p in build_fact_index(snap, harmonisation=[("S", ws)],
                                                                      scope="metrics").paths)

    def test_digest_is_stable_and_changes_with_content(self, stands) -> None:
        prev, now = stands
        a, b = build_fact_index(now), build_fact_index(now)
        assert a.digest() == b.digest() and a.digest() != build_fact_index(prev).digest()
