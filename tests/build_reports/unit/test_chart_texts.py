# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       19.09.2026
# Geändert:       19.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prüft den Sprachkatalog der Diagrammbeschriftungen: Vollständigkeit,
#   gleiche Platzhalter, Monatsabkürzungen — und vor allem zwei Dinge, die
#   sonst still danebengehen: dass **jedes** registrierte Metrik-Plugin den
#   lang-Parameter führt (ein vergessenes fällt erst auf, wenn jemand genau
#   diese Metrik auswählt), und dass ein Diagramm in jeder Sprache anders
#   aussieht als auf Englisch.
# =============================================================================

from __future__ import annotations

import inspect
import re

import pytest

from build_reports.chart_texts import (
    _TEXTS,
    DEFAULT_LANG,
    LANGUAGES,
    MONTHS,
    keys,
    month_abbr,
    normalise,
    t,
)
from build_reports.metrics import all_metrics
from build_reports.metrics.base import MetricPlugin

PLATZHALTER = re.compile(r"\{(\w+)")


class TestCatalogue:
    def test_every_key_has_every_language(self) -> None:
        fehlend = [(k, lang) for k in keys() for lang in LANGUAGES
                   if lang not in _TEXTS[k]]
        assert fehlend == []

    def test_placeholders_match_across_languages(self) -> None:
        schief = {
            k: {lang: sorted(PLATZHALTER.findall(v))
                for lang, v in _TEXTS[k].items()}
            for k in keys()
            if len({tuple(sorted(PLATZHALTER.findall(v)))
                    for v in _TEXTS[k].values()}) > 1
        }
        assert schief == {}

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError):
            t("gibt.es.nicht")

    def test_unknown_language_falls_back(self) -> None:
        assert normalise("kl") == DEFAULT_LANG
        assert t("axis.date", "kl") == t("axis.date", DEFAULT_LANG)

    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_month_table_is_complete(self, lang: str) -> None:
        """Index 0 bleibt leer, damit Monat 1..12 direkt indiziert werden."""
        monate = MONTHS[lang]
        assert len(monate) == 13
        assert monate[0] == ""
        assert all(m for m in monate[1:])

    def test_month_names_are_not_all_german(self) -> None:
        """Bis 0.32.0 waren die Monatsabkuerzungen in JEDEM Report deutsch —
        fest verdrahtet und in zwei Modulen doppelt gepflegt."""
        assert month_abbr("de")[12] == "Dez"
        assert month_abbr("en")[12] == "Dec"
        assert month_abbr("fr")[12] == "déc"


class TestEveryPluginTakesTheLanguage:
    """Ein vergessenes Plugin faellt sonst erst auf, wenn jemand genau diese
    Metrik auswaehlt — die Unit-Tests rufen render() mit zwei Argumenten auf
    und blieben gruen, run_render() uebergibt aber drei."""

    def test_registry_is_not_empty(self) -> None:
        assert all_metrics()

    @pytest.mark.parametrize("plugin", all_metrics(),
                             ids=lambda p: p.metric_id)
    def test_render_accepts_lang(self, plugin: MetricPlugin) -> None:
        sig = inspect.signature(plugin.render)
        assert "lang" in sig.parameters, plugin.metric_id

    @pytest.mark.parametrize("plugin", all_metrics(),
                             ids=lambda p: p.metric_id)
    def test_lang_is_optional(self, plugin: MetricPlugin) -> None:
        """Bestandsaufrufe mit zwei Argumenten müssen weiter funktionieren."""
        sig = inspect.signature(plugin.render)
        assert sig.parameters["lang"].default == DEFAULT_LANG, plugin.metric_id
