# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       19.09.2026
# Geändert:       19.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Prüft den Sprachkatalog der Reportschicht: Vollständigkeit über alle fünf
#   Sprachen, gleiche Platzhalter je Schlüssel, Deckungsgleichheit von Farb-
#   und Schlüsseltabellen — und dass ein Report in jeder Sprache erzeugt wird
#   und sich vom englischen auch tatsächlich unterscheidet. Der letzte Punkt
#   ist der wichtigste: Ein Katalogeintrag, der nie verdrahtet wurde, fällt
#   sonst nicht auf.
# =============================================================================

from __future__ import annotations

import re
from datetime import date

import pytest

from portfolio import summary
from portfolio.capability_config import Capability
from portfolio.decision_config import LogEntry
from portfolio.dependency_config import Dependency
from portfolio.flow_problems_config import FlowProblem
from portfolio.nfr_config import Nfr, RunwayItem
from portfolio.report_texts import (
    _TEXTS,
    DEFAULT_LANG,
    LANGUAGES,
    keys,
    normalise,
    t,
)
from portfolio.risks_config import Risk
from portfolio.summary import SourceQuality
from portfolio.themes_config import Epic, StrategicTheme

PLATZHALTER = re.compile(r"\{(\w+)")


class TestCatalogue:
    def test_every_key_has_every_language(self) -> None:
        fehlend = [(k, lang) for k in keys() for lang in LANGUAGES
                   if lang not in _TEXTS[k]]
        assert fehlend == []

    def test_placeholders_match_across_languages(self) -> None:
        """Ein Platzhalter, den nur eine Sprache kennt, wirft zur Laufzeit —
        und zwar erst bei dem Anwender, der diese Sprache benutzt."""
        schief = {
            k: {lang: sorted(PLATZHALTER.findall(v))
                for lang, v in _TEXTS[k].items()}
            for k in keys()
            if len({tuple(sorted(PLATZHALTER.findall(v)))
                    for v in _TEXTS[k].values()}) > 1
        }
        assert schief == {}

    def test_unknown_key_raises(self) -> None:
        """Ein fehlender Schluessel ist ein Programmierfehler und soll laut
        sein — eine stille Ersatzausgabe landet im Report."""
        with pytest.raises(KeyError):
            t("gibt.es.nicht")

    def test_unknown_language_falls_back(self) -> None:
        """Eine unbekannte Sprache kommt aus einer Einstellung, nicht aus dem
        Code — sie faellt still auf die Vorgabe zurueck."""
        assert normalise("kl") == DEFAULT_LANG
        assert normalise(None) == DEFAULT_LANG
        assert t("col.status", "kl") == t("col.status", DEFAULT_LANG)

    def test_german_conference_prose_is_roberts_wording(self) -> None:
        """Die deutschen Eintraege des Konferenzblocks sind Roberts eigene
        Saetze aus 0.31.0 und werden nicht geglaettet."""
        assert t("vsc.input1", "de") == "Input 1 · Aktuelle Daten"
        assert t("vsc.input2", "de") == "Input 2 · Impediment-Backlog & Governance"
        assert (t("vsc.input3", "de")
                == "Input 3 · Business Objectives (Capability-Map & SLOs)")
        assert (t("vsc.input4", "de")
                == "Input 4 · Integrierte Roadmap & Strategic Themes")
        assert t("vsc.no_date", "de") == "Konferenztermin nicht gesetzt"
        assert "noch 19 Tage" == t("vsc.lead.days", "de", days=19)


class TestStatusKeyTables:
    """Farbtabelle und Schluesseltabelle muessen dieselben Status kennen."""

    PAARE = [
        ("_CONF_COLORS", "_CONF_TEXT_KEYS"),
        ("_ROAM_COLORS", "_ROAM_TEXT_KEYS"),
        ("_IMPACT_COLORS", "_IMPACT_TEXT_KEYS"),
        ("_NFR_STATUS_COLORS", "_NFR_TEXT_KEYS"),
        ("_RUNWAY_COLORS", "_RUNWAY_TEXT_KEYS"),
        ("_HEALTH_COLORS", "_HEALTH_TEXT_KEYS"),
        ("_DEP_STATUS_COLORS", "_DEP_TEXT_KEYS"),
        ("_LOG_STATUS_COLORS", "_LOG_TEXT_KEYS"),
        ("_SLO_STATUS_COLORS", "_SLO_TEXT_KEYS"),
        ("_TIER_COLORS", "_TIER_TEXT_KEYS"),
        ("_FLOW_STATUS_COLORS", "_FLOW_TEXT_KEYS"),
    ]

    @pytest.mark.parametrize("farben,schluessel", PAARE)
    def test_same_statuses(self, farben: str, schluessel: str) -> None:
        a = set(getattr(summary, farben))
        b = set(getattr(summary, schluessel))
        assert a == b, f"{farben} vs {schluessel}"

    @pytest.mark.parametrize("_farben,schluessel", PAARE)
    def test_keys_exist_in_catalogue(self, _farben: str, schluessel: str) -> None:
        fehlend = [v for v in getattr(summary, schluessel).values()
                   if v not in _TEXTS]
        assert fehlend == []


