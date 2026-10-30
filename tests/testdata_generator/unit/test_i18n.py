# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Mehrsprachigkeit des Testdaten-Generators (Beta, 30.10.2026): die drei
#   Textkataloge (Datenraum-Texte `i18n`, Oberflächentexte `web/texts`,
#   altes ART-Fenster `gui._T`) tragen jeden Schlüssel in allen fünf
#   Sprachen mit denselben Platzhaltern; `t()` fällt auf Englisch zurück;
#   Geschichte, README, Protokoll, Schritte und KI-Übungstexte folgen `lang`;
#   die Sprachvorgabe kommt aus der Suite-Einstellung.
# =============================================================================

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from build_reports.chart_texts import LANGUAGES
from testdata_generator import i18n
from testdata_generator.ai_drafts import questions
from testdata_generator.dataspace import STEP_IDS, STEPS
from testdata_generator.scenario import _readme_text
from testdata_generator.story import TEMPLATE_TITLES, bind_roles, story_for, template_title
from testdata_generator.structure import structure_template
from testdata_generator.web.texts import LANGUAGE_NAMES, MANUALS, TEXTS, texts_for

_PH = re.compile(r"\{(\w+)(?::[^}]*)?\}")


def _placeholders(text: str) -> set[str]:
    return set(_PH.findall(text))


