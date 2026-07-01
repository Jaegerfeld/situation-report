# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       01.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   tkinter-GUI für den Monte-Carlo-Forecast. Erlaubt Auswahl einer
#   IssueTimes-Datei (optional CFD), Eingabe der Simulationsparameter
#   (History-Fenster, Horizont, Backlog, Läufe, Scope-Wachstum, Seed) und
#   erzeugt den HTML-Report. Die display-unabhängige Logik (Übersetzungen _T
#   und parse_form) ist getrennt gehalten und unit-getestet; der tkinter-Teil
#   wird im Test nicht instanziiert (benötigt eine laufende Anzeige).
# =============================================================================

from __future__ import annotations

import json
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .cli import run_simulation

# ---------------------------------------------------------------------------
# Sprache (geteilte Präferenzdatei mit Launcher/Portfolio)
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
_LANG_ORDER = [LANG_DE, LANG_EN]
_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"


def _load_lang_pref() -> str:
    """Lies die geteilte Sprachpräferenz; EN, wenn unbekannt/nicht gesetzt."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _LANG_ORDER else LANG_EN
    except Exception:
        return LANG_EN


def _save_lang_pref(lang: str) -> None:
    """Persistiere die Sprachpräferenz in die geteilte Datei."""
    try:
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        prefs: dict = {}
        try:
            with open(_PREFS_PATH) as f:
                prefs = json.load(f)
        except Exception:
            pass
        prefs["lang"] = lang
        with open(_PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Übersetzungen
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title": "Monte-Carlo-Forecast",
        "lbl_lang": "Sprache",
        "grp_data": "Daten",
        "grp_params": "Parameter",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, optional)",
        "btn_browse": "Durchsuchen …",
        "lbl_history_days": "History-Fenster (Tage)",
        "lbl_history_end": "History-Ende (JJJJ-MM-TT, leer = heute)",
        "lbl_horizon": "Horizont (Tage)",
        "lbl_backlog": "Backlog (Items, leer = kein Termin-Forecast)",
        "lbl_runs": "Läufe",
        "lbl_split_rate": "Scope-Wachstum (neue Items je erledigtem)",
        "lbl_seed": "Seed (leer = zufällig)",
        "btn_generate": "Report erzeugen …",
        "dlg_issue_times": "IssueTimes-Datei wählen",
        "dlg_cfd": "CFD-Datei wählen",
        "dlg_save": "Report speichern",
        "msg_need_issue_times": "Bitte eine IssueTimes-Datei wählen.",
        "msg_invalid": "Ungültige Eingabe: {error}",
        "msg_generating": "Report wird erzeugt …",
        "msg_done": "Report erzeugt: {path}",
        "msg_no_data": "Kein Durchsatz im History-Fenster — nichts zu simulieren.",
        "msg_error": "Fehler: {error}",
    },
    LANG_EN: {
        "window_title": "Monte-Carlo Forecast",
        "lbl_lang": "Language",
        "grp_data": "Data",
        "grp_params": "Parameters",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, optional)",
        "btn_browse": "Browse …",
        "lbl_history_days": "History window (days)",
        "lbl_history_end": "History end (YYYY-MM-DD, empty = today)",
        "lbl_horizon": "Horizon (days)",
        "lbl_backlog": "Backlog (items, empty = no date forecast)",
        "lbl_runs": "Runs",
        "lbl_split_rate": "Scope growth (new items per completed)",
        "lbl_seed": "Seed (empty = random)",
        "btn_generate": "Generate report …",
        "dlg_issue_times": "Choose IssueTimes file",
        "dlg_cfd": "Choose CFD file",
        "dlg_save": "Save report",
        "msg_need_issue_times": "Please choose an IssueTimes file.",
        "msg_invalid": "Invalid input: {error}",
        "msg_generating": "Generating report …",
        "msg_done": "Report generated: {path}",
        "msg_no_data": "No throughput in the history window — nothing to simulate.",
        "msg_error": "Error: {error}",
    },
}


def _tr(lang: str, key: str) -> str:
    """Übersetze `key`; EN-Fallback, wenn die Sprache/der Key fehlt."""
    return _T.get(lang, _T[LANG_EN]).get(key) or _T[LANG_EN][key]


# ---------------------------------------------------------------------------
# Display-unabhängige Form-Logik (unit-getestet)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunParams:
    """Validierte Simulationsparameter, fertig für run_simulation()."""

    issue_times: Path
    cfd: Path | None
    history_days: int
    history_end: date | None
    horizon_days: int
    backlog: int | None
    runs: int
    split_rate: float
    seed: int | None


def _req_int(value: str, name: str, minimum: int = 1) -> int:
    """Parse eine Pflicht-Ganzzahl mit Mindestwert."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer") from None
    if n < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return n


