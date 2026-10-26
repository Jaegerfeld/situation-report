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
#   Beta Schnitt 1a): Rollenbindung an Positionen der Struktur, Hinweise
#   bei fehlenden Positionen, Standard-Geschichte, Roundtrip der story.json.
# =============================================================================

from __future__ import annotations

import pytest

from testdata_generator.story import (
    ROLE_BLOCKED_DEPENDENCY,
    ROLE_CROSS_SOLUTION_DEPENDENCY,
    ROLE_HOST_SOLUTION,
    ROLE_OUTLIER_ART,
    ROLE_RECURRING_SEAM,
    ROLE_SECOND_SOLUTION,
    ROLE_SLO_BREACH_SOLUTION,
    ROLE_WEAK_SOURCE_ART,
    TEMPLATE_STANDARD,
    WHEN_ALWAYS,
    WHEN_NOW,
    bind_roles,
    load_story,
    save_story,
    standard_story,
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


class TestBinding:
    def test_standard_binds_every_role_by_position(self) -> None:
        b = bind_roles(structure_template(STRUCTURE_STANDARD).portfolios[0])
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


class TestStandardStory:
    def test_standard_story_has_all_events_with_ids_and_tags(self) -> None:
        b = bind_roles(structure_template(STRUCTURE_STANDARD).portfolios[0])
        story = standard_story(b, {"Alpha": "A", "Beta": "B"})
        assert story.template == TEMPLATE_STANDARD
        assert [e.event_id for e in story.events] == ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]
        assert story.events[0].title.startswith("ART Alpha-3 ist der Ausreißer")
        assert "DP-A1" in story.events[0].effect
        assert "AS-B1" in story.events[1].effect
        assert story.events[2].when == WHEN_NOW
        assert story.events[0].when == WHEN_ALWAYS
        assert len(story.summary) == 3 and "Alpha-3" in story.summary[1]
        assert story.roles[ROLE_OUTLIER_ART] == "Alpha-3"

    def test_small_story_leaves_out_unbound_events(self) -> None:
        b = bind_roles(structure_template(TEMPLATE_SMALL).portfolios[0])
        story = standard_story(b, {"Alpha": "A"})
        ids = [e.event_id for e in story.events]
        assert "E1" in ids and "E3" in ids and "E5" in ids and "E7" in ids
        assert "E2" not in ids and "E4" not in ids and "E6" not in ids
        assert story.notices == b.notices and story.notices


class TestSerialisation:
    def test_roundtrip(self, tmp_path) -> None:
        b = bind_roles(structure_template(STRUCTURE_STANDARD).portfolios[0])
        story = standard_story(b, {"Alpha": "A", "Beta": "B"})
        path = tmp_path / "story.json"
        save_story(path, story)
        loaded = load_story(path)
        assert story_to_dict(loaded) == story_to_dict(story)

    def test_from_dict_rejects_unknown_template_role_and_when(self) -> None:
        with pytest.raises(ValueError, match="template 'calm' unknown"):
            story_from_dict({"template": "calm"})
        with pytest.raises(ValueError, match="role 'hero' unknown"):
            story_from_dict({"template": TEMPLATE_STANDARD,
                             "events": [{"id": "E1", "role": "hero"}]})
        with pytest.raises(ValueError, match="when 'later'"):
            story_from_dict({"template": TEMPLATE_STANDARD,
                             "events": [{"id": "E1", "role": ROLE_OUTLIER_ART,
                                         "when": "later"}]})
