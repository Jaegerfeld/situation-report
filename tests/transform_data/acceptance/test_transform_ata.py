# =============================================================================
# Autor:          Robert Seebauer
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.04.2026
# Geändert:       14.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Acceptance-Tests für transform_data auf Basis des realen ART_A-Datensatzes.
#   Prüft fachliche Korrektheit der gesamten Pipeline: Vollständigkeit der
#   verarbeiteten Issues, chronologische Sortierung der Transitions,
#   Korrektheit der Meilenstein-Daten (First Date, Closed Date),
#   Plausibilität der Stage-Minuten sowie Invarianten für den CFD.
#   Ein fixer Referenzzeitpunkt gewährleistet reproduzierbare Ergebnisse.
# =============================================================================

"""
Acceptance tests for transform_data using the real ART_A dataset.

These tests verify business/domain correctness, not technical implementation
details. They use the actual ART_A.json export and the original workflow
definition to ensure the pipeline meets its functional requirements.

A fixed reference_dt is used so results are reproducible across runs.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from transform_data.workflow import parse_workflow
from transform_data.processor import process_issues

# Fixed reference date → stage minutes for open issues are deterministic
REFERENCE_DT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def workflow(ata_workflow: Path):
    return parse_workflow(ata_workflow)


@pytest.fixture(scope="module")
def result(ata_json: Path, workflow):
    records, unmapped = process_issues(ata_json, workflow, REFERENCE_DT)
    return records, unmapped


@pytest.fixture(scope="module")
def records(result):
    return result[0]


@pytest.fixture(scope="module")
def unmapped(result):
    return result[1]


@pytest.fixture(scope="module")
def by_key(records):
    return {r.key: r for r in records}


# ---------------------------------------------------------------------------
# Vollständigkeit
# ---------------------------------------------------------------------------

class TestCompleteness:
    def test_all_issues_processed(self, records):
        """Die JSON enthält 533 Issues — alle müssen verarbeitet werden."""
        assert len(records) == 533

    def test_every_issue_has_all_stage_columns(self, records, workflow):
        """Jedes Issue hat einen Eintrag für jede Stage im Workflow."""
        for r in records:
            assert set(r.stage_minutes.keys()) == set(workflow.stages)

    def test_every_issue_has_a_key(self, records):
        assert all(r.key.startswith("ART_A-") for r in records)

    def test_every_issue_has_a_project(self, records):
        assert all(r.project == "ART_A" for r in records)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

class TestTransitions:
    def test_first_transition_is_always_created(self, records):
        """Das erste Element jeder Transitions-Liste muss 'Created' sein."""
        for r in records:
            assert r.transitions[0].label == "Created"

    def test_transitions_are_chronologically_ordered(self, records):
        for r in records:
            timestamps = [t.timestamp for t in r.transitions]
            assert timestamps == sorted(timestamps), f"{r.key}: Transitions nicht sortiert"

    def test_known_issue_has_expected_transition(self, by_key):
        """ART_A-739 wechselt direkt nach der Erstellung in Analysis."""
        r = by_key["ART_A-739"]
        labels = [t.label for t in r.transitions]
        assert "Analysis" in labels


# ---------------------------------------------------------------------------
# Datums-Meilensteine
# ---------------------------------------------------------------------------

class TestMilestoneDates:
    def test_first_date_set_for_issues_that_reached_first_stage(self, records, workflow):
        """Jedes Issue das die first_stage je erreicht hat, muss ein first_date haben."""
        for r in records:
            reached = any(t.label == workflow.first_stage for t in r.transitions[1:])
            if reached:
                assert r.first_date is not None, f"{r.key}: first_date fehlt"

    def test_first_date_not_before_created(self, records):
        for r in records:
            if r.first_date:
                assert r.first_date >= r.created, f"{r.key}: first_date vor created"

    def test_closed_date_not_before_created(self, records):
        for r in records:
            if r.closed_date:
                assert r.closed_date >= r.created, f"{r.key}: closed_date vor created"

    def test_known_issue_art_a_739_first_date(self, by_key):
        """ART_A-739: First Date muss der Analysis-Transition entsprechen."""
        r = by_key["ART_A-739"]
        assert r.first_date is not None
        # First Date liegt nach dem Erstellungszeitpunkt
        assert r.first_date > r.created
        # First Date liegt am 30.11.2025
        assert r.first_date.year == 2025
        assert r.first_date.month == 11
        assert r.first_date.day == 30


# ---------------------------------------------------------------------------
# Stage-Zeit-Berechnung
# ---------------------------------------------------------------------------

class TestStageMinutes:
    def test_no_negative_stage_minutes(self, records):
        for r in records:
            for stage, minutes in r.stage_minutes.items():
                assert minutes >= 0, f"{r.key}/{stage}: negative Minuten"

    def test_issues_with_transitions_have_nonzero_total(self, records):
        """Issues mit mindestens einer Transition müssen Gesamtzeit > 0 haben."""
        for r in records:
            if len(r.transitions) > 1:  # mehr als nur "Created"
                total = sum(r.stage_minutes.values())
                assert total > 0, f"{r.key}: Gesamtzeit = 0 obwohl Transitionen vorhanden"

    def test_known_issue_art_a_739_dominant_stage_is_analysis(self, by_key):
        """ART_A-739 verbringt die meiste Zeit in Analysis."""
        r = by_key["ART_A-739"]
        dominant = max(r.stage_minutes, key=r.stage_minutes.get)
        assert dominant == "Analysis"

    def test_known_issue_art_a_717_inprogress_date_set(self, by_key):
        """ART_A-717 hat eine Implementation-Transition → inprogress_date muss gesetzt sein."""
        r = by_key["ART_A-717"]
        assert r.inprogress_date is not None


# ---------------------------------------------------------------------------
# Unmapped Status
# ---------------------------------------------------------------------------

class TestUnmappedStatuses:
    def test_only_known_unmapped_status(self, unmapped):
        """Bei der original Workflow-Datei ist nur 'To Do' nicht gemappt."""
        assert unmapped == {"To Do"}


# ---------------------------------------------------------------------------
# CFD-Invarianten (über IssueRecord-Daten)
# ---------------------------------------------------------------------------

class TestCfdInvariants:
    def test_initial_stage_is_always_a_workflow_stage(self, records, workflow):
        """initial_stage muss immer eine bekannte Stage sein (nie None nach Fallback)."""
        for r in records:
            assert r.initial_stage in workflow.stages, (
                f"{r.key}: initial_stage='{r.initial_stage}' nicht in Workflow"
            )

    def test_created_date_not_in_future(self, records):
        cutoff = datetime(2026, 12, 31, tzinfo=timezone.utc)
        for r in records:
            assert r.created <= cutoff, f"{r.key}: created liegt in der Zukunft"
