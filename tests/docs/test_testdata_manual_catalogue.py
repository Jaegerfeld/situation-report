# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       31.10.2026
# Geändert:       31.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Hält die fünf Textkataloge des Generator-Handbuchs in Deckung. Seit dem
#   Neuschnitt vom 31.10.2026 baut docs/generate_testdata_generator_manual.py
#   einen Aufbau aus fünf Katalogen (_M["de"|"en"|"ro"|"pt"|"fr"]); fehlt
#   ein Schlüssel in einer Sprache, bricht der PDF-Bau erst beim Rendern
#   dieser Sprache ab. Der Test prüft vorher: gleiche Schlüsselmengen, keine
#   leeren Texte, und jeder Aufbau lässt sich in jeder Sprache zusammensetzen
#   (reportlab parst die Absatz-Auszeichnung dabei mit — ein nicht
#   geschlossenes <b> fällt hier auf, nicht erst im PDF).
# =============================================================================

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "docs" / "generate_testdata_generator_manual.py"
LANGS = ("de", "en", "ro", "pt", "fr")


@pytest.fixture(scope="module")
def manual():
    pytest.importorskip("reportlab")
    sys.path.insert(0, str(ROOT / "docs"))
    try:
        spec = importlib.util.spec_from_file_location("tdg_manual_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ROOT / "docs"))
    return module


def test_catalogues_share_one_key_set(manual):
    assert set(manual._M) == set(LANGS)
    reference = set(manual._M["de"])
    for lang in LANGS:
        missing = reference - set(manual._M[lang])
        extra = set(manual._M[lang]) - reference
        assert not missing and not extra, f"{lang}: missing={sorted(missing)} extra={sorted(extra)}"


def test_no_empty_texts(manual):
    for lang in LANGS:
        empty = [k for k, v in manual._M[lang].items() if not str(v).strip()]
        assert not empty, f"{lang}: {empty}"


@pytest.mark.parametrize("lang", LANGS)
def test_content_builds_in_every_language(manual, lang):
    story = manual.build_content(manual.make_styles(), lang)
    assert len(story) > 100
    headings = [f.getPlainText() for f in story if f.__class__.__name__ == "Paragraph"
                and f.style.name == "TDG_H1"]
    assert len(headings) == 10, headings
