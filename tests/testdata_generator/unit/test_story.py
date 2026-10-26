# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       26.10.2026
# Geändert:       26.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die Geschichte als Daten (testdata_generator/story.py,
#   Beta Schnitt 1a + 2): Rollenbindung an Positionen der Struktur,
#   Hinweise bei fehlenden Positionen, die vier Vorlagen mit Stand-Fenstern,
#   Ereignis-Schalter samt Abhängigkeits-Hinweis, Phasenauflösung,
#   Roundtrip der story.json (Schema 2) und Lesen von Schema-1-Dateien.
# =============================================================================

from __future__ import annotations

import pytest

from testdata_generator.story import (
    ALL_EVENTS,
    EVENT_BLOCKED,
    EVENT_CROSS_SOLUTION,
    EVENT_HOST_PATTERNS,
    EVENT_IDS,
    EVENT_NEW_RISK,
    EVENT_OUTLIER,
    EVENT_ROADMAPS,
    EVENT_SEAM,
    EVENT_SLO_BREACH,
    EVENT_WEAK_DECAY,
    EVENT_WEAK_SOURCE,
    PHASE_EARLY,
    PHASE_END,
    PHASE_LATE,
    PHASE_MID,
    PHASE_START,
    ROLE_BLOCKED_DEPENDENCY,
    ROLE_CROSS_SOLUTION_DEPENDENCY,
    ROLE_HOST_SOLUTION,
    ROLE_OUTLIER_ART,
    ROLE_RECURRING_SEAM,
    ROLE_SECOND_SOLUTION,
    ROLE_SLO_BREACH_SOLUTION,
    ROLE_WEAK_SOURCE_ART,
    STORY_TEMPLATES,
    SUGGESTED_STANDS,
    TEMPLATE_CALM,
    TEMPLATE_ESCALATION,
    TEMPLATE_RECOVERY,
    TEMPLATE_STANDARD,
    bind_roles,
    load_story,
    parse_switches,
    save_story,
    stand_for_phase,
    standard_story,
    story_for,
    story_from_dict,
    story_to_dict,
)
from testdata_generator.structure import (
    TEMPLATE_SMALL,
    structure_from_arts_spec,
    structure_template,
)
from testdata_generator.structure import (
    TEMPLATE_STANDARD as STRUCTURE_STANDARD,
)

TAGS = {"Alpha": "A", "Beta": "B"}


def _standard_binding():
    return bind_roles(structure_template(STRUCTURE_STANDARD).portfolios[0])


class TestBinding:
    def test_standard_binds_every_role_by_position(self) -> None:
        b = _standard_binding()
        assert b.get(ROLE_HOST_SOLUTION) == "Alpha"
        assert b.get(ROLE_SECOND_SOLUTION) == "Beta"
        assert b.art(ROLE_OUTLIER_ART) == "Alpha-3"
        assert b.art(ROLE_WEAK_SOURCE_ART) == "Beta-3"
        assert b.pair(ROLE_BLOCKED_DEPENDENCY) == ("Alpha-1", "Alpha-3")
        assert b.pair(ROLE_RECURRING_SEAM) == ("Alpha-1", "Alpha-3")
        assert b.pair(ROLE_CROSS_SOLUTION_DEPENDENCY) == ("Beta-1", "Alpha-1")
        assert b.get(ROLE_SLO_BREACH_SOLUTION) == "Beta"
        assert b.notices == []

    def test_renaming_does_not_move_the_roles(self) -> None:
        p = structure_template(STRUCTURE_STANDARD).portfolios[0]
        p.solutions[0].name = "Nord"
        p.solutions[0].arts = ["Nord-A", "Nord-B", "Nord-C"]
        b = bind_roles(p)
        assert b.art(ROLE_OUTLIER_ART) == "Nord-C"
        assert b.pair(ROLE_CROSS_SOLUTION_DEPENDENCY) == ("Beta-1", "Nord-A")

    def test_single_solution_drops_cross_solution_roles_with_notice(self) -> None:
        b = bind_roles(structure_template(TEMPLATE_SMALL).portfolios[0])
        assert b.art(ROLE_OUTLIER_ART) == "Alpha-2"
        assert not b.has(ROLE_WEAK_SOURCE_ART)
        assert not b.has(ROLE_CROSS_SOLUTION_DEPENDENCY)
        assert not b.has(ROLE_SLO_BREACH_SOLUTION)
        assert any("Nur eine Solution" in n for n in b.notices)

    def test_one_art_host_has_no_outlier(self) -> None:
        b = bind_roles(structure_from_arts_spec("1,2").portfolios[0])
        assert not b.has(ROLE_OUTLIER_ART)
        assert not b.has(ROLE_BLOCKED_DEPENDENCY)
        assert b.art(ROLE_WEAK_SOURCE_ART) == "Beta-2"
        assert any("nur einen ART" in n for n in b.notices)

    def test_one_art_second_solution_is_weak_source_and_seam_partner(self) -> None:
        b = bind_roles(structure_from_arts_spec("3,1").portfolios[0])
        assert b.art(ROLE_WEAK_SOURCE_ART) == "Beta-1"
        assert b.pair(ROLE_CROSS_SOLUTION_DEPENDENCY) == ("Beta-1", "Alpha-1")
        assert any("zugleich" in n for n in b.notices)

    def test_third_and_further_solutions_are_named_as_anchor_free(self) -> None:
        b = bind_roles(structure_from_arts_spec("3,4s,1,2").portfolios[0])
        assert any("Solution Gamma" in n and "Solution Delta" in n
                   for n in b.notices)


