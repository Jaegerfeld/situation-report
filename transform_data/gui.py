# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.04.2026
# Geändert:       28.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für transform_data. Ermöglicht die
#   Auswahl von Jira-JSON-Export, Workflow-Definitionsdatei und Ausgabeordner
#   über Dateidialoge. Unterstützt Deutsch und Englisch (Sprachumschaltung im
#   Menü). Ausgabeordner und Präfix werden beim Öffnen der JSON-Datei
#   automatisch vorbelegt. Die Transformation läuft in einem separaten Thread,
#   sodass die Oberfläche während der Verarbeitung reaktionsfähig bleibt.
#   Bei Operationen über 3 Sekunden erscheint ein Ladebalken.
#   Warnungen und Ergebnisse werden im Log-Bereich angezeigt.
# =============================================================================

import json
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

from .transform import run_transform

# ---------------------------------------------------------------------------
# Language constants
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title":     "transform_data",
        "menu_options":     "Optionen",
        "menu_language":    "Sprache",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "menu_lang_ro":     "Română",
        "menu_lang_pt":     "Português",
        "menu_lang_fr":     "Français",
        "menu_help":        "Hilfe",
        "menu_manual":      "Manual",
        "lbl_json":         "JSON-Datei",
        "lbl_workflow":     "Workflow-Datei",
        "lbl_output_dir":   "Ausgabeordner",
        "lbl_prefix":       "Präfix",
        "lbl_log":          "Log",
        "btn_browse":       "Durchsuchen…",
        "btn_run":          "Ausführen",
        "dlg_json":         "JSON-Datei wählen",
        "dlg_workflow":     "Workflow-Datei wählen",
        "dlg_output_dir":   "Ausgabeordner wählen",
        "err_no_json":      "FEHLER: Keine JSON-Datei ausgewählt.",
        "err_no_workflow":  "FEHLER: Keine Workflow-Datei ausgewählt.",
        "err_json_missing": "FEHLER: JSON-Datei nicht gefunden: {}",
        "err_wf_missing":   "FEHLER: Workflow-Datei nicht gefunden: {}",
        "log_started":      "--- Transformation gestartet ---",
        "log_done":         "--- Fertig ---",
        "log_error":        "FEHLER: {}",
    },
    LANG_EN: {
        "window_title":     "transform_data",
        "menu_options":     "Options",
        "menu_language":    "Language",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "menu_lang_ro":     "Română",
        "menu_lang_pt":     "Português",
        "menu_lang_fr":     "Français",
        "menu_help":        "Help",
        "menu_manual":      "Manual",
        "lbl_json":         "JSON File",
        "lbl_workflow":     "Workflow File",
        "lbl_output_dir":   "Output Folder",
        "lbl_prefix":       "Prefix",
        "lbl_log":          "Log",
        "btn_browse":       "Browse…",
        "btn_run":          "Run",
        "dlg_json":         "Select JSON file",
        "dlg_workflow":     "Select workflow file",
        "dlg_output_dir":   "Select output folder",
        "err_no_json":      "ERROR: No JSON file selected.",
        "err_no_workflow":  "ERROR: No workflow file selected.",
        "err_json_missing": "ERROR: JSON file not found: {}",
        "err_wf_missing":   "ERROR: Workflow file not found: {}",
        "log_started":      "--- Transformation started ---",
        "log_done":         "--- Done ---",
        "log_error":        "ERROR: {}",
    },
    LANG_RO: {
        "window_title":     "transform_data",
        "menu_options":     "Opțiuni",
        "menu_language":    "Limbă",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "menu_lang_ro":     "Română",
        "menu_lang_pt":     "Português",
        "menu_lang_fr":     "Français",
        "menu_help":        "Ajutor",
        "menu_manual":      "Manual",
        "lbl_json":         "Fişier JSON",
        "lbl_workflow":     "Fişier Workflow",
        "lbl_output_dir":   "Folder de ieşire",
        "lbl_prefix":       "Prefix",
        "lbl_log":          "Jurnal",
        "btn_browse":       "Răsfoire…",
        "btn_run":          "Executare",
        "dlg_json":         "Selectați fişierul JSON",
        "dlg_workflow":     "Selectați fişierul Workflow",
        "dlg_output_dir":   "Selectați folderul de ieşire",
        "err_no_json":      "EROARE: Niciun fişier JSON selectat.",
        "err_no_workflow":  "EROARE: Niciun fişier Workflow selectat.",
        "err_json_missing": "EROARE: Fişier JSON negăsit: {}",
        "err_wf_missing":   "EROARE: Fişier Workflow negăsit: {}",
        "log_started":      "--- Transformare pornită ---",
        "log_done":         "--- Finalizat ---",
        "log_error":        "EROARE: {}",
    },
    LANG_PT: {
        "window_title":     "transform_data",
        "menu_options":     "Opções",
        "menu_language":    "Idioma",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "menu_lang_ro":     "Română",
        "menu_lang_pt":     "Português",
        "menu_lang_fr":     "Français",
        "menu_help":        "Ajuda",
        "menu_manual":      "Manual",
        "lbl_json":         "Ficheiro JSON",
        "lbl_workflow":     "Ficheiro Workflow",
        "lbl_output_dir":   "Pasta de saída",
        "lbl_prefix":       "Prefixo",
        "lbl_log":          "Registo",
        "btn_browse":       "Procurar…",
        "btn_run":          "Executar",
        "dlg_json":         "Selecionar ficheiro JSON",
        "dlg_workflow":     "Selecionar ficheiro Workflow",
        "dlg_output_dir":   "Selecionar pasta de saída",
        "err_no_json":      "ERRO: Nenhum ficheiro JSON selecionado.",
        "err_no_workflow":  "ERRO: Nenhum ficheiro Workflow selecionado.",
        "err_json_missing": "ERRO: Ficheiro JSON não encontrado: {}",
        "err_wf_missing":   "ERRO: Ficheiro Workflow não encontrado: {}",
        "log_started":      "--- Transformação iniciada ---",
        "log_done":         "--- Concluído ---",
        "log_error":        "ERRO: {}",
    },
    LANG_FR: {
        "window_title":     "transform_data",
        "menu_options":     "Options",
        "menu_language":    "Langue",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "menu_lang_ro":     "Română",
        "menu_lang_pt":     "Português",
        "menu_lang_fr":     "Français",
        "menu_help":        "Aide",
        "menu_manual":      "Manuel",
        "lbl_json":         "Fichier JSON",
        "lbl_workflow":     "Fichier Workflow",
        "lbl_output_dir":   "Dossier de sortie",
        "lbl_prefix":       "Préfixe",
        "lbl_log":          "Journal",
        "btn_browse":       "Parcourir…",
        "btn_run":          "Exécuter",
        "dlg_json":         "Sélectionner le fichier JSON",
        "dlg_workflow":     "Sélectionner le fichier Workflow",
        "dlg_output_dir":   "Sélectionner le dossier de sortie",
        "err_no_json":      "ERREUR : Aucun fichier JSON sélectionné.",
        "err_no_workflow":  "ERREUR : Aucun fichier Workflow sélectionné.",
        "err_json_missing": "ERREUR : Fichier JSON introuvable : {}",
        "err_wf_missing":   "ERREUR : Fichier Workflow introuvable : {}",
        "log_started":      "--- Transformation démarrée ---",
        "log_done":         "--- Terminé ---",
        "log_error":        "ERREUR : {}",
    },
}

