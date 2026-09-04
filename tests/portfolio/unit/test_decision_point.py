# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       05.09.2026
# Geändert:       05.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Entscheidungspunkt-Weckers (P4): die Einordnung einer
#   Abhängigkeit an der Naht zwischen Value Streams, die Druckformel
#   (Status × Überfälligkeit) und vor allem die drei Regeln, die den Wecker
#   leise halten — extern weckt nicht, ohne vereinbarte Schwelle gibt es
#   keinen Alarm, und Unterschwelligkeit wird ausgesprochen statt
#   weggelassen.
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

from portfolio.decision_point import (
    SCOPE_CROSS_VS,
    SCOPE_EXTERNAL,
    SCOPE_INTERNAL,
    classify,
    compute_pressure,
    overdue_factor,
    render_decision_point_html,
)
from portfolio.dependency_config import (
    DEP_AT_RISK,
    DEP_BLOCKED,
    DEP_DONE,
    DEP_ON_TRACK,
    Dependency,
)

REF = date(2026, 9, 5)

ARTS = {
    "Solution Alpha": {"ART Alpha-1", "ART Alpha-2"},
    "Solution Beta": {"ART Beta-1", "ART Beta-2"},
}


def _dep(dep_id: str, to_art: str, status: str = DEP_AT_RISK,
         due_offset: int | None = None) -> Dependency:
    return Dependency(
        dep_id=dep_id, title=f"Dependency {dep_id}", from_art="ART Alpha-1",
        to_art=to_art, status=status,
        due=None if due_offset is None else REF + timedelta(days=due_offset))


class TestClassify:
    """Die Naht wird aus der Konfiguration ABGELEITET, nie im Register
    behauptet — dieselbe Regel wie das Cross-VS-Flag aus B6."""

    def test_own_solution_is_internal(self) -> None:
        scope, target = classify(
            "Solution Alpha", _dep("D1", "ART Alpha-2"), ARTS)
        assert scope == SCOPE_INTERNAL
        assert target == "Solution Alpha"

    def test_sibling_solution_is_cross_value_stream(self) -> None:
        scope, target = classify(
            "Solution Alpha", _dep("D2", "ART Beta-1"), ARTS)
        assert scope == SCOPE_CROSS_VS
        assert target == "Solution Beta"

    def test_unknown_target_leaves_the_portfolio(self) -> None:
        scope, target = classify(
            "Solution Alpha", _dep("D3", "Platform Services"), ARTS)
        assert scope == SCOPE_EXTERNAL
        assert target == ""


class TestWeighting:
    """Ganzzahlige Stufen, damit ein Mensch den Wert nachrechnen kann."""

    def test_overdue_factor_steps(self) -> None:
        assert overdue_factor(0) == 1
        assert overdue_factor(1) == 2
        assert overdue_factor(29) == 2
        assert overdue_factor(30) == 3

    def test_status_and_overdue_multiply(self) -> None:
        entries = [
            # blocked (3) x mehr als ein Monat ueberfaellig (3) = 9
            ("Solution Alpha", _dep("D1", "ART Beta-1", DEP_BLOCKED, -40)),
            # at_risk (2) x ueberfaellig (2) = 4
            ("Solution Alpha", _dep("D2", "ART Beta-1", DEP_AT_RISK, -5)),
            # on_track (1) x puenktlich (1) = 1
            ("Solution Alpha", _dep("D3", "ART Beta-2", DEP_ON_TRACK, 20)),
        ]
        pressure = compute_pressure(entries, ARTS, reference=REF)
        assert pressure.value == 14
        assert [i.weight for i in pressure.items] == [9, 4, 1]

    def test_heaviest_contributor_comes_first(self) -> None:
        entries = [
            ("Solution Alpha", _dep("D-light", "ART Beta-1", DEP_ON_TRACK, 10)),
            ("Solution Alpha", _dep("D-heavy", "ART Beta-1", DEP_BLOCKED, -60)),
        ]
        pressure = compute_pressure(entries, ARTS, reference=REF)
        assert [i.dependency.dep_id for i in pressure.items] == \
            ["D-heavy", "D-light"]


