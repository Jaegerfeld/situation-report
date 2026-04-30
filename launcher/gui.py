# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.04.2026
# Geändert:       30.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Launcher-GUI für SituationReport. Zeigt alle verfügbaren und geplanten
#   Module als Karten-Grid. Verfügbare Module können direkt gestartet werden;
#   sie öffnen sich als eigenständige Prozesse in separaten Fenstern.
#   Geplante Module sind sichtbar, aber deaktiviert.
#   Sprache (DE/EN/RO/PT/FR) wird über den Flag-Button umgeschaltet und
#   aus der gemeinsamen Präferenzdatei ~/.situation_report/prefs.json geladen.
#   Über den ?-Button kann das Benutzerhandbuch geöffnet werden.
# =============================================================================

from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

C_ACCENT = "#2980b9"

# ---------------------------------------------------------------------------
# Language constants
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

_MANUAL_URLS: dict[str, str] = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/launcher_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/launcher_UserManual.pdf",
    LANG_RO: "https://jaegerfeld.github.io/situation-report/launcher_UserManual.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/launcher_UserManual.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/launcher_UserManual.pdf",
}


def _load_lang_pref() -> str:
    """Load the last-used language preference from disk, defaulting to English."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _LANG_ORDER else LANG_EN
    except Exception:
        return LANG_EN


def _save_lang_pref(lang: str) -> None:
    """Persist the language preference to disk."""
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


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Starten",
        "lbl_planned":                    "(bald verfügbar)",
        "tip_language":                   "Sprache wechseln",
        "tip_manual":                     "Benutzerhandbuch öffnen",
        "mod_build_reports_name":         "Build Reports",
        "mod_build_reports_desc":         "Flow-Metriken und Reports",
        "mod_transform_data_name":        "Transform Data",
        "mod_transform_data_desc":        "Jira-Daten aufbereiten",
        "mod_get_data_name":              "Get Data",
        "mod_get_data_desc":              "Daten aus Jira laden",
        "mod_simulate_name":              "Simulate",
        "mod_simulate_desc":              "Prognosen und Simulationen",
        "mod_testdata_generator_name":    "Testdata Generator",
        "mod_testdata_generator_desc":    "Synthetische Testdaten erstellen",
    },
    LANG_EN: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Launch",
        "lbl_planned":                    "(coming soon)",
        "tip_language":                   "Switch language",
        "tip_manual":                     "Open user manual",
        "mod_build_reports_name":         "Build Reports",
        "mod_build_reports_desc":         "Flow metrics and reports",
        "mod_transform_data_name":        "Transform Data",
        "mod_transform_data_desc":        "Prepare Jira data",
        "mod_get_data_name":              "Get Data",
        "mod_get_data_desc":              "Fetch data from Jira",
        "mod_simulate_name":              "Simulate",
        "mod_simulate_desc":              "Forecasts and simulations",
        "mod_testdata_generator_name":    "Testdata Generator",
        "mod_testdata_generator_desc":    "Generate synthetic test data",
    },
    LANG_RO: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Lansare",
        "lbl_planned":                    "(în curând)",
        "tip_language":                   "Schimbați limba",
        "tip_manual":                     "Deschideți manualul",
        "mod_build_reports_name":         "Build Reports",
        "mod_build_reports_desc":         "Metrici de flux și rapoarte",
        "mod_transform_data_name":        "Transform Data",
        "mod_transform_data_desc":        "Pregătire date Jira",
        "mod_get_data_name":              "Get Data",
        "mod_get_data_desc":              "Preluare date din Jira",
        "mod_simulate_name":              "Simulate",
        "mod_simulate_desc":              "Prognoze și simulări",
        "mod_testdata_generator_name":    "Testdata Generator",
        "mod_testdata_generator_desc":    "Generare date de test sintetice",
    },
    LANG_PT: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Iniciar",
        "lbl_planned":                    "(em breve)",
        "tip_language":                   "Mudar idioma",
        "tip_manual":                     "Abrir manual do utilizador",
        "mod_build_reports_name":         "Build Reports",
        "mod_build_reports_desc":         "Métricas de fluxo e relatórios",
        "mod_transform_data_name":        "Transform Data",
        "mod_transform_data_desc":        "Preparar dados Jira",
        "mod_get_data_name":              "Get Data",
        "mod_get_data_desc":              "Obter dados do Jira",
        "mod_simulate_name":              "Simulate",
        "mod_simulate_desc":              "Previsões e simulações",
        "mod_testdata_generator_name":    "Testdata Generator",
        "mod_testdata_generator_desc":    "Gerar dados de teste sintéticos",
    },
    LANG_FR: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Lancer",
        "lbl_planned":                    "(bientôt disponible)",
        "tip_language":                   "Changer de langue",
        "tip_manual":                     "Ouvrir le manuel",
        "mod_build_reports_name":         "Build Reports",
        "mod_build_reports_desc":         "Métriques de flux et rapports",
        "mod_transform_data_name":        "Transform Data",
        "mod_transform_data_desc":        "Préparer les données Jira",
        "mod_get_data_name":              "Get Data",
        "mod_get_data_desc":              "Récupérer les données Jira",
        "mod_simulate_name":              "Simulate",
        "mod_simulate_desc":              "Prévisions et simulations",
        "mod_testdata_generator_name":    "Testdata Generator",
        "mod_testdata_generator_desc":    "Générer des données de test synthétiques",
    },
}

# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------


@dataclass
class _ModuleEntry:
    """Descriptor for a single SituationReport module shown in the launcher."""
    module_id: str
    icon: str
    available: bool


_MODULES: list[_ModuleEntry] = [
    _ModuleEntry("transform_data",     "🔄", True),
    _ModuleEntry("build_reports",      "📊", True),
    _ModuleEntry("get_data",           "📥", False),
    _ModuleEntry("simulate",           "🎲", False),
    _ModuleEntry("testdata_generator", "🧪", False),
]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class LauncherApp(tk.Tk):
    """Main tkinter application window for the SituationReport launcher."""

    def __init__(self) -> None:
        super().__init__()
        self.resizable(False, False)

        self._lang_var = tk.StringVar(value=_load_lang_pref())
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._flag_btn: tk.Button | None = None
        self._manual_btn: tk.Button | None = None
        self._title_lbl: tk.Label | None = None
        self._card_widgets: list[dict] = []

        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._create_flag_imgs()
        self._build_ui()
        self._apply_language()

    def _tr(self, key: str) -> str:
        """Look up a translation key for the current language, falling back to English."""
        return _T.get(self._lang_var.get(), _T[LANG_EN]).get(key, key)

    def _create_flag_imgs(self) -> None:
        """
        Build PhotoImage objects for all supported language flags using inline pixel drawing.

        Images are generated programmatically (no external files) so they work
        inside a portable bundle without any resource-path handling.
        The images are stored in self._flag_imgs and must not be garbage-collected.
        """
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
        """Cycle the UI language through all available languages."""
        current = self._lang_var.get()
        idx = _LANG_ORDER.index(current) if current in _LANG_ORDER else -1
        self._lang_var.set(_LANG_ORDER[(idx + 1) % len(_LANG_ORDER)])

    def _build_ui(self) -> None:
        """Build the full UI: title bar and 2-column module card grid."""
        self.configure(padx=16, pady=12)

        # Title bar
        title_frame = tk.Frame(self)
        title_frame.pack(fill="x", pady=(0, 12))

        self._title_lbl = tk.Label(title_frame, font=("TkDefaultFont", 15, "bold"))
        self._title_lbl.pack(side="left")

        tk.Label(title_frame, text=f"v{_VERSION}", fg="#888888").pack(
            side="left", padx=(8, 0)
        )
        tk.Label(
            title_frame, text="ALPHA",
            fg="white", bg="#e74c3c",
            font=("TkDefaultFont", 8, "bold"),
            padx=5, pady=1,
        ).pack(side="left", padx=(6, 0))

        self._flag_btn = tk.Button(
            title_frame,
            image=self._flag_imgs.get(self._lang_var.get()),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._toggle_language,
        )
        self._flag_btn.pack(side="right", padx=(4, 0))

        self._manual_btn = tk.Button(
            title_frame,
            text="?",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("TkDefaultFont", 11, "bold"),
            fg=C_ACCENT,
            command=self._open_manual,
        )
        self._manual_btn.pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 12))

        # Card grid (2 columns)
        grid_frame = tk.Frame(self)
        grid_frame.pack(fill="both", expand=True)

        self._card_widgets = []
        for i, entry in enumerate(_MODULES):
            row, col = divmod(i, 2)
            card = self._build_card(grid_frame, entry)
            card["frame"].grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._card_widgets.append(card)

        grid_frame.columnconfigure(0, weight=1, minsize=170)
        grid_frame.columnconfigure(1, weight=1, minsize=170)

    def _build_card(self, parent: tk.Widget, entry: _ModuleEntry) -> dict:
        """
        Build a single module card and return handles to its translatable widgets.

        Args:
            parent: Parent widget for the card frame.
            entry:  Module entry with id, icon, and availability flag.

        Returns:
            Dict with keys: frame, name_lbl, desc_lbl, action_widget,
            module_id, available.
        """
        frame = ttk.Frame(parent, relief="solid", borderwidth=1, padding=14)

        tk.Label(frame, text=entry.icon, font=("TkDefaultFont", 30)).pack()

        name_lbl = tk.Label(frame, font=("TkDefaultFont", 11, "bold"))
        name_lbl.pack(pady=(6, 0))

        desc_lbl = tk.Label(frame, fg="#555555", wraplength=155, justify="center")
        desc_lbl.pack(pady=(3, 10))

        if entry.available:
            action_widget: tk.Widget = ttk.Button(
                frame,
                command=lambda mid=entry.module_id: self._launch(mid),
            )
        else:
            action_widget = tk.Label(
                frame, fg="#999999", font=("TkDefaultFont", 9, "italic")
            )

        action_widget.pack()

        return {
            "frame": frame,
            "name_lbl": name_lbl,
            "desc_lbl": desc_lbl,
            "action_widget": action_widget,
            "module_id": entry.module_id,
            "available": entry.available,
        }

    def _apply_language(self) -> None:
        """Update all translatable widgets and the window title for the current language."""
        _save_lang_pref(self._lang_var.get())
        self.title(f"{self._tr('window_title')} – ALPHA")
        if self._title_lbl:
            self._title_lbl.configure(text=self._tr("window_title"))
        if self._flag_btn and self._lang_var.get() in self._flag_imgs:
            self._flag_btn.configure(image=self._flag_imgs[self._lang_var.get()])

        for card in self._card_widgets:
            mid = card["module_id"]
            card["name_lbl"].configure(text=self._tr(f"mod_{mid}_name"))
            card["desc_lbl"].configure(text=self._tr(f"mod_{mid}_desc"))
            if card["available"]:
                card["action_widget"].configure(text=self._tr("btn_launch"))
            else:
                card["action_widget"].configure(text=self._tr("lbl_planned"))

    def _open_manual(self) -> None:
        """Open the language-appropriate user manual PDF on GitHub Pages."""
        webbrowser.open(_MANUAL_URLS.get(self._lang_var.get(), _MANUAL_URLS[LANG_EN]))

    def _launch(self, module_id: str) -> None:
        """
        Start a module as a separate process.

        Args:
            module_id: Python module name to run (e.g. 'build_reports').
        """
        subprocess.Popen([sys.executable, "-m", module_id])


def main() -> None:
    """Entry point for the launcher GUI."""
    LauncherApp().mainloop()
