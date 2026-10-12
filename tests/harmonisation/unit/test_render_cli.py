# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Tests für die Entscheider-Matrix (HTML) und die Kommandozeile: alle
#   fünf Sprachen, Legende vor der ersten Tabelle, Board-Spalten, zweite
#   Lesart mit Beleggrad, Datumsformat je Sprache, kein Urteil im Text,
#   CLI mit --example und Fehlerpfad.
# =============================================================================

from __future__ import annotations

from datetime import date
from html import escape

import pytest

from harmonisation.cli import main as cli_main
from harmonisation.examples import write_example
from harmonisation.model import LANGS, load_workspace
from harmonisation.render import _T, render_html


@pytest.fixture
def ws(tmp_path):
    write_example(tmp_path)
    return load_workspace(tmp_path)


class TestTranslations:
    def test_same_keys_in_all_languages(self) -> None:
        ref = set(_T["en"])
        for lang in LANGS:
            assert set(_T[lang]) == ref, lang
            assert all(_T[lang].values()), lang


class TestRender:
    @pytest.mark.parametrize("lang", LANGS)
    def test_renders_every_language(self, ws, lang: str) -> None:
        html = render_html(ws, lang, today=date(2026, 10, 12))
        assert f'<html lang="{lang}">' in html
        assert escape(_T[lang]["title"]) in html
        for p in ws.processes:
            assert escape(p.name) in html

    def test_legend_comes_before_the_first_table(self, ws) -> None:
        html = render_html(ws, "de")
        assert html.index('class="legend"') < html.index("<table>")

    def test_scores_and_board_columns(self, ws) -> None:
        html = render_html(ws, "de")
        assert "67.6" in html and "84.3" in html             # Median je Dimension, o2d
        assert "Spanne 21" in html                             # zwei Bewertungen
        assert "standardisieren" in html and "markenspezifisch" in html
        assert "Zustellfenster" in html                        # Tiefe im Wortlaut des Boards
        assert html.count("keine Bewertung") == 6              # p2p und h2r, je drei Zellen

    def test_second_reading_shows_evidence_and_unknown(self, ws) -> None:
        html = render_html(ws, "en")
        assert "Second reading" in html
        assert "hearsay" in html and "documented" in html and "unknown" in html

    def test_no_recommendation_anywhere(self, ws) -> None:
        html = render_html(ws, "de").lower()
        assert "empfiehlt weder" in html
        assert "empfehlung:" not in html

    def test_date_format_follows_language(self, ws) -> None:
        today = date(2026, 10, 12)
        assert "12.10.2026" in render_html(ws, "de", today)
        assert "2026-10-12" in render_html(ws, "en", today)
        assert "12/10/2026" in render_html(ws, "fr", today)

    def test_unknown_language_falls_back_to_english(self, ws) -> None:
        assert '<html lang="en">' in render_html(ws, "xx")

    def test_singular_for_one_assessment(self, ws) -> None:
        html = render_html(ws, "de")
        assert "1 Bewertung ·" in html and "1 Bewertungen" not in html


class TestCli:
    def test_example_then_report(self, tmp_path, capsys) -> None:
        rc = cli_main([str(tmp_path), "--example", "--lang", "en"])
        assert rc == 0
        out = tmp_path / "matrix.en.html"
        assert out.exists() and "decision matrix" in out.read_text(encoding="utf-8")
        assert "report:" in capsys.readouterr().out

    def test_explicit_output_and_language(self, tmp_path) -> None:
        write_example(tmp_path)
        target = tmp_path / "out" / "m.html"
        assert cli_main([str(tmp_path), "--output", str(target), "--lang", "fr"]) == 0
        assert "matrice de décision" in target.read_text(encoding="utf-8")

    def test_missing_workspace_is_a_clean_error(self, tmp_path, capsys) -> None:
        rc = cli_main([str(tmp_path / "nothing")])
        assert rc == 2
        assert "catalogue.json" in capsys.readouterr().err
