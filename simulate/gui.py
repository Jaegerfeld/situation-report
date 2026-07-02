# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       01.07.2026
# Geändert:       02.07.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   tkinter-GUI für den Monte-Carlo-Forecast. Erlaubt Auswahl einer
#   IssueTimes-Datei (optional CFD), Eingabe der Simulationsparameter
#   (History-Fenster, Horizont, Backlog, Läufe, Scope-Wachstum, Seed) und
#   erzeugt den HTML-Report. Wie die übrigen Modul-GUIs unterstützt sie fünf
#   Sprachen (Flaggen-Umschalter oben rechts) sowie den gemeinsamen
#   Projekt-Template-Modus (Menü „Templates“ → Speichern/Laden). Die
#   display-unabhängige Logik (Übersetzungen _T, parse_form sowie die
#   Template-Abschnittsfunktionen) ist getrennt gehalten und unit-getestet;
#   der tkinter-Teil wird im Test nicht instanziiert (benötigt eine Anzeige).
# =============================================================================

from __future__ import annotations

import json
import threading
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import project_template

from .cli import run_simulation

# ---------------------------------------------------------------------------
# Sprache (geteilte Präferenzdatei mit Launcher/Portfolio)
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"
_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]
_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

#: Hosted user-manual PDF per language (GitHub Pages, deployed from docs/).
_MANUAL_BASE = "https://jaegerfeld.github.io/situation-report/"
_MANUAL_URLS: dict[str, str] = {
    LANG_DE: _MANUAL_BASE + "simulate_Benutzerhandbuch.pdf",
    LANG_EN: _MANUAL_BASE + "simulate_UserManual.pdf",
    LANG_RO: _MANUAL_BASE + "simulate_ManualUtilizator.pdf",
    LANG_PT: _MANUAL_BASE + "simulate_ManualUtilizador.pdf",
    LANG_FR: _MANUAL_BASE + "simulate_ManuelUtilisateur.pdf",
}


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
        "menu_template": "Templates",
        "menu_tpl_save": "Speichern…",
        "menu_tpl_load": "Laden…",
        "menu_help": "Hilfe",
        "menu_manual": "Manual",
        "tip_language": "Sprache wechseln",
        "dlg_tpl_save": "Template speichern",
        "dlg_tpl_load": "Template laden",
        "log_tpl_saved": "Template gespeichert: {}",
        "log_tpl_loaded": "Template geladen: {}",
        "log_tpl_error": "Fehler beim Template: {}",
        "log_tpl_missing": "Hinweis: Datei aus Template nicht gefunden: {}",
        "grp_data": "Daten",
        "grp_params": "Parameter",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, optional)",
        "btn_browse": "Durchsuchen…",
        "lbl_history_days": "History-Fenster (Tage)",
        "lbl_history_end": "History-Ende (JJJJ-MM-TT, leer = heute)",
        "lbl_horizon": "Horizont (Tage)",
        "lbl_target_date": "Zieldatum (JJJJ-MM-TT, überschreibt Horizont)",
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
        "menu_template": "Templates",
        "menu_tpl_save": "Save…",
        "menu_tpl_load": "Load…",
        "menu_help": "Help",
        "menu_manual": "Manual",
        "tip_language": "Change language",
        "dlg_tpl_save": "Save Template",
        "dlg_tpl_load": "Load Template",
        "log_tpl_saved": "Template saved: {}",
        "log_tpl_loaded": "Template loaded: {}",
        "log_tpl_error": "Template error: {}",
        "log_tpl_missing": "Note: file from template not found: {}",
        "grp_data": "Data",
        "grp_params": "Parameters",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, optional)",
        "btn_browse": "Browse…",
        "lbl_history_days": "History window (days)",
        "lbl_history_end": "History end (YYYY-MM-DD, empty = today)",
        "lbl_horizon": "Horizon (days)",
        "lbl_target_date": "Target date (YYYY-MM-DD, overrides horizon)",
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
    LANG_RO: {
        "window_title": "Prognoză Monte-Carlo",
        "menu_template": "Şabloane",
        "menu_tpl_save": "Salvare…",
        "menu_tpl_load": "Încărcare…",
        "menu_help": "Ajutor",
        "menu_manual": "Manual",
        "tip_language": "Schimbă limba",
        "dlg_tpl_save": "Salvare şablon",
        "dlg_tpl_load": "Încărcare şablon",
        "log_tpl_saved": "Şablon salvat: {}",
        "log_tpl_loaded": "Şablon încărcat: {}",
        "log_tpl_error": "Eroare şablon: {}",
        "log_tpl_missing": "Notă: fişier din şablon negăsit: {}",
        "grp_data": "Date",
        "grp_params": "Parametri",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, opţional)",
        "btn_browse": "Răsfoire…",
        "lbl_history_days": "Fereastră istoric (zile)",
        "lbl_history_end": "Sfârşit istoric (AAAA-LL-ZZ, gol = azi)",
        "lbl_horizon": "Orizont (zile)",
        "lbl_target_date": "Dată ţintă (AAAA-LL-ZZ, înlocuieşte orizontul)",
        "lbl_backlog": "Backlog (elemente, gol = fără prognoză de termen)",
        "lbl_runs": "Rulări",
        "lbl_split_rate": "Creştere scop (elemente noi per finalizat)",
        "lbl_seed": "Sămânţă (gol = aleatoriu)",
        "btn_generate": "Generare raport …",
        "dlg_issue_times": "Selectaţi fişierul IssueTimes",
        "dlg_cfd": "Selectaţi fişierul CFD",
        "dlg_save": "Salvare raport",
        "msg_need_issue_times": "Selectaţi un fişier IssueTimes.",
        "msg_invalid": "Intrare nevalidă: {error}",
        "msg_generating": "Se generează raportul …",
        "msg_done": "Raport generat: {path}",
        "msg_no_data": "Niciun debit în fereastra de istoric — nimic de simulat.",
        "msg_error": "Eroare: {error}",
    },
    LANG_PT: {
        "window_title": "Previsão Monte-Carlo",
        "menu_template": "Modelos",
        "menu_tpl_save": "Guardar…",
        "menu_tpl_load": "Carregar…",
        "menu_help": "Ajuda",
        "menu_manual": "Manual",
        "tip_language": "Mudar idioma",
        "dlg_tpl_save": "Guardar modelo",
        "dlg_tpl_load": "Carregar modelo",
        "log_tpl_saved": "Modelo guardado: {}",
        "log_tpl_loaded": "Modelo carregado: {}",
        "log_tpl_error": "Erro no modelo: {}",
        "log_tpl_missing": "Nota: ficheiro do modelo não encontrado: {}",
        "grp_data": "Dados",
        "grp_params": "Parâmetros",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, opcional)",
        "btn_browse": "Procurar…",
        "lbl_history_days": "Janela de histórico (dias)",
        "lbl_history_end": "Fim do histórico (AAAA-MM-DD, vazio = hoje)",
        "lbl_horizon": "Horizonte (dias)",
        "lbl_target_date": "Data-alvo (AAAA-MM-DD, substitui o horizonte)",
        "lbl_backlog": "Backlog (itens, vazio = sem previsão de data)",
        "lbl_runs": "Execuções",
        "lbl_split_rate": "Crescimento do âmbito (novos itens por concluído)",
        "lbl_seed": "Semente (vazio = aleatório)",
        "btn_generate": "Gerar relatório …",
        "dlg_issue_times": "Selecionar ficheiro IssueTimes",
        "dlg_cfd": "Selecionar ficheiro CFD",
        "dlg_save": "Guardar relatório",
        "msg_need_issue_times": "Selecione um ficheiro IssueTimes.",
        "msg_invalid": "Entrada inválida: {error}",
        "msg_generating": "A gerar o relatório …",
        "msg_done": "Relatório gerado: {path}",
        "msg_no_data": "Sem throughput na janela de histórico — nada a simular.",
        "msg_error": "Erro: {error}",
    },
    LANG_FR: {
        "window_title": "Prévision Monte-Carlo",
        "menu_template": "Modèles",
        "menu_tpl_save": "Enregistrer…",
        "menu_tpl_load": "Charger…",
        "menu_help": "Aide",
        "menu_manual": "Manuel",
        "tip_language": "Changer de langue",
        "dlg_tpl_save": "Enregistrer le modèle",
        "dlg_tpl_load": "Charger le modèle",
        "log_tpl_saved": "Modèle enregistré : {}",
        "log_tpl_loaded": "Modèle chargé : {}",
        "log_tpl_error": "Erreur de modèle : {}",
        "log_tpl_missing": "Note : fichier du modèle introuvable : {}",
        "grp_data": "Données",
        "grp_params": "Paramètres",
        "lbl_issue_times": "IssueTimes (.xlsx)",
        "lbl_cfd": "CFD (.xlsx, optionnel)",
        "btn_browse": "Parcourir…",
        "lbl_history_days": "Fenêtre d'historique (jours)",
        "lbl_history_end": "Fin d'historique (AAAA-MM-JJ, vide = aujourd'hui)",
        "lbl_horizon": "Horizon (jours)",
        "lbl_target_date": "Date cible (AAAA-MM-JJ, remplace l'horizon)",
        "lbl_backlog": "Backlog (éléments, vide = pas de prévision de date)",
        "lbl_runs": "Exécutions",
        "lbl_split_rate": "Croissance du périmètre (nouveaux éléments par terminé)",
        "lbl_seed": "Graine (vide = aléatoire)",
        "btn_generate": "Générer le rapport …",
        "dlg_issue_times": "Choisir le fichier IssueTimes",
        "dlg_cfd": "Choisir le fichier CFD",
        "dlg_save": "Enregistrer le rapport",
        "msg_need_issue_times": "Veuillez choisir un fichier IssueTimes.",
        "msg_invalid": "Entrée invalide : {error}",
        "msg_generating": "Génération du rapport …",
        "msg_done": "Rapport généré : {path}",
        "msg_no_data": "Aucun débit dans la fenêtre d'historique — rien à simuler.",
        "msg_error": "Erreur : {error}",
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
    target_date: date | None
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


def _opt_date(value: str, name: str) -> date | None:
    """Parse ein optionales ISO-Datum (leer -> None)."""
    if value.strip() == "":
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{name} must be YYYY-MM-DD") from None


def parse_form(
    issue_times: str,
    cfd: str,
    history_days: str,
    history_end: str,
    horizon: str,
    target_date: str,
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
        target_date: Optionales ISO-Zieldatum; überschreibt den Horizont
                     ("wie viele Items bis zu diesem Termin?").
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

    end = _opt_date(history_end, "history end")
    target = _opt_date(target_date, "target date")

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
        target_date=target,
        backlog=_opt_int(backlog, "backlog"),
        runs=_req_int(runs, "runs"),
        split_rate=rate,
        seed=_opt_int(seed, "seed", minimum=0) if seed.strip() else None,
    )


# ---------------------------------------------------------------------------
# Projekt-Template-Abschnitt (display-unabhängig, unit-getestet)
# ---------------------------------------------------------------------------

#: Reihenfolge/Menge der Felder, die im simulate-Template-Abschnitt liegen.
_TEMPLATE_FIELDS = (
    "issue_times", "cfd", "history_days", "history_end", "horizon",
    "target_date", "backlog", "runs", "split_rate", "seed",
)


def _build_template_section(values: dict[str, str]) -> dict:
    """Assemble the simulate section for the shared project template."""
    return {key: str(values.get(key, "")) for key in _TEMPLATE_FIELDS}


def _parse_template_section(data: dict) -> dict:
    """Normalise a simulate template section; missing keys → empty string."""
    return {key: str(data.get(key, "")) for key in _TEMPLATE_FIELDS}


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
            k: tk.StringVar(value=_DEFAULTS.get(k, "")) for k in _TEMPLATE_FIELDS
        }
        self.status = tk.StringVar(value="")
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._create_flag_imgs()
        self._build()

    def _t(self, key: str) -> str:
        return _tr(self.lang, key)

    # -- Sprache ------------------------------------------------------------

    def _create_flag_imgs(self) -> None:
        """Build PhotoImage flags for all supported languages via inline pixels."""
        W, H = 32, 20

        de = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            color = ["#000000", "#DD0000", "#FFCC00"][y * 3 // H]
            de.put("{" + " ".join([color] * W) + "}", to=(0, y))

        gb = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row: list[str] = []
            for x in range(W):
                cx = abs(x - (W - 1) / 2)
                cy = abs(y - (H - 1) / 2)
                nx, ny = x / (W - 1), y / (H - 1)
                if cx < W * 0.13 or cy < H * 0.13:
                    row.append("#C8102E")
                elif cx < W * 0.24 or cy < H * 0.24:
                    row.append("#FFFFFF")
                elif abs(nx - ny) < 0.16 or abs(nx - (1 - ny)) < 0.16:
                    row.append("#FFFFFF")
                else:
                    row.append("#012169")
            gb.put("{" + " ".join(row) + "}", to=(0, y))

        ro = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row = ["#002B7F" if x < W // 3 else "#FCD116" if x < 2 * W // 3 else "#CE1126"
                   for x in range(W)]
            ro.put("{" + " ".join(row) + "}", to=(0, y))

        pt = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row = ["#006600" if x < W * 2 // 5 else "#FF0000" for x in range(W)]
            pt.put("{" + " ".join(row) + "}", to=(0, y))

        fr = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row = ["#002395" if x < W // 3 else "#FFFFFF" if x < 2 * W // 3 else "#ED2939"
                   for x in range(W)]
            fr.put("{" + " ".join(row) + "}", to=(0, y))

        self._flag_imgs = {LANG_DE: de, LANG_EN: gb, LANG_RO: ro, LANG_PT: pt, LANG_FR: fr}

    def _toggle_language(self) -> None:
        """Cycle the UI language through all available languages and rebuild."""
        idx = _LANG_ORDER.index(self.lang) if self.lang in _LANG_ORDER else -1
        self._set_language(_LANG_ORDER[(idx + 1) % len(_LANG_ORDER)])

    def _set_language(self, lang: str) -> None:
        """Persist the language and rebuild the whole window in that language."""
        self.lang = lang if lang in _LANG_ORDER else LANG_EN
        _save_lang_pref(self.lang)
        for child in self.root.winfo_children():
            child.destroy()
        self._build()

    def _open_manual(self) -> None:
        """Öffnet das gehostete Benutzerhandbuch (aktuelle Sprache) im Browser."""
        webbrowser.open(_MANUAL_URLS.get(self.lang, _MANUAL_URLS[LANG_EN]))

    # -- Aufbau -------------------------------------------------------------

    def _build(self) -> None:
        self.root.title(self._t("window_title"))
        self._build_menu()
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="nsew")
        self._flag_btn = tk.Button(
            frm, image=self._flag_imgs[self.lang], command=self._toggle_language,
            relief="flat", cursor="hand2", bd=0, padx=4, pady=2,
        )
        self._flag_btn.grid(column=2, row=0, sticky="ne", pady=(0, 4))
        self._build_data(frm)
        self._build_params(frm)
        ttk.Button(frm, text=self._t("btn_generate"),
                   command=self._on_generate).grid(column=0, columnspan=3,
                                                    pady=(12, 4), sticky="w")
        ttk.Label(frm, textvariable=self.status, foreground="#14304a").grid(
            column=0, columnspan=3, sticky="w")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        tpl_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=self._t("menu_template"), menu=tpl_menu)
        tpl_menu.add_command(label=self._t("menu_tpl_save"), command=self._save_template)
        tpl_menu.add_command(label=self._t("menu_tpl_load"), command=self._load_template)
        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=self._t("menu_help"), menu=help_menu)
        help_menu.add_command(label=self._t("menu_manual"), command=self._open_manual)
        self.root.config(menu=menubar)

    def _build_data(self, frm: ttk.Frame) -> None:
        grp = ttk.LabelFrame(frm, text=self._t("grp_data"), padding=8)
        grp.grid(column=0, columnspan=3, row=1, sticky="ew", pady=4)
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
        grp.grid(column=0, columnspan=3, row=2, sticky="ew", pady=4)
        fields = ["history_days", "history_end", "horizon", "target_date",
                  "backlog", "runs", "split_rate", "seed"]
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

    # -- Projekt-Template ---------------------------------------------------

    def _save_template(self) -> None:
        """Write the current form fields as this module's project-template section."""
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_tpl_save"), defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            section = _build_template_section(
                {k: v.get() for k, v in self.vars.items()})
            project_template.save_template(
                Path(path), project_template.MODULE_SIMULATE, section,
                language=self.lang)
            self.status.set(self._t("log_tpl_saved").format(Path(path).name))
        except Exception as exc:  # noqa: BLE001 — GUI darf nicht crashen
            self.status.set(self._t("log_tpl_error").format(exc))

    def _load_template(self) -> None:
        """Load this module's section from a project-template file into the UI."""
        path = filedialog.askopenfilename(
            title=self._t("dlg_tpl_load"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            envelope = project_template.load_template(Path(path))
            section = _parse_template_section(
                project_template.get_section(
                    envelope, project_template.MODULE_SIMULATE))
        except Exception as exc:  # noqa: BLE001 — GUI darf nicht crashen
            self.status.set(self._t("log_tpl_error").format(exc))
            return

        for key, var in self.vars.items():
            var.set(section[key])

        issue_times = section["issue_times"]
        missing = bool(issue_times) and not Path(issue_times).is_file()

        new_lang = envelope.get("language", self.lang)
        self._set_language(new_lang)

        if missing:
            self.status.set(self._t("log_tpl_missing").format(issue_times))
        else:
            self.status.set(self._t("log_tpl_loaded").format(Path(path).name))

    # -- Ausführung ---------------------------------------------------------

    def _on_generate(self) -> None:
        try:
            params = parse_form(*(self.vars[k].get() for k in _TEMPLATE_FIELDS))
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
                horizon_days=params.horizon_days, target_date=params.target_date,
                backlog=params.backlog,
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