# ---------------------------------------------------------------------------
# Ein vollstaendiger Satz Registerdaten — je Tabelle eine Zeile, damit jede
# Renderfunktion etwas zu zeigen hat.
# ---------------------------------------------------------------------------

REF = date(2026, 9, 19)


def _alle_bloecke(lang: str) -> str:
    quality = [SourceQuality(label="ART A", records=100, pct_missing_first=5.0,
                             pct_open=30.0, has_cfd=True,
                             data_as_of=date(2026, 9, 5), age_days=14)]
    risks = [("Sol", Risk("R-1", "Lieferant", "owned", owner="Team A",
                          impact="high", status_since=date(2026, 6, 1)))]
    nfrs = [("Sol", Nfr("N-1", "Antwortzeit", "< 1s", "violated",
                        actual="1.4s", owner="Team A"))]
    runway = [("Sol", RunwayItem("RW-1", "Testumgebung", "gap",
                                 needed_by=date(2026, 8, 1), owner="Team A"))]
    caps = [("Sol", Capability("C-1", "Zahlung", "critical", [],
                               owner="Team A",
                               assessed_on=date(2026, 9, 1)))]
    deps = [("Sol", Dependency("D-1", "API", "ART A", "ART B", "blocked",
                               due=date(2026, 8, 1)))]
    logs = [("Sol", LogEntry("L-1", "decision", "Kaufen", "accepted",
                             owner="Team A", logged_on=date(2026, 8, 1),
                             review_by=date(2026, 9, 1)))]
    flows = [("Sol", FlowProblem("FP-1", "Testumgebung fehlt", "open",
                                 ["VS A", "VS B"], source="VSC",
                                 raised_on=date(2026, 6, 1), conferences=3))]
    themes = [("Sol", StrategicTheme("T-1", "Digital", "Beschreibung"))]
    epics = [("Sol", Epic("EP-1", "Portal", "ART A", "P1",
                          status="in_progress"))]
    return "".join([
        summary.render_quality_html(quality, lang=lang),
        summary.render_roam_html(risks, reference=REF, lang=lang),
        summary.render_nfr_html(nfrs, runway, reference=REF, lang=lang),
        summary.render_capabilities_html(caps, lang=lang),
        summary.render_dependencies_html(deps, reference=REF, lang=lang),
        summary.render_decisions_html(logs, reference=REF, lang=lang),
        summary.render_flow_problems_html(flows, reference=REF, lang=lang),
        summary.render_themes_html(themes, epics, lang=lang),
        summary.render_legend_key_html(lang),
    ])


class TestEveryLanguageRenders:
    @pytest.mark.parametrize("lang", LANGUAGES)
    def test_renders_without_a_missing_key(self, lang: str) -> None:
        html = _alle_bloecke(lang)
        assert html
        # Rohe Statusschluessel duerfen nicht durchschlagen.
        for roh in ("at_risk", "in_place", "on_track", "cross_vs"):
            assert roh not in html, f"{roh} steht roh im {lang}-Report"

    @pytest.mark.parametrize("lang", [x for x in LANGUAGES if x != "en"])
    def test_differs_from_english(self, lang: str) -> None:
        """Eine Sprache, die sich nicht vom Englischen unterscheidet, ist eine
        Sprache, die man zu uebersetzen vergessen hat."""
        assert _alle_bloecke(lang) != _alle_bloecke("en")

    def test_default_is_english(self) -> None:
        assert _alle_bloecke(DEFAULT_LANG) == _alle_bloecke("en")

    @pytest.mark.parametrize("lang,muster", [
        ("de", "19.09.2026"), ("en", "2026-09-19"), ("ro", "19.09.2026"),
        ("pt", "19/09/2026"), ("fr", "19/09/2026"),
    ])
    def test_date_format_follows_the_language(self, lang: str,
                                              muster: str) -> None:
        assert date(2026, 9, 19).strftime(t("fmt.date", lang)) == muster