class TestPhases:
    @pytest.mark.parametrize("stands,expected", [
        (2, {PHASE_START: 1, PHASE_EARLY: 1, PHASE_MID: 2, PHASE_LATE: 2, PHASE_END: 2}),
        (3, {PHASE_START: 1, PHASE_EARLY: 2, PHASE_MID: 2, PHASE_LATE: 3, PHASE_END: 3}),
        (6, {PHASE_START: 1, PHASE_EARLY: 2, PHASE_MID: 4, PHASE_LATE: 5, PHASE_END: 6}),
        (12, {PHASE_START: 1, PHASE_EARLY: 4, PHASE_MID: 7, PHASE_LATE: 9, PHASE_END: 12}),
    ])
    def test_phase_to_stand(self, stands: int, expected: dict) -> None:
        assert {p: stand_for_phase(p, stands) for p in expected} == expected

    def test_unknown_phase(self) -> None:
        with pytest.raises(ValueError, match="Unknown phase"):
            stand_for_phase("later", 6)


class TestTemplates:
    def test_every_template_builds_for_the_standard_structure(self) -> None:
        for template in STORY_TEMPLATES:
            story = story_for(template, _standard_binding(), TAGS, stands=6)
            assert story.template == template and story.stands == 6
            assert [e.event_id for e in story.events] == list(EVENT_IDS)
            assert len(story.summary) == 3
            assert SUGGESTED_STANDS[template] in (3, 6)

    def test_standard_switches_turning_points_on_with_the_last_stand(self) -> None:
        story = story_for(TEMPLATE_STANDARD, _standard_binding(), TAGS, stands=6)
        start = {EVENT_OUTLIER, EVENT_WEAK_SOURCE, EVENT_SLO_BREACH, EVENT_HOST_PATTERNS}
        for k in range(1, 6):
            assert story.active_events(k) == start
        assert story.active_events(6) == ALL_EVENTS
        assert "DP-A1" in story.events[0].effect and "AS-B1" in story.events[1].effect

    def test_calm_has_everything_off(self) -> None:
        story = story_for(TEMPLATE_CALM, _standard_binding(), TAGS, stands=3)
        assert all(not e.enabled for e in story.events)
        assert story.active_events(1) == frozenset() == story.active_events(3)
        assert story.title == "Ruhig"

    def test_escalation_adds_pressure_stand_by_stand(self) -> None:
        story = story_for(TEMPLATE_ESCALATION, _standard_binding(), TAGS, stands=6)
        sets = [story.active_events(k) for k in range(1, 7)]
        assert sets[0] == {EVENT_OUTLIER, EVENT_WEAK_SOURCE, EVENT_HOST_PATTERNS}
        assert EVENT_SLO_BREACH in sets[1] and EVENT_SLO_BREACH not in sets[0]
        assert EVENT_BLOCKED in sets[3] and EVENT_BLOCKED not in sets[2]
        assert {EVENT_WEAK_DECAY, EVENT_CROSS_SOLUTION, EVENT_SEAM} <= sets[4]
        assert not {EVENT_WEAK_DECAY, EVENT_CROSS_SOLUTION, EVENT_SEAM} & sets[3]
        assert sets[5] == ALL_EVENTS
        assert all(a <= b for a, b in zip(sets, sets[1:]))   # never loses pressure

    def test_recovery_heals_over_the_series(self) -> None:
        story = story_for(TEMPLATE_RECOVERY, _standard_binding(), TAGS, stands=6)
        first, last = story.active_events(1), story.active_events(6)
        assert {EVENT_OUTLIER, EVENT_WEAK_SOURCE, EVENT_BLOCKED, EVENT_CROSS_SOLUTION,
                EVENT_SEAM, EVENT_SLO_BREACH, EVENT_HOST_PATTERNS} == first
        assert last == {EVENT_HOST_PATTERNS}
        assert EVENT_SEAM not in story.active_events(2)             # start only
        assert EVENT_BLOCKED in story.active_events(2) and EVENT_BLOCKED not in story.active_events(3)
        assert EVENT_OUTLIER in story.active_events(4) and EVENT_OUTLIER not in story.active_events(5)
        assert EVENT_WEAK_SOURCE in story.active_events(5) and EVENT_WEAK_SOURCE not in last
        assert not any(e.enabled for e in story.events
                       if e.event_id in (EVENT_WEAK_DECAY, EVENT_NEW_RISK, EVENT_ROADMAPS))

    def test_unknown_template(self) -> None:
        with pytest.raises(ValueError, match="Unknown story template"):
            story_for("drama", _standard_binding(), TAGS)

    def test_small_structure_leaves_out_unbound_events(self) -> None:
        b = bind_roles(structure_template(TEMPLATE_SMALL).portfolios[0])
        story = story_for(TEMPLATE_STANDARD, b, {"Alpha": "A"}, stands=6)
        ids = {e.event_id for e in story.events}
        assert {EVENT_OUTLIER, EVENT_BLOCKED, EVENT_SEAM, EVENT_HOST_PATTERNS, EVENT_ROADMAPS} <= ids
        assert not {EVENT_WEAK_SOURCE, EVENT_CROSS_SOLUTION, EVENT_SLO_BREACH,
                    EVENT_WEAK_DECAY, EVENT_NEW_RISK} & ids
        assert story.notices and story.notices[0] in b.notices

    def test_standard_story_wrapper(self) -> None:
        story = standard_story(_standard_binding(), TAGS, stands=2)
        assert story.template == TEMPLATE_STANDARD
        assert story.active_events(1) < story.active_events(2) == ALL_EVENTS


