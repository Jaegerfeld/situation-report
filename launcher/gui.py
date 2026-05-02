# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.04.2026
# Geändert:       02.05.2026
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
#   Beim Start wird im Hintergrund auf neue Versionen geprüft (GitHub Releases).
# =============================================================================

from __future__ import annotations

import json
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk
from typing import Literal

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

C_ACCENT = "#2980b9"

_UPDATE_API = "https://api.github.com/repos/Jaegerfeld/situation-report/releases/latest"
_RELEASES_URL = "https://github.com/Jaegerfeld/situation-report/releases/latest"


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version tag like 'v0.9.0' or '0.9.0' into a comparable int tuple."""
    return tuple(int(x) for x in tag.lstrip("v").split("."))


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
    LANG_RO: "https://jaegerfeld.github.io/situation-report/launcher_ManualUtilizator.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/launcher_ManualUtilizador.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/launcher_ManuelUtilisateur.pdf",
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
        "lbl_update":                     "Update verfügbar: {version}",
        "btn_download":                   "Herunterladen",
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
        "mod_helper_name":               "Helper",
        "mod_helper_desc":               "JSON-Dateien zusammenführen",
    },
    LANG_EN: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Launch",
        "lbl_planned":                    "(coming soon)",
        "tip_language":                   "Switch language",
        "tip_manual":                     "Open user manual",
        "lbl_update":                     "Update available: {version}",
        "btn_download":                   "Download",
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
        "mod_helper_name":               "Helper",
        "mod_helper_desc":               "Merge JSON files",
    },
    LANG_RO: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Lansare",
        "lbl_planned":                    "(în curând)",
        "tip_language":                   "Schimbați limba",
        "tip_manual":                     "Deschideți manualul",
        "lbl_update":                     "Actualizare disponibilă: {version}",
        "btn_download":                   "Descărcare",
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
        "mod_helper_name":               "Helper",
        "mod_helper_desc":               "Combinare fișiere JSON",
    },
    LANG_PT: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Iniciar",
        "lbl_planned":                    "(em breve)",
        "tip_language":                   "Mudar idioma",
        "tip_manual":                     "Abrir manual do utilizador",
        "lbl_update":                     "Atualização disponível: {version}",
        "btn_download":                   "Transferir",
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
        "mod_helper_name":               "Helper",
        "mod_helper_desc":               "Combinar ficheiros JSON",
    },
    LANG_FR: {
        "window_title":                   "SituationReport",
        "btn_launch":                     "Lancer",
        "lbl_planned":                    "(bientôt disponible)",
        "tip_language":                   "Changer de langue",
        "tip_manual":                     "Ouvrir le manuel",
        "lbl_update":                     "Mise à jour disponible : {version}",
        "btn_download":                   "Télécharger",
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
        "mod_helper_name":               "Helper",
        "mod_helper_desc":               "Fusionner des fichiers JSON",
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
    maturity: Literal["alpha", "beta"] | None = None


_MODULES: list[_ModuleEntry] = [
    _ModuleEntry("transform_data",     "🔄", True,  "beta"),
    _ModuleEntry("build_reports",      "📊", True,  "beta"),
    _ModuleEntry("get_data",           "📥", False, None),
    _ModuleEntry("simulate",           "🎲", False, None),
    _ModuleEntry("testdata_generator", "🧪", True,  "alpha"),
    _ModuleEntry("helper",             "🔧", True,  "alpha"),
]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class LauncherApp(tk.Tk):
    """Main tkinter application window for the SituationReport launcher."""

    def __init__(self) -> None:
        super().__init__()
        self.resizable(False, True)

        self._lang_var = tk.StringVar(value=_load_lang_pref())
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._flag_btn: tk.Button | None = None
        self._manual_btn: tk.Button | None = None
        self._title_lbl: tk.Label | None = None
        self._card_widgets: list[dict] = []
        self._update_bar: tk.Frame | None = None
        self._update_lbl: tk.Label | None = None
        self._update_btn: tk.Button | None = None
        self._separator: ttk.Separator | None = None
        self._latest_version: str | None = None

        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._create_flag_imgs()
        self._build_ui()
        self._apply_language()
        self._fit_to_screen()
        threading.Thread(target=self._check_for_update, daemon=True).start()

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
            title_frame, text="BETA",
            fg="white", bg="#e67e22",
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

        # Update notification bar — hidden until a newer version is detected
        self._update_bar = tk.Frame(self, bg="#fff3cd")

        self._separator = ttk.Separator(self, orient="horizontal")
        self._separator.pack(fill="x", pady=(0, 12))

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

        name_frame = tk.Frame(frame)
        name_frame.pack(pady=(6, 0))

        name_lbl = tk.Label(name_frame, font=("TkDefaultFont", 11, "bold"))
        name_lbl.pack(side="left")

        if entry.maturity:
            badge_color = "#e74c3c" if entry.maturity == "alpha" else "#e67e22"
            tk.Label(
                name_frame, text=entry.maturity.upper(),
                fg="white", bg=badge_color,
                font=("TkDefaultFont", 7, "bold"),
                padx=4, pady=1,
            ).pack(side="left", padx=(5, 0))

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
        self.title(f"{self._tr('window_title')} – BETA")
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

        if self._latest_version:
            if self._update_lbl:
                self._update_lbl.configure(
                    text=self._tr("lbl_update").format(version=self._latest_version)
                )
            if self._update_btn:
                self._update_btn.configure(text=self._tr("btn_download"))

    def _check_for_update(self) -> None:
        """Background thread: query the GitHub Releases API and compare versions."""
        if _VERSION == "?":
            return
        try:
            req = urllib.request.Request(
                _UPDATE_API,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"SituationReport/{_VERSION}",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            latest_tag = data.get("tag_name", "")
            if not latest_tag:
                return
            if _parse_version(latest_tag) > _parse_version(_VERSION):
                self.after(0, lambda: self._show_update_banner(latest_tag))
        except Exception:
            pass

    def _show_update_banner(self, latest_tag: str) -> None:
        """Display the yellow update notification bar above the module grid."""
        self._latest_version = latest_tag

        inner = tk.Frame(self._update_bar, bg="#fff3cd")
        inner.pack(padx=12, pady=6)

        self._update_lbl = tk.Label(
            inner,
            text=self._tr("lbl_update").format(version=latest_tag),
            bg="#fff3cd",
            fg="#856404",
        )
        self._update_lbl.pack(side="left")

        self._update_btn = tk.Button(
            inner,
            text=self._tr("btn_download"),
            relief="flat",
            cursor="hand2",
            bg="#ffc107",
            fg="#333333",
            font=("TkDefaultFont", 9, "bold"),
            command=lambda: webbrowser.open(_RELEASES_URL),
        )
        self._update_btn.pack(side="left", padx=(10, 0))

        self._update_bar.pack(fill="x", pady=(0, 8), before=self._separator)

    def _fit_to_screen(self) -> None:
        """Cap the initial window size so it fits within the screen (FullHD and above)."""
        self.update_idletasks()
        sh = self.winfo_screenheight()
        sw = self.winfo_screenwidth()
        w = min(self.winfo_reqwidth(), sw - 40)
        h = min(self.winfo_reqheight(), sh - 80)
        self.geometry(f"{w}x{h}")

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