class TestCatalogues:
    def test_every_data_room_key_has_five_languages_and_equal_placeholders(self) -> None:
        for key in i18n.keys():
            entry = i18n._T[key]
            assert set(entry) == set(LANGUAGES), key
            ref = _placeholders(entry["en"])
            for lang, text in entry.items():
                assert _placeholders(text) == ref, (key, lang)
                assert text.strip(), (key, lang)

    def test_web_texts_cover_five_languages_with_the_same_keys(self) -> None:
        assert set(TEXTS) == set(LANGUAGES)
        keys = set(TEXTS["en"])
        for lang, block in TEXTS.items():
            assert set(block) == keys, lang
            for key, text in block.items():
                assert _placeholders(text) == _placeholders(TEXTS["en"][key]), (key, lang)
        assert set(MANUALS) == set(LANGUAGE_NAMES) == set(LANGUAGES)
        assert texts_for("fr")["app"] == TEXTS["fr"]["app"]
        assert texts_for("xx") is TEXTS["en"] and texts_for(None) is TEXTS["en"]

    def test_old_window_texts_cover_five_languages(self) -> None:
        from testdata_generator.gui import _T as window_texts
        assert set(window_texts) == set(LANGUAGES)
        keys = set(window_texts["en"])
        for lang, block in window_texts.items():
            assert set(block) == keys, lang
            for key, text in block.items():
                assert text.count("{}") == window_texts["en"][key].count("{}"), (key, lang)

    def test_t_formats_and_falls_back_to_english(self) -> None:
        assert i18n.t("tpl.calm", "de") == "Ruhig"
        assert i18n.t("tpl.calm", "xx") == i18n.t("tpl.calm", "en") == "Calm"
        assert i18n.t("det.stands_running", "pt", n=3) == "3 estados"
        with pytest.raises(KeyError):
            i18n.t("no.such.key", "en")
        assert i18n.normalise("ro") == "ro" and i18n.normalise(None) == "en"
        assert template_title("recovery", "fr") == "Reprise"
        assert TEMPLATE_TITLES == {t: template_title(t) for t in TEMPLATE_TITLES}
        assert i18n.step_label("stands", "ro") == "Seria de stări" and i18n.step_label("odd") == "odd"
        assert [s for s, _l in STEPS] == list(STEP_IDS)

    def test_language_preference_comes_from_the_suite_file(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(i18n, "_PREFS_PATH", tmp_path / ".situation_report" / "prefs.json")
        assert i18n.load_lang_pref() == "en"
        (tmp_path / ".situation_report").mkdir()
        (tmp_path / ".situation_report" / "prefs.json").write_text(json.dumps({"lang": "pt"}), encoding="utf-8")
        assert i18n.load_lang_pref() == "pt"
        (tmp_path / ".situation_report" / "prefs.json").write_text(json.dumps({"lang": "xx"}), encoding="utf-8")
        assert i18n.load_lang_pref() == "en"
        (tmp_path / ".situation_report" / "prefs.json").write_text("{broken", encoding="utf-8")
        assert i18n.load_lang_pref("de") == "de"


class TestStoryAndReadmeFollowLang:
    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_story_texts_are_in_the_requested_language(self, lang) -> None:
        portfolio = structure_template("standard").portfolios[0]
        story = story_for("escalation", bind_roles(portfolio, lang), stands=6, lang=lang)
        assert story.title == template_title("escalation", lang)
        e1 = next(e for e in story.events if e.event_id == "E1")
        assert e1.title == i18n.t("ev.E1.title", lang, art="ART Alpha-3")
        assert "Alpha-3" in e1.title and "A" in e1.effect
        assert story.summary == [
            i18n.t("sum.escalation.1", lang),
            i18n.t("sum.escalation.2", lang,
                   blocks=i18n.t("sum.part.blocks_outlier", lang, outlier="Alpha-3"),
                   decay=i18n.t("sum.part.decay_weak", lang, weak="Beta-3")),
            i18n.t("sum.escalation.3", lang)]

    def test_notices_follow_lang(self) -> None:
        small = structure_template("small").portfolios[0]
        assert bind_roles(small, "de").notices == [i18n.t("notice.one_solution", "de")]
        assert bind_roles(small).notices == ["Only one solution — no weak source, no SLO breach in a second "
                                             "solution, no cross-solution dependency."]
        one_art = structure_template("standard").portfolios[0]
        one_art.solutions[0].arts = one_art.solutions[0].arts[:1]
        assert bind_roles(one_art, "pt").notices == [
            i18n.t("notice.one_art_host", "pt", solution=one_art.solutions[0].display_name)]
        story = story_for("calm", bind_roles(small, "fr"), stands=3, switches={"E6": True}, lang="fr")
        assert any(n.startswith("Interrupteurs sans") and "E6" in n for n in story.notices)

    def test_estimate_warning_follows_lang(self) -> None:
        from testdata_generator.structure import estimate
        est = estimate(structure_template("large"), stands=6, scale="l")
        assert est.warn and est.warn_arts == 49 and est.warn_portfolios == 5
        assert est.warn_reason == est.warn_text("en") == est.warn_text("xx")
        assert est.warn_text("de") == "49 ARTs (ab 30 dauert die Erzeugung spürbar); 5 Portfolios bei Umfang L"
        assert not estimate(structure_template("small")).warn

    def test_readme_is_english_by_default_and_german_on_request(self) -> None:
        portfolio = structure_template("standard").portfolios[0]
        dates = [date(2025, 6, 2), date(2025, 6, 16), date(2025, 6, 30)]
        en = _readme_text(portfolio, story_for("recovery", bind_roles(portfolio), stands=3), 7,
                          dates[-1], "s", dates)
        assert "## Structure" in en and "## Story \"Recovery\"" in en and "## Stands" in en
        assert "stands 01 to 02" in en or "stand 01" in en
        assert "Stände" not in en and "Geschichte" not in en
        de = _readme_text(portfolio, story_for("recovery", bind_roles(portfolio, "de"), stands=3, lang="de"),
                          7, dates[-1], "s", dates, lang="de")
        assert "## Struktur" in de and "## Geschichte „Erholung“" in de and "## Stände" in de
        ro = _readme_text(portfolio, story_for("calm", bind_roles(portfolio, "ro"), stands=3, lang="ro"),
                          7, dates[-1], "s", dates, lang="ro")
        assert "## Structură" in ro and "_(oprit)_" in ro

    def test_questions_exist_in_all_languages(self) -> None:
        seen = {tuple(questions(lang)) for lang in LANGUAGES}
        assert len(seen) == 5 and all(len(q) == 3 for q in seen)
