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
#   CLI mit --example und Fehlerpfad; seit Schritt 2 auch der eingebettete
#   Block, --since/--delta und --narrate (Mock, Fehlpfad mit Rückgabewert 3).
# =============================================================================

from __future__ import annotations

from datetime import date
from html import escape

import pytest

from harmonisation.cli import main as cli_main
from harmonisation.examples import write_example
from harmonisation.model import LANGS, load_workspace
from harmonisation.render import _T, render_html, render_matrix_block


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


class TestBlock:
    def test_block_is_embeddable_and_scoped(self, ws) -> None:
        block = render_matrix_block(ws, "de", heading="Solution A")
        assert "<html" not in block and "<body" not in block
        assert block.startswith('<div class="harmo">') and "<h3>Solution A</h3>" in block
        assert ".harmo table{" in block and "\ntable{" not in block
        assert "67.6" in block and "standardisieren" in block
        assert "empfiehlt weder" in block                 # der Anspruch reist mit

    def test_no_heading_for_a_single_source(self, ws) -> None:
        assert "<h3>" not in render_matrix_block(ws, "en")


class TestCliStep2:
    def test_since_writes_the_delta_page(self, tmp_path, capsys) -> None:
        write_example(tmp_path)
        assert cli_main([str(tmp_path), "--since", "2026-09-20"]) == 0
        out = tmp_path / "delta.de.html"
        text = out.read_text(encoding="utf-8")
        assert "Veränderte Zellen" in text and "Bewertung vom 22.09.2026" in text
        assert "delta:" in capsys.readouterr().out

    def test_delta_against_a_second_folder(self, tmp_path) -> None:
        now, prev = tmp_path / "now", tmp_path / "prev"
        write_example(now)
        write_example(prev)
        for path in (prev / "assessments").glob("2026-09-2*.json"):
            path.unlink()
        assert cli_main([str(now), "--delta", str(prev), "--lang", "en"]) == 0
        text = (now / "delta.en.html").read_text(encoding="utf-8")
        assert "Changed cells" in text and "prev" in text

    def test_since_and_delta_exclude_each_other(self, tmp_path) -> None:
        write_example(tmp_path)
        with pytest.raises(SystemExit):
            cli_main([str(tmp_path), "--since", "2026-09-20", "--delta", str(tmp_path)])

    def test_bad_since_date_is_rejected(self, tmp_path) -> None:
        with pytest.raises(SystemExit):
            cli_main([str(tmp_path), "--since", "gestern"])

    def test_narrate_with_mock_adds_draft_and_evidence(self, tmp_path) -> None:
        write_example(tmp_path)
        assert cli_main([str(tmp_path), "--lang", "en", "--narrate", "mock"]) == 0
        page = (tmp_path / "matrix.en.html").read_text(encoding="utf-8")
        assert "AI reading (draft)" in page and "AI-drafted" in page
        assert (tmp_path / "matrix.en.reading.md").exists()
        assert (tmp_path / "llm_audit.jsonl").exists()

    def test_narrate_on_the_delta(self, tmp_path) -> None:
        write_example(tmp_path)
        rc = cli_main([str(tmp_path), "--since", "2026-09-20", "--narrate", "mock"])
        assert rc == 0
        page = (tmp_path / "delta.de.html").read_text(encoding="utf-8")
        assert "KI-Lesart (Entwurf)" in page
        assert page.index("KI-Lesart") > page.index("</table>")
        assert (tmp_path / "delta.de.reading.md").exists()

    def test_failed_ai_keeps_the_page_and_says_so(self, tmp_path, capsys) -> None:
        write_example(tmp_path)
        rc = cli_main([str(tmp_path), "--narrate", "no-such-provider"])
        assert rc == 3
        page = (tmp_path / "matrix.de.html").read_text(encoding="utf-8")
        assert "Entscheider-Matrix" in page and "KI-Lesart" not in page
        assert "AI reading skipped" in capsys.readouterr().out
        assert not (tmp_path / "matrix.de.reading.md").exists()