class TestWhatDoesNotWakeAnyone:
    """Die drei Regeln gegen Alarm-Müdigkeit."""

    def test_external_targets_are_counted_but_never_weigh_in(self) -> None:
        """Eine Abhängigkeit zum Lieferanten ist realer Druck — aber keine
        Konferenz DIESER Value Streams kann darüber entscheiden."""
        entries = [
            ("Solution Alpha", _dep("EXT", "Platform Services", DEP_BLOCKED, -90)),
        ]
        pressure = compute_pressure(entries, ARTS, threshold=1, reference=REF)
        assert pressure.value == 0
        assert pressure.external_open == 1
        assert pressure.triggered is False

    def test_internal_dependencies_do_not_weigh_in(self) -> None:
        entries = [
            ("Solution Alpha", _dep("INT", "ART Alpha-2", DEP_BLOCKED, -90)),
        ]
        assert compute_pressure(entries, ARTS, reference=REF).value == 0

    def test_done_dependencies_exert_no_pressure(self) -> None:
        entries = [
            ("Solution Alpha", _dep("D1", "ART Beta-1", DEP_DONE, -90)),
        ]
        pressure = compute_pressure(entries, ARTS, reference=REF)
        assert pressure.value == 0
        assert pressure.external_open == 0

    def test_without_an_agreed_threshold_nothing_ever_triggers(self) -> None:
        """Das Werkzeug erfindet keinen Schwellenwert — die Schwelle gehört
        ins Ritual."""
        entries = [
            ("Solution Alpha", _dep("D1", "ART Beta-1", DEP_BLOCKED, -90)),
        ]
        pressure = compute_pressure(entries, ARTS, threshold=None, reference=REF)
        assert pressure.value == 9
        assert pressure.triggered is False

    def test_single_solution_is_not_applicable_rather_than_zero(self) -> None:
        """Ohne Nachbar-Solution gibt es keine Naht — eine beruhigende Null
        wäre eine Falschaussage."""
        entries = [("Solution Alpha", _dep("D1", "Elsewhere", DEP_BLOCKED, -90))]
        pressure = compute_pressure(
            entries, {"Solution Alpha": {"ART Alpha-1"}}, threshold=1,
            reference=REF)
        assert pressure.applicable is False
        assert pressure.triggered is False


class TestTriggering:
    def test_reaching_the_threshold_triggers(self) -> None:
        entries = [("Solution Alpha", _dep("D1", "ART Beta-1", DEP_AT_RISK, 5))]
        assert compute_pressure(
            entries, ARTS, threshold=2, reference=REF).triggered is True

    def test_staying_below_does_not(self) -> None:
        entries = [("Solution Alpha", _dep("D1", "ART Beta-1", DEP_AT_RISK, 5))]
        assert compute_pressure(
            entries, ARTS, threshold=3, reference=REF).triggered is False


class TestRendering:
    """Stille ist Information: jeder Zustand wird ausgesprochen."""

    def _html(self, threshold, status=DEP_AT_RISK, due=5, arts=ARTS):
        entries = [("Solution Alpha", _dep("D1", "ART Beta-1", status, due))]
        return render_decision_point_html(
            compute_pressure(entries, arts, threshold=threshold, reference=REF))

    def test_triggered_asks_the_question(self) -> None:
        html = self._html(threshold=2)
        assert "threshold reached" in html
        assert "Convene a Value Stream Conference?" in html

    def test_below_threshold_is_stated_out_loud(self) -> None:
        html = self._html(threshold=99)
        assert "below threshold" in html
        assert "Pressure 2 of 99" in html

    def test_missing_threshold_says_so(self) -> None:
        html = self._html(threshold=None)
        assert "No threshold agreed yet" in html

    def test_not_applicable_says_so(self) -> None:
        html = self._html(threshold=2, arts={"Solution Alpha": {"ART Alpha-1"}})
        assert "single solution" in html

    def test_contributors_are_listed_with_their_weight(self) -> None:
        html = self._html(threshold=2)
        assert "D1" in html
        assert "Solution Beta · ART Beta-1" in html

    def test_external_note_explains_the_exclusion(self) -> None:
        entries = [
            ("Solution Alpha", _dep("D1", "ART Beta-1", DEP_AT_RISK, 5)),
            ("Solution Alpha", _dep("EXT", "Vendor X", DEP_BLOCKED, -10)),
        ]
        html = render_decision_point_html(
            compute_pressure(entries, ARTS, threshold=2, reference=REF))
        assert "outside the portfolio" in html
        assert "excluded from the indicator" in html