class TestSwitches:
    def test_parse_switches(self) -> None:
        assert parse_switches(["E3=off", "e9=ON", "E1=1"]) == {"E3": False, "E9": True, "E1": True}
        assert parse_switches(None) == {}

    @pytest.mark.parametrize("bad", ["E3", "E99=on", "E3=maybe"])
    def test_parse_switches_rejects(self, bad: str) -> None:
        with pytest.raises(ValueError, match="event switch"):
            parse_switches([bad])

    def test_switch_overrides_the_template(self) -> None:
        story = story_for(TEMPLATE_STANDARD, _standard_binding(), TAGS, stands=6,
                          switches={EVENT_BLOCKED: False, EVENT_NEW_RISK: False})
        assert EVENT_BLOCKED not in story.active_events(6)
        assert EVENT_NEW_RISK not in story.active_events(6)
        calm_plus = story_for(TEMPLATE_CALM, _standard_binding(), TAGS, stands=3,
                              switches={EVENT_SLO_BREACH: True})
        assert calm_plus.active_events(1) == {EVENT_SLO_BREACH}

    def test_decay_without_weak_source_stays_off_with_notice(self) -> None:
        story = story_for(TEMPLATE_STANDARD, _standard_binding(), TAGS, stands=6,
                          switches={EVENT_WEAK_SOURCE: False})
        decay = next(e for e in story.events if e.event_id == EVENT_WEAK_DECAY)
        assert not decay.enabled
        assert any("E8 braucht E2" in n for n in story.notices)
        assert EVENT_WEAK_DECAY not in story.active_events(6)

    def test_switch_for_an_event_the_structure_cannot_host_is_noted(self) -> None:
        b = bind_roles(structure_template(TEMPLATE_SMALL).portfolios[0])
        story = story_for(TEMPLATE_STANDARD, b, {"Alpha": "A"}, switches={EVENT_SLO_BREACH: True})
        assert any("Schalter ohne Ereignis" in n and "E6" in n for n in story.notices)


class TestSerialisation:
    def test_roundtrip(self, tmp_path) -> None:
        story = story_for(TEMPLATE_ESCALATION, _standard_binding(), TAGS, stands=6,
                          switches={EVENT_SEAM: False})
        path = tmp_path / "story.json"
        save_story(path, story)
        loaded = load_story(path)
        assert story_to_dict(loaded) == story_to_dict(story)
        assert loaded.active_events(5) == story.active_events(5)
        data = story_to_dict(story)
        assert data["schema"] == 2 and data["events"][2]["enabled"] is True
        assert data["events"][4] == {**data["events"][4], "id": "E5", "enabled": False}

    def test_schema_one_file_is_still_readable(self) -> None:
        story = story_from_dict({"schema": 1, "template": TEMPLATE_STANDARD, "events": [
            {"id": "E1", "role": ROLE_OUTLIER_ART, "when": "always", "title": "t"},
            {"id": "E3", "role": ROLE_BLOCKED_DEPENDENCY, "when": "now", "title": "t"}]})
        assert story.active_events(1) == {"E1"}
        assert story.active_events(6) == {"E1", "E3"}

    def test_from_dict_rejects_unknown_template_role_phase_and_when(self) -> None:
        with pytest.raises(ValueError, match="template 'drama' unknown"):
            story_from_dict({"template": "drama"})
        with pytest.raises(ValueError, match="role 'hero' unknown"):
            story_from_dict({"template": TEMPLATE_STANDARD,
                             "events": [{"id": "E1", "role": "hero"}]})
        with pytest.raises(ValueError, match="phase 'soon' unknown"):
            story_from_dict({"template": TEMPLATE_STANDARD,
                             "events": [{"id": "E1", "role": ROLE_OUTLIER_ART, "onset": "soon"}]})
        with pytest.raises(ValueError, match="when 'later'"):
            story_from_dict({"template": TEMPLATE_STANDARD,
                             "events": [{"id": "E1", "role": ROLE_OUTLIER_ART, "when": "later"}]})
