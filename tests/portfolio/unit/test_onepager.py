# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests des Lagevortrag-Einseiters (P6): fünf Sprachen mit gleichen
#   Schlüsseln, Aufbau aus dem Demo-Portfolio (vier Dimensionen × drei
#   Fragen, Konfidenz je Zelle, Entscheidungsbedarf ohne Empfehlung, BLUF
#   als Vorlagensatz), Spalte 2 nur mit Vergleichsstand, Kata-Modus leer,
#   Konfidenz-Regeln, Namensbegrenzung, kein Urteil im Text.
# =============================================================================

from __future__ import annotations

from datetime import date, timedelta

import pytest

from portfolio.onepager import (
    _T,
    CONF_NONE,
    DIMENSIONS,
    QUESTIONS,
    _age_conf,
    _names,
    build_onepager,
    render_onepager_html,
)
from portfolio.snapshot import load_snapshot
from portfolio.solution_config import load_solution_config
from portfolio.summary import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM

REF = date(2026, 10, 13)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    from testdata_generator.scenario import build_portfolio_scenario
    out = tmp_path_factory.mktemp("demo")
    paths = build_portfolio_scenario(out, seed=42, reference=REF, log=lambda m: None)
    return paths


@pytest.fixture(scope="module")
def onepager(demo):
    cfg = load_solution_config(demo["portfolio"])
    return build_onepager(cfg, "de", prev_snapshot=load_snapshot(demo["snapshot_prev"]),
                          reference=REF)


class TestTexts:
    def test_same_keys_in_all_languages(self) -> None:
        ref = set(_T["en"])
        for lang in ("de", "en", "ro", "pt", "fr"):
            assert set(_T[lang]) == ref, lang
            assert all(_T[lang].values()), lang

    def test_placeholders_match(self) -> None:
        import re
        for key in _T["en"]:
            ref = set(re.findall(r"{(\w+)", _T["en"][key]))
            for lang in ("de", "ro", "pt", "fr"):
                assert set(re.findall(r"{(\w+)", _T[lang][key])) == ref, (lang, key)


class TestBuild:
    def test_four_by_three_with_confidence_everywhere(self, onepager) -> None:
        assert tuple(onepager.cells) == DIMENSIONS
        for dim in DIMENSIONS:
            assert tuple(onepager.cells[dim]) == QUESTIONS
            for q in QUESTIONS:
                assert onepager.cells[dim][q].confidence in ("high", "medium", "low", CONF_NONE)

    def test_flow_cell_carries_the_numbers(self, onepager) -> None:
        q1 = onepager.cells["flow"]["q1"]
        assert q1.lines[0].endswith("offen (WIP)") and "Median-CT" in q1.lines[1]
        assert any("Flussprobleme" in line for line in q1.lines)
        assert q1.confidence != CONF_NONE

    def test_column_two_comes_from_the_delta(self, onepager) -> None:
        q2 = onepager.cells["flow"]["q2"]
        assert q2.lines and q2.lines[0].startswith("Durchsatz ")
        assert onepager.prev_as_of == REF - timedelta(days=14)

    def test_column_three_names_decision_points_only(self, onepager) -> None:
        decide = [line for dim in DIMENSIONS for line in onepager.cells[dim]["q3"].decide]
        assert decide, "the demo carries survived flow problems and a breached SLO"
        joined = " ".join(decide).lower()
        assert "flussprobleme ab der dritten konferenz" in joined
        assert "slo verletzt" in joined
        assert "empfehl" not in joined and "sollte" not in joined

    def test_bluf_is_a_single_sentence_from_the_data(self, onepager) -> None:
        assert onepager.bluf.endswith(".") and onepager.bluf.count(";") <= 1
        assert "überleben die dritte Konferenz" in onepager.bluf or "verletzt" in onepager.bluf

    def test_without_earlier_state_column_two_is_empty(self, demo) -> None:
        cfg = load_solution_config(demo["solution_alpha"])
        op = build_onepager(cfg, "en", reference=REF)
        assert op.prev_as_of is None
        assert all(not op.cells[dim]["q2"].lines for dim in DIMENSIONS)
        assert op.cells["dependencies"]["q1"].lines[0].startswith("cross-VS pressure")

    def test_sources_name_the_registers(self, onepager) -> None:
        assert any("IssueTimes" in s for s in onepager.sources)
        assert any(s.startswith("dependencies, risks: dependencies, risks") for s in onepager.sources)


class TestRender:
    @pytest.mark.parametrize("lang", ["de", "en", "ro", "pt", "fr"])
    def test_every_language_renders_a_four_row_table(self, onepager, lang) -> None:
        html = render_onepager_html(onepager, lang)
        assert f'<html lang="{lang}">' in html
        assert html.count('<td class="dim">') == 4
        assert _T[lang]["q1"] in html and _T[lang]["bluf"] in html
        assert "badge" in html

    def test_speaker_field_in_column_three(self, onepager) -> None:
        html = render_onepager_html(onepager, "de")
        assert html.count("Vortragende(r):") == 4
        assert "kein Vergleichsstand — Spalte leer" not in html

    def test_no_prev_says_so(self, demo) -> None:
        cfg = load_solution_config(demo["solution_beta"])
        html = render_onepager_html(build_onepager(cfg, "de", reference=REF), "de")
        assert html.count("kein Vergleichsstand — Spalte leer") == 4

    def test_kata_is_empty_but_structured(self, onepager) -> None:
        html = render_onepager_html(onepager, "de", kata=True)
        assert 'class="kata"' in html and "Übungsblatt" in html
        assert "Durchsatz" not in html and "Entscheidungsbedarf" not in html
        assert html.count('class="line"') == 4 * 3 * 4
        assert "30 Minuten" in html

    def test_no_judgement_words(self, onepager) -> None:
        html = render_onepager_html(onepager, "de").lower()
        assert "empfehlung:" not in html and "sollte" not in html

    def test_output_is_one_page_sized(self, onepager) -> None:
        html = render_onepager_html(onepager, "de")
        assert "@page{size:A4 landscape" in html


class TestHelpers:
    def test_age_confidence(self) -> None:
        today = date(2026, 10, 13)
        assert _age_conf([], today, present=False) == CONF_NONE
        assert _age_conf([], today, present=True) == CONFIDENCE_MEDIUM
        assert _age_conf([today - timedelta(days=5)], today, present=True) == CONFIDENCE_HIGH
        assert _age_conf([today - timedelta(days=45)], today, present=True) == CONFIDENCE_MEDIUM

    def test_names_are_capped(self) -> None:
        assert _names(["a", "b", "c", "d", "e"]) == "a, b, c (+2)"
        assert _names(["a"]) == "a"
