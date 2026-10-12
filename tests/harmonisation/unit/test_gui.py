# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests der display-unabhängigen Teile von harmonisation.gui:
#   Übersetzungstabelle, Manual-Adressen und die drei Formular-Parser.
#   Der tkinter-Teil wird nicht instanziiert.
# =============================================================================

from __future__ import annotations

from datetime import date

import pytest

from harmonisation.gui import (
    _LANG_ORDER,
    _MANUAL_URLS,
    _T,
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    UNKNOWN,
    _tr,
    parse_assessment_form,
    parse_decision_form,
    parse_process_form,
)
from harmonisation.model import (
    DECISION_BRAND_SPECIFIC,
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
)

_ALL_LANGS = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)


class TestTranslations:
    def test_same_keys_no_empty_values(self) -> None:
        ref = set(_T[LANG_EN])
        for lang in _ALL_LANGS:
            assert set(_T[lang]) == ref, lang
            assert all(_T[lang].values()), lang

    def test_fallback_to_english(self) -> None:
        assert _tr("xx", "window_title") == _T[LANG_EN]["window_title"]

    def test_manual_urls_per_language(self) -> None:
        assert set(_MANUAL_URLS) == set(_LANG_ORDER)
        assert _MANUAL_URLS[LANG_DE].endswith("harmonisation_Benutzerhandbuch.pdf")
        assert _MANUAL_URLS[LANG_EN].endswith("harmonisation_UserManual.pdf")


class TestProcessForm:
    def test_builds_process_with_brands(self) -> None:
        p = parse_process_form(" o2d ", "Order-to-Delivery", "Logistics", "A, B,,C ")
        assert p.id == "o2d" and p.brands == ("A", "B", "C") and p.owner == "Logistics"

    @pytest.mark.parametrize("pid, name", [("", "x"), ("a b", "x"), ("ok", "  ")])
    def test_rejects_bad_ids_and_names(self, pid: str, name: str) -> None:
        with pytest.raises(ValueError):
            parse_process_form(pid, name)


class TestAssessmentForm:
    def test_values_unknown_and_evidence(self) -> None:
        a = parse_assessment_form("o2d", "Me", "2026-10-12",
                                  {"bv1": ("4", EVIDENCE_DOCUMENTED), "bv2": (UNKNOWN, EVIDENCE_ESTIMATED),
                                   "bv3": ("", EVIDENCE_ESTIMATED)}, " note ")
        assert a.answers["bv1"].value == 4 and a.answers["bv1"].evidence == EVIDENCE_DOCUMENTED
        assert a.answers["bv2"].value is None and a.answers["bv3"].value is None
        assert a.day == date(2026, 10, 12) and a.note == "note"

    @pytest.mark.parametrize("value, evidence", [("5", EVIDENCE_ESTIMATED), ("x", EVIDENCE_ESTIMATED),
                                                 ("2", "guess")])
    def test_rejects_bad_answers(self, value: str, evidence: str) -> None:
        with pytest.raises(ValueError):
            parse_assessment_form("p", "a", "2026-10-12", {"bv1": (value, evidence)})

    def test_rejects_bad_date_and_missing_process(self) -> None:
        with pytest.raises(ValueError):
            parse_assessment_form("p", "a", "12.10.2026", {})
        with pytest.raises(ValueError):
            parse_assessment_form("", "a", "2026-10-12", {})


class TestDecisionForm:
    def test_builds_decision(self) -> None:
        d = parse_decision_form("c2o", DECISION_BRAND_SPECIFIC, " only the interface ", "2026-10-06", "Board")
        assert d.decision == DECISION_BRAND_SPECIFIC and d.depth == "only the interface"
        assert d.day == date(2026, 10, 6)

    def test_empty_date_is_allowed_bad_decision_is_not(self) -> None:
        assert parse_decision_form("c2o", "open").day is None
        with pytest.raises(ValueError):
            parse_decision_form("c2o", "maybe")
