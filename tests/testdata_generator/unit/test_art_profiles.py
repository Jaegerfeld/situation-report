# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       04.09.2026
# Geändert:       04.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der ART-Profile des Demo-Portfolios: dieselben Regler wie
#   die Einzel-ART-Erzeugung (Ø-/σ-Cycle-Time, Muster + Stärke 0–100,
#   Backflow …), validierte Overrides je ART, prev/now-Semantik
#   (Override gilt in beiden Ständen, Story-Tweaks nur ohne Override)
#   und die Dialog-Helfer (Diff gegen Defaults).
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from testdata_generator.scenario import (
    STORY_NOW,
    STORY_PREV,
    _profiles,
    apply_art_overrides,
    build_portfolio_scenario,
    default_art_profile_rows,
    parse_art_profile_entries,
)

REF = date(2026, 6, 30)


def _by_name(profiles):
    return {p.name: p for _, p in profiles}


class TestApplyOverrides:
    def test_values_are_coerced_and_applied(self) -> None:
        merged = _by_name(apply_art_overrides(_profiles(), {
            "Alpha-1": {"mean_cycle_days": "60", "std_cycle_days": 5,
                        "issue_count": "80", "pattern": "Cluster",
                        "pattern_strength": 80}}))
        p = merged["Alpha-1"]
        assert p.mean_cycle_days == 60.0
        assert p.std_cycle_days == 5.0
        assert p.issue_count == 80
        assert p.pattern == "cluster"
        # Nutzerseitig 0–100, intern 0–1 (Konvention der Einzel-ART-GUI).
        assert p.pattern_strength == 0.8
        # Nicht überschriebene ARTs bleiben unangetastet.
        assert merged["Alpha-3"].mean_cycle_days == 45

    def test_unknown_art_field_pattern_and_range_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown ART name"):
            apply_art_overrides(_profiles(), {"Gamma-1": {}})
        with pytest.raises(ValueError, match="Unknown profile field"):
            apply_art_overrides(_profiles(), {"Alpha-1": {"foo": 1}})
        with pytest.raises(ValueError, match="Unknown pattern"):
            apply_art_overrides(_profiles(), {"Alpha-1": {"pattern": "zig"}})
        with pytest.raises(ValueError, match="0–100"):
            apply_art_overrides(_profiles(),
                                {"Alpha-1": {"pattern_strength": 300}})
        with pytest.raises(ValueError, match="number expected"):
            apply_art_overrides(_profiles(),
                                {"Alpha-1": {"mean_cycle_days": "viel"}})


class TestPrevNowSemantics:
    def test_override_wins_in_both_stands_with_throughput_scaling(
            self) -> None:
        overrides = {"Alpha-1": {"issue_count": 200}}
        now = _by_name(_profiles(STORY_NOW, overrides))["Alpha-1"]
        prev = _by_name(_profiles(STORY_PREV, overrides))["Alpha-1"]
        assert now.issue_count == 200
        # Durchsatz-Story bleibt: prev = 88 % des (überschriebenen) Werts.
        assert prev.issue_count == 176

    def test_beta3_story_tweak_only_without_override(self) -> None:
        default_prev = _by_name(_profiles(STORY_PREV))["Beta-3"]
        assert default_prev.todo_rate == 0.45  # Story: Lücken waren kleiner
        overridden_prev = _by_name(_profiles(
            STORY_PREV, {"Beta-3": {"todo_rate": 0.3}}))["Beta-3"]
        assert overridden_prev.todo_rate == 0.3  # Override gilt auch prev


class TestDialogHelpers:
    def test_unchanged_entries_yield_no_overrides(self) -> None:
        assert parse_art_profile_entries(default_art_profile_rows()) == {}

    def test_changed_fields_become_overrides(self) -> None:
        rows = default_art_profile_rows()
        rows["Alpha-3"]["mean_cycle_days"] = "90"
        rows["Beta-1"]["pattern"] = "batch"
        rows["Beta-2"]["std_cycle_days"] = "4"  # Default war leer (=auto)
        overrides = parse_art_profile_entries(rows)
        assert overrides == {"Alpha-3": {"mean_cycle_days": "90"},
                             "Beta-1": {"pattern": "batch"},
                             "Beta-2": {"std_cycle_days": "4"}}

    def test_invalid_entries_raise_at_ok_time(self) -> None:
        rows = default_art_profile_rows()
        rows["Alpha-1"]["pattern_strength"] = "999"
        with pytest.raises(ValueError, match="0–100"):
            parse_art_profile_entries(rows)


class TestEndToEnd:
    def test_scenario_respects_overrides(self, tmp_path) -> None:
        import openpyxl
        paths = build_portfolio_scenario(
            tmp_path, seed=42, reference=REF, scale="s",
            log=lambda m: None,
            art_profiles={"Alpha-1": {"issue_count": 30,
                                      "pattern": "cluster",
                                      "pattern_strength": 70}})
        ws = openpyxl.load_workbook(
            tmp_path / "solutions" / "alpha" / "arts"
            / "Alpha-1_IssueTimes.xlsx").active
        assert ws.max_row - 1 == 30
        # Delta-Story lebt weiter (prev nutzt dieselben Overrides).
        from portfolio.delta import compute_delta
        from portfolio.snapshot import load_snapshot
        delta = compute_delta(load_snapshot(paths["snapshot_prev"]),
                              load_snapshot(paths["snapshot_now"]))
        assert not delta.quiet and delta.completed_delta > 0