_MANUAL_URLS: dict[str, str] = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/transform_data_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_RO: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
}

_LANG_FLAGS: dict[str, str] = {
    LANG_DE: "🇩🇪", LANG_EN: "🇬🇧", LANG_RO: "🇷🇴", LANG_PT: "🇵🇹", LANG_FR: "🇫🇷",
}

_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"


def _load_lang_pref() -> str:
    """Load the last-used language preference from disk, defaulting to English."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _T else LANG_EN
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


class TransformApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.resizable(True, True)

        self._lang_var = tk.StringVar(value=_load_lang_pref())
        self._lang_var.trace_add("write", lambda *_: self._apply_language())

        self._json_var = tk.StringVar()
        self._workflow_var = tk.StringVar()
        self._output_dir_var = tk.StringVar()
        self._prefix_var = tk.StringVar()
        self._auto_prefix: str = ""
        self._progress_after_id: str | None = None

        # widget refs for language updates
        self._lbl_json: tk.Label
        self._lbl_workflow: tk.Label
        self._lbl_output_dir: tk.Label
        self._lbl_prefix: tk.Label
        self._lbl_log: tk.Label
        self._btn_browse_json: ttk.Button
        self._btn_browse_workflow: ttk.Button
        self._btn_browse_output: ttk.Button
        self._run_btn: ttk.Button

        self._build_ui()
        self._apply_language()
        self._fit_to_screen()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _tr(self, key: str) -> str:
        """Return translated string for the current language."""
        return _T.get(self._lang_var.get(), _T[LANG_EN]).get(key, key)

    def _fit_to_screen(self) -> None:
        """Cap the initial window size so it fits within the screen (FullHD and above)."""
        self.update_idletasks()
        sh = self.winfo_screenheight()
        sw = self.winfo_screenwidth()
        w = min(self.winfo_reqwidth(), sw - 40)
        h = min(self.winfo_reqheight(), sh - 80)
        self.geometry(f"{w}x{h}")

    # -------------------------------------------------------------------------
    # Menu bar
    # -------------------------------------------------------------------------

    def _build_menubar(self) -> None:
        """Build (or rebuild) the top menu bar with Help → Manual and a language flag."""
        menubar = tk.Menu(self)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._tr("menu_help"), menu=help_menu)
        help_menu.add_command(label=self._tr("menu_manual"), command=self._open_manual)

        # Language flag (rightmost)
        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_radiobutton(label="🇩🇪  Deutsch",   variable=self._lang_var, value=LANG_DE)
        lang_menu.add_radiobutton(label="🇬🇧  English",   variable=self._lang_var, value=LANG_EN)
        lang_menu.add_radiobutton(label="🇷🇴  Română",    variable=self._lang_var, value=LANG_RO)
        lang_menu.add_radiobutton(label="🇵🇹  Português", variable=self._lang_var, value=LANG_PT)
        lang_menu.add_radiobutton(label="🇫🇷  Français",  variable=self._lang_var, value=LANG_FR)
        menubar.add_cascade(label=_LANG_FLAGS.get(self._lang_var.get(), "🌐"), menu=lang_menu)

        self.config(menu=menubar)

    def _open_manual(self) -> None:
        """Open the language-appropriate user manual PDF on GitHub Pages."""
        webbrowser.open(_MANUAL_URLS.get(self._lang_var.get(), _MANUAL_URLS[LANG_EN]))

    # -------------------------------------------------------------------------
    # UI build
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build all widgets. Labels and buttons are stored for language updates."""
        pad = {"padx": 8, "pady": 4}
        self.columnconfigure(1, weight=1)

        self._lbl_json = tk.Label(self, anchor="w")
        self._lbl_json.grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._json_var, state="readonly", width=55).grid(
            row=0, column=1, sticky="ew", **pad
        )
        self._btn_browse_json = ttk.Button(self, command=self._pick_json)
        self._btn_browse_json.grid(row=0, column=2, **pad)

        self._lbl_workflow = tk.Label(self, anchor="w")
        self._lbl_workflow.grid(row=1, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._workflow_var, state="readonly", width=55).grid(
            row=1, column=1, sticky="ew", **pad
        )
        self._btn_browse_workflow = ttk.Button(self, command=self._pick_workflow)
        self._btn_browse_workflow.grid(row=1, column=2, **pad)

        self._lbl_output_dir = tk.Label(self, anchor="w")
        self._lbl_output_dir.grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._output_dir_var, state="readonly", width=55).grid(
            row=2, column=1, sticky="ew", **pad
        )
        self._btn_browse_output = ttk.Button(self, command=self._pick_output_dir)
        self._btn_browse_output.grid(row=2, column=2, **pad)

        self._lbl_prefix = tk.Label(self, anchor="w")
        self._lbl_prefix.grid(row=3, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._prefix_var, width=55).grid(
            row=3, column=1, sticky="ew", **pad
        )

        self._run_btn = ttk.Button(self, command=self._run)
        self._run_btn.grid(row=4, column=0, columnspan=3, pady=8)

        self._progress_bar = ttk.Progressbar(self, mode="indeterminate", length=300)
        self._progress_bar.grid(row=5, column=0, columnspan=3, pady=(0, 4))
        self._progress_bar.grid_remove()

        self._lbl_log = tk.Label(self, anchor="w")
        self._lbl_log.grid(row=6, column=0, sticky="w", **pad)
        self._log_area = scrolledtext.ScrolledText(
            self, height=12, state="disabled", wrap="word"
        )
        self._log_area.grid(row=7, column=0, columnspan=3, sticky="nsew", **pad)
        self.rowconfigure(7, weight=1)

    def _apply_language(self) -> None:
        """Update window title, menu bar, and all translatable widget labels."""
        _save_lang_pref(self._lang_var.get())
        self.title(f"{self._tr('window_title')}  v{_VERSION}")
        self._build_menubar()
        self._lbl_json.config(text=self._tr("lbl_json"))
        self._lbl_workflow.config(text=self._tr("lbl_workflow"))
        self._lbl_output_dir.config(text=self._tr("lbl_output_dir"))
        self._lbl_prefix.config(text=self._tr("lbl_prefix"))
        self._lbl_log.config(text=self._tr("lbl_log"))
        self._btn_browse_json.config(text=self._tr("btn_browse"))
        self._btn_browse_workflow.config(text=self._tr("btn_browse"))
        self._btn_browse_output.config(text=self._tr("btn_browse"))
        self._run_btn.config(text=self._tr("btn_run"))

    # -------------------------------------------------------------------------
    # File pickers
    # -------------------------------------------------------------------------

    def _pick_json(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("dlg_json"),
            filetypes=[("JSON", "*.json"), ("*", "*.*")],
        )
        if not path:
            return
        self._json_var.set(path)
        if not self._output_dir_var.get():
            self._output_dir_var.set(str(Path(path).parent))
        stem = Path(path).stem
        if not self._prefix_var.get() or self._prefix_var.get() == self._auto_prefix:
            self._prefix_var.set(stem)
            self._auto_prefix = stem

    def _pick_workflow(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("dlg_workflow"),
            filetypes=[("Text", "*.txt"), ("*", "*.*")],
        )
        if path:
            self._workflow_var.set(path)

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title=self._tr("dlg_output_dir"))
        if path:
            self._output_dir_var.set(path)

    # -------------------------------------------------------------------------
    # Run
    # -------------------------------------------------------------------------

    def _run(self) -> None:
        json_path = self._json_var.get().strip()
        workflow_path = self._workflow_var.get().strip()

        if not json_path:
            self._log(self._tr("err_no_json"))
            return
        if not workflow_path:
            self._log(self._tr("err_no_workflow"))
            return
        if not Path(json_path).is_file():
            self._log(self._tr("err_json_missing").format(json_path))
            return
        if not Path(workflow_path).is_file():
            self._log(self._tr("err_wf_missing").format(workflow_path))
            return

        output_dir_str = self._output_dir_var.get().strip()
        output_dir = Path(output_dir_str) if output_dir_str else None
        prefix = self._prefix_var.get().strip() or None

        self._set_running(True)
        self._log(self._tr("log_started"))

        def worker() -> None:
            try:
                run_transform(
                    Path(json_path),
                    Path(workflow_path),
                    output_dir=output_dir,
                    prefix=prefix,
                    log=self._log,
                )
                self._log(self._tr("log_done"))
            except Exception as exc:
                self._log(self._tr("log_error").format(exc))
            finally:
                self.after(0, lambda: self._set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        def _append() -> None:
            self._log_area.configure(state="normal")
            self._log_area.insert("end", msg + "\n")
            self._log_area.see("end")
            self._log_area.configure(state="disabled")
        self.after(0, _append)

    def _set_running(self, running: bool) -> None:
        self._run_btn.configure(state="disabled" if running else "normal")
        if running:
            self._start_progress()
        else:
            self._stop_progress()

    def _start_progress(self) -> None:
        """Schedule the progress bar to appear after 3 seconds."""
        def _show() -> None:
            self._progress_bar.grid()
            self._progress_bar.start(10)
        self._progress_after_id = self.after(3000, _show)

    def _stop_progress(self) -> None:
        """Cancel any pending progress bar and hide it immediately."""
        if self._progress_after_id is not None:
            self.after_cancel(self._progress_after_id)
            self._progress_after_id = None
        self._progress_bar.stop()
        self._progress_bar.grid_remove()


if __name__ == "__main__":
    TransformApp().mainloop()