def _opt_int(value: str, name: str, minimum: int = 1) -> int | None:
    """Parse eine optionale Ganzzahl (leer -> None)."""
    if value.strip() == "":
        return None
    return _req_int(value, name, minimum)


def parse_form(
    issue_times: str,
    cfd: str,
    history_days: str,
    history_end: str,
    horizon: str,
    backlog: str,
    runs: str,
    split_rate: str,
    seed: str,
) -> RunParams:
    """
    Validiere die GUI-Felder (Strings) und baue typisierte RunParams.

    Args:
        issue_times: Pfad zur IssueTimes-Datei (Pflicht, nicht leer).
        cfd:         Optionaler CFD-Pfad (leer = None).
        history_days: History-Fensterlänge in Tagen (> 0).
        history_end: Optionales ISO-Enddatum (leer = None/heute).
        horizon:     Horizont in Tagen (> 0).
        backlog:     Optionale Item-Zahl für den Termin-Forecast (> 0 oder leer).
        runs:        Anzahl Läufe (> 0).
        split_rate:  Scope-Wachstum >= 0 (leer = 0.0).
        seed:        Optionaler Seed (leer = None).

    Returns:
        Validierte RunParams.

    Raises:
        ValueError: Bei fehlender Datei oder ungültigen Zahlen/Datum.
    """
    if issue_times.strip() == "":
        raise ValueError("issue_times is required")

    end: date | None = None
    if history_end.strip():
        try:
            end = datetime.strptime(history_end.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("history end must be YYYY-MM-DD") from None

    rate = 0.0
    if split_rate.strip():
        try:
            rate = float(split_rate)
        except ValueError:
            raise ValueError("split rate must be a number") from None
        if rate < 0:
            raise ValueError("split rate must be >= 0")

    return RunParams(
        issue_times=Path(issue_times.strip()),
        cfd=Path(cfd.strip()) if cfd.strip() else None,
        history_days=_req_int(history_days, "history days"),
        history_end=end,
        horizon_days=_req_int(horizon, "horizon"),
        backlog=_opt_int(backlog, "backlog"),
        runs=_req_int(runs, "runs"),
        split_rate=rate,
        seed=_opt_int(seed, "seed", minimum=0) if seed.strip() else None,
    )


# ---------------------------------------------------------------------------
# tkinter-GUI (nicht im Test instanziiert)
# ---------------------------------------------------------------------------

#: Standardwerte für die Eingabefelder.
_DEFAULTS = {
    "history_days": "180",
    "horizon": "84",
    "runs": "25000",
    "split_rate": "0.0",
}


class ForecastApp:
    """Schlankes Eingabeformular für den Monte-Carlo-Forecast."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = _load_lang_pref()
        self.vars: dict[str, tk.StringVar] = {
            k: tk.StringVar(value=_DEFAULTS.get(k, "")) for k in (
                "issue_times", "cfd", "history_days", "history_end",
                "horizon", "backlog", "runs", "split_rate", "seed")
        }
        self.status = tk.StringVar(value="")
        root.title(_tr(self.lang, "window_title"))
        self._build()

    def _t(self, key: str) -> str:
        return _tr(self.lang, key)

    def _build(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="nsew")
        self._build_lang(frm)
        self._build_data(frm)
        self._build_params(frm)
        ttk.Button(frm, text=self._t("btn_generate"),
                   command=self._on_generate).grid(column=0, columnspan=3,
                                                    pady=(12, 4), sticky="w")
        ttk.Label(frm, textvariable=self.status, foreground="#14304a").grid(
            column=0, columnspan=3, sticky="w")

    def _build_lang(self, frm: ttk.Frame) -> None:
        ttk.Label(frm, text=self._t("lbl_lang")).grid(column=0, row=0, sticky="w")
        box = ttk.Combobox(frm, values=_LANG_ORDER, width=6, state="readonly")
        box.set(self.lang)
        box.bind("<<ComboboxSelected>>", lambda _e: self._switch_lang(box.get()))
        box.grid(column=1, row=0, sticky="w", pady=(0, 8))

    def _switch_lang(self, lang: str) -> None:
        self.lang = lang if lang in _LANG_ORDER else LANG_EN
        _save_lang_pref(self.lang)
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self._t("window_title"))
        self._build()

    def _build_data(self, frm: ttk.Frame) -> None:
        grp = ttk.LabelFrame(frm, text=self._t("grp_data"), padding=8)
        grp.grid(column=0, columnspan=3, sticky="ew", pady=4)
        self._file_row(grp, 0, "lbl_issue_times", "issue_times",
                       "dlg_issue_times")
        self._file_row(grp, 1, "lbl_cfd", "cfd", "dlg_cfd")

    def _file_row(self, grp: ttk.LabelFrame, row: int, label_key: str,
                  var_key: str, dlg_key: str) -> None:
        ttk.Label(grp, text=self._t(label_key)).grid(column=0, row=row, sticky="w")
        ttk.Entry(grp, textvariable=self.vars[var_key], width=48).grid(
            column=1, row=row, sticky="w", padx=4)
        ttk.Button(grp, text=self._t("btn_browse"),
                   command=lambda: self._browse(var_key, dlg_key)).grid(
            column=2, row=row, sticky="w")

    def _build_params(self, frm: ttk.Frame) -> None:
        grp = ttk.LabelFrame(frm, text=self._t("grp_params"), padding=8)
        grp.grid(column=0, columnspan=3, sticky="ew", pady=4)
        fields = ["history_days", "history_end", "horizon", "backlog",
                  "runs", "split_rate", "seed"]
        for row, key in enumerate(fields):
            ttk.Label(grp, text=self._t(f"lbl_{key}")).grid(
                column=0, row=row, sticky="w")
            ttk.Entry(grp, textvariable=self.vars[key], width=20).grid(
                column=1, row=row, sticky="w", padx=4, pady=1)

    def _browse(self, var_key: str, dlg_key: str) -> None:
        path = filedialog.askopenfilename(
            title=self._t(dlg_key),
            filetypes=[("Excel", "*.xlsx"), ("All files", "*.*")])
        if path:
            self.vars[var_key].set(path)

    def _on_generate(self) -> None:
        try:
            params = parse_form(*(self.vars[k].get() for k in (
                "issue_times", "cfd", "history_days", "history_end",
                "horizon", "backlog", "runs", "split_rate", "seed")))
        except ValueError as exc:
            messagebox.showerror(self._t("window_title"),
                                 self._t("msg_invalid").format(error=exc))
            return
        output = filedialog.asksaveasfilename(
            title=self._t("dlg_save"), defaultextension=".html",
            filetypes=[("HTML", "*.html")])
        if not output:
            return
        self.status.set(self._t("msg_generating"))
        threading.Thread(target=self._run, args=(params, Path(output)),
                         daemon=True).start()

    def _run(self, params: RunParams, output: Path) -> None:
        try:
            html = run_simulation(
                params.issue_times, cfd=params.cfd,
                history_days=params.history_days, history_end=params.history_end,
                horizon_days=params.horizon_days, backlog=params.backlog,
                runs=params.runs, split_rate=params.split_rate, seed=params.seed,
                output_html=output, open_browser=True, log=lambda _m: None)
            msg = (self._t("msg_done").format(path=output) if html
                   else self._t("msg_no_data"))
        except Exception as exc:  # noqa: BLE001 — GUI darf nicht crashen
            msg = self._t("msg_error").format(error=exc)
        self.root.after(0, lambda: self.status.set(msg))


def main() -> None:
    """Starte die Forecast-GUI."""
    root = tk.Tk()
    ForecastApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
