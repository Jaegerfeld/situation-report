# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Unit-Tests für die display-unabhängigen Teile von simulate.gui: die
#   Übersetzungstabelle _T (gleiche Keys, keine Leerwerte, EN-Fallback) und die
#   Form→RunParams-Validierung. Der tkinter-Teil wird nicht instanziiert.
# =============================================================================

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from simulate.gui import (
    _LANG_ORDER,
    _MANUAL_URLS,
    _T,
    LANG_DE,
    LANG_EN,
    LANG_FR,
    LANG_PT,
    LANG_RO,
    _tr,
    parse_form,
)

_ALL_LANGS = (LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR)


class TestTranslations:
    def test_all_languages_present(self) -> None:
        for lang in _ALL_LANGS:
            assert lang in _T

    def test_same_keys_in_all_languages(self) -> None:
        ref = set(_T[LANG_EN].keys())
        for lang in _ALL_LANGS:
            assert set(_T[lang].keys()) == ref

    def test_no_empty_values(self) -> None:
        for lang, entries in _T.items():
            for key, value in entries.items():
                assert value, f"Empty translation [{lang}][{key}]"

    def test_fallback_to_english(self) -> None:
        assert _tr("xx", "window_title") == _T[LANG_EN]["window_title"]

    def test_manual_urls(self) -> None:
        assert set(_MANUAL_URLS) == set(_LANG_ORDER)
        assert _MANUAL_URLS[LANG_DE].endswith("simulate_Benutzerhandbuch.pdf")
        assert _MANUAL_URLS[LANG_EN].endswith("simulate_UserManual.pdf")
        assert _MANUAL_URLS[LANG_RO].endswith("simulate_ManualUtilizator.pdf")
        assert _MANUAL_URLS[LANG_PT].endswith("simulate_ManualUtilizador.pdf")
        assert _MANUAL_URLS[LANG_FR].endswith("simulate_ManuelUtilisateur.pdf")

    def test_lang_order_is_five_languages(self) -> None:
        assert _LANG_ORDER == [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]


class TestParseForm:
    def _defaults(self, **over: str) -> dict[str, str]:
        base = dict(
            issue_times="C:/x/ART_A_IssueTimes.xlsx", cfd="", history_days="180",
            history_end="", horizon="84", target_date="", backlog="", runs="25000",
            split_rate="0.0", seed="",
        )
        base.update(over)
        return base

    def test_builds_valid_params(self) -> None:
        p = parse_form(**self._defaults(backlog="50", seed="7",
                                        history_end="2026-07-01", split_rate="0.1"))
        assert p.issue_times == Path("C:/x/ART_A_IssueTimes.xlsx")
        assert p.cfd is None
        assert p.history_days == 180
        assert p.history_end == date(2026, 7, 1)
        assert p.horizon_days == 84
        assert p.backlog == 50
        assert p.runs == 25000
        assert p.split_rate == pytest.approx(0.1)
        assert p.seed == 7

    def test_optional_fields_become_none(self) -> None:
        p = parse_form(**self._defaults())
        assert p.cfd is None and p.history_end is None
        assert p.backlog is None and p.seed is None
        assert p.target_date is None
        assert p.split_rate == 0.0

    def test_target_date_parsed(self) -> None:
        p = parse_form(**self._defaults(target_date="2026-09-30"))
        assert p.target_date == date(2026, 9, 30)

    def test_bad_target_date_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(target_date="30.09.2026"))

    def test_missing_issue_times_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(issue_times="  "))

    def test_bad_int_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(runs="abc"))

    def test_runs_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(runs="0"))

    def test_bad_date_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(history_end="01.07.2026"))

    def test_negative_split_rate_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_form(**self._defaults(split_rate="-0.5"))

    def test_seed_zero_allowed(self) -> None:
        assert parse_form(**self._defaults(seed="0")).seed == 0

    def test_cfd_path_kept(self) -> None:
        p = parse_form(**self._defaults(cfd="C:/x/ART_A_CFD.xlsx"))
        assert p.cfd == Path("C:/x/ART_A_CFD.xlsx")
