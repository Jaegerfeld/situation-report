# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.04.2026
# Geändert:       22.05.2026
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
#   Warnungen und Ergebnisse werden im Log-Bereich angezeigt. Nach einem
#   erfolgreichen Lauf können die erzeugten Dateien per Datenübergabe direkt
#   in build_reports geöffnet werden.
# =============================================================================

import json
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

import project_template

from .transform import TransformResult, run_transform

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
        "menu_template":    "Templates",
        "menu_tpl_save":    "Speichern…",
        "menu_tpl_load":    "Laden…",
        "dlg_tpl_save":     "Template speichern",
        "dlg_tpl_load":     "Template laden",
        "log_tpl_saved":    "Template gespeichert: {}",
        "log_tpl_loaded":   "Template geladen: {}",
        "log_tpl_error":    "Fehler beim Template: {}",
        "log_tpl_missing":  "Hinweis: Datei aus Template nicht gefunden: {}",
        "lbl_json":         "JSON-Datei",
        "lbl_workflow":     "Workflow-Datei",
        "lbl_output_dir":   "Ausgabeordner",
        "lbl_prefix":       "Präfix",
        "lbl_log":          "Log",
        "btn_browse":       "Durchsuchen…",
        "btn_run":          "Ausführen",
        "btn_open_build_reports": "In build_reports öffnen",
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
        "log_handover":     "build_reports wird mit den transformierten Daten geöffnet…",
        "log_handover_error": "Fehler bei der Datenübergabe: {}",
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
        "menu_template":    "Templates",
        "menu_tpl_save":    "Save…",
        "menu_tpl_load":    "Load…",
        "dlg_tpl_save":     "Save Template",
        "dlg_tpl_load":     "Load Template",
        "log_tpl_saved":    "Template saved: {}",
        "log_tpl_loaded":   "Template loaded: {}",
        "log_tpl_error":    "Template error: {}",
        "log_tpl_missing":  "Note: file from template not found: {}",
        "lbl_json":         "JSON File",
        "lbl_workflow":     "Workflow File",
        "lbl_output_dir":   "Output Folder",
        "lbl_prefix":       "Prefix",
        "lbl_log":          "Log",
        "btn_browse":       "Browse…",
        "btn_run":          "Run",
        "btn_open_build_reports": "Open in build_reports",
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
        "log_handover":     "Opening build_reports with the transformed data…",
        "log_handover_error": "Data hand-over error: {}",
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
        "menu_template":    "Şabloane",
        "menu_tpl_save":    "Salvare…",
        "menu_tpl_load":    "Încărcare…",
        "dlg_tpl_save":     "Salvare şablon",
        "dlg_tpl_load":     "Încărcare şablon",
        "log_tpl_saved":    "Şablon salvat: {}",
        "log_tpl_loaded":   "Şablon încărcat: {}",
        "log_tpl_error":    "Eroare şablon: {}",
        "log_tpl_missing":  "Notă: fişier din şablon negăsit: {}",
        "lbl_json":         "Fişier JSON",
        "lbl_workflow":     "Fişier Workflow",
        "lbl_output_dir":   "Folder de ieşire",
        "lbl_prefix":       "Prefix",
        "lbl_log":          "Jurnal",
        "btn_browse":       "Răsfoire…",
        "btn_run":          "Executare",
        "btn_open_build_reports": "Deschidere în build_reports",
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
        "log_handover":     "Se deschide build_reports cu datele transformate…",
        "log_handover_error": "Eroare la transferul datelor: {}",
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
        "menu_template":    "Modelos",
        "menu_tpl_save":    "Guardar…",
        "menu_tpl_load":    "Carregar…",
        "dlg_tpl_save":     "Guardar modelo",
        "dlg_tpl_load":     "Carregar modelo",
        "log_tpl_saved":    "Modelo guardado: {}",
        "log_tpl_loaded":   "Modelo carregado: {}",
        "log_tpl_error":    "Erro no modelo: {}",
        "log_tpl_missing":  "Nota: ficheiro do modelo não encontrado: {}",
        "lbl_json":         "Ficheiro JSON",
        "lbl_workflow":     "Ficheiro Workflow",
        "lbl_output_dir":   "Pasta de saída",
        "lbl_prefix":       "Prefixo",
        "lbl_log":          "Registo",
        "btn_browse":       "Procurar…",
        "btn_run":          "Executar",
        "btn_open_build_reports": "Abrir no build_reports",
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
        "log_handover":     "A abrir o build_reports com os dados transformados…",
        "log_handover_error": "Erro na transferência de dados: {}",
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
        "menu_template":    "Modèles",
        "menu_tpl_save":    "Enregistrer…",
        "menu_tpl_load":    "Charger…",
        "dlg_tpl_save":     "Enregistrer le modèle",
        "dlg_tpl_load":     "Charger le modèle",
        "log_tpl_saved":    "Modèle enregistré : {}",
        "log_tpl_loaded":   "Modèle chargé : {}",
        "log_tpl_error":    "Erreur de modèle : {}",
        "log_tpl_missing":  "Note : fichier du modèle introuvable : {}",
        "lbl_json":         "Fichier JSON",
        "lbl_workflow":     "Fichier Workflow",
        "lbl_output_dir":   "Dossier de sortie",
        "lbl_prefix":       "Préfixe",
        "lbl_log":          "Journal",
        "btn_browse":       "Parcourir…",
        "btn_run":          "Exécuter",
        "btn_open_build_reports": "Ouvrir dans build_reports",
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
        "log_handover":     "Ouverture de build_reports avec les données transformées…",
        "log_handover_error": "Erreur de transfert de données : {}",
    },
}

_MANUAL_URLS: dict[str, str] = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/transform_data_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_RO: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/transform_data_UserManual.pdf",
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


def _build_template_section(
    json_file: str, workflow_file: str, output_dir: str, prefix: str
) -> dict:
    """Assemble the transform_data section for the shared project template."""
    return {
        "json_file": json_file,
        "workflow_file": workflow_file,
        "output_dir": output_dir,
        "prefix": prefix,
    }


def _parse_template_section(data: dict) -> dict:
    """Normalise a transform_data template section; missing keys → empty string."""
    return {
        "json_file": str(data.get("json_file", "")),
        "workflow_file": str(data.get("workflow_file", "")),
        "output_dir": str(data.get("output_dir", "")),
        "prefix": str(data.get("prefix", "")),
    }


def _build_handover_section(
    result: TransformResult,
    workflow_file: str,
    base_section: dict | None = None,
) -> dict:
    """
    Assemble the build_reports section for a data hand-over template.

    The three transformed XLSX paths and the workflow file are always set to
    the fresh values. If ``base_section`` is given (the build_reports section
    of a project template loaded in transform_data), every other key — PI
    config, filters, metric selection, terminology — is carried over so those
    settings reach build_reports. Without a base section the PI config stays
    empty for the user to pick.
    """
    section = dict(base_section) if base_section else {}
    section.update(
        {
            "issue_times": str(result.issue_times),
            "cfd": str(result.cfd),
            "transitions": str(result.transitions),
            "workflow": workflow_file,
        }
    )
    section.setdefault("pi_config", "")
    return section


def write_handover_template(
    path: Path,
    result: TransformResult,
    json_file: str,
    workflow_file: str,
    output_dir: str,
    prefix: str,
    language: str,
    base_template: Path | None = None,
) -> None:
    """
    Write a project template that hands transformed data to build_reports.

    The file holds both the transform_data section (for round-tripping the
    source paths) and a pre-filled build_reports section. build_reports loads
    it via ``--gui-template`` and deletes it afterwards.

    If ``base_template`` points at a readable project template, its
    build_reports section is used as the basis for the hand-over section so
    the user's PI config and filters carry over. An unreadable base template
    is ignored (the hand-over falls back to paths only).
    """
    base_section: dict | None = None
    if base_template is not None:
        try:
            envelope = project_template.load_template(base_template)
            base_section = project_template.get_section(
                envelope, project_template.MODULE_BUILD_REPORTS
            )
        except (OSError, ValueError, json.JSONDecodeError):
            base_section = None

    project_template.save_template(
        path,
        project_template.MODULE_TRANSFORM_DATA,
        _build_template_section(json_file, workflow_file, output_dir, prefix),
        language=language,
    )
    project_template.save_template(
        path,
        project_template.MODULE_BUILD_REPORTS,
        _build_handover_section(result, workflow_file, base_section),
    )


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
        self._last_result: TransformResult | None = None
        self._loaded_template_path: Path | None = None

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
        self._open_br_btn: ttk.Button

        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._create_flag_imgs()
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
        """Build (or rebuild) the top menu bar with Help → Manual."""
        menubar = tk.Menu(self)

        tpl_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._tr("menu_template"), menu=tpl_menu)
        tpl_menu.add_command(label=self._tr("menu_tpl_save"), command=self._save_template)
        tpl_menu.add_command(label=self._tr("menu_tpl_load"), command=self._load_template)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._tr("menu_help"), menu=help_menu)
        help_menu.add_command(label=self._tr("menu_manual"), command=self._open_manual)

        self.config(menu=menubar)

    def _open_manual(self) -> None:
        """Open the language-appropriate user manual PDF on GitHub Pages."""
        webbrowser.open(_MANUAL_URLS.get(self._lang_var.get(), _MANUAL_URLS[LANG_EN]))

    def _create_flag_imgs(self) -> None:
        """Build PhotoImage objects for all supported language flags using inline pixel drawing."""
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

    # -------------------------------------------------------------------------
    # UI build
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build all widgets. Labels and buttons are stored for language updates."""
        pad = {"padx": 8, "pady": 4}
        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, minsize=44)

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

        self._flag_btn = tk.Button(
            self,
            image=self._flag_imgs[self._lang_var.get()],
            command=self._toggle_language,
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=4,
            pady=2,
        )
        self._flag_btn.grid(row=0, column=3, sticky="ne", rowspan=4, padx=(2, 8))

        btn_bar = tk.Frame(self)
        btn_bar.grid(row=4, column=0, columnspan=3, pady=8)
        self._run_btn = ttk.Button(btn_bar, command=self._run)
        self._run_btn.pack(side="left", padx=4)
        self._open_br_btn = ttk.Button(
            btn_bar, command=self._open_in_build_reports, state="disabled"
        )
        self._open_br_btn.pack(side="left", padx=4)

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
        self._flag_btn.configure(image=self._flag_imgs[self._lang_var.get()])
        self._lbl_json.config(text=self._tr("lbl_json"))
        self._lbl_workflow.config(text=self._tr("lbl_workflow"))
        self._lbl_output_dir.config(text=self._tr("lbl_output_dir"))
        self._lbl_prefix.config(text=self._tr("lbl_prefix"))
        self._lbl_log.config(text=self._tr("lbl_log"))
        self._btn_browse_json.config(text=self._tr("btn_browse"))
        self._btn_browse_workflow.config(text=self._tr("btn_browse"))
        self._btn_browse_output.config(text=self._tr("btn_browse"))
        self._run_btn.config(text=self._tr("btn_run"))
        self._open_br_btn.config(text=self._tr("btn_open_build_reports"))

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
    # Project template
    # -------------------------------------------------------------------------

    def _save_template(self) -> None:
        """Write the current paths/prefix as this module's project-template section."""
        path = filedialog.asksaveasfilename(
            title=self._tr("dlg_tpl_save"),
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("*", "*.*")],
        )
        if not path:
            return
        try:
            section = _build_template_section(
                json_file=self._json_var.get(),
                workflow_file=self._workflow_var.get(),
                output_dir=self._output_dir_var.get(),
                prefix=self._prefix_var.get(),
            )
            project_template.save_template(
                Path(path),
                project_template.MODULE_TRANSFORM_DATA,
                section,
                language=self._lang_var.get(),
            )
            self._loaded_template_path = Path(path)
            self._log(self._tr("log_tpl_saved").format(Path(path).name))
        except Exception as exc:
            self._log(self._tr("log_tpl_error").format(exc))

    def _load_template(self) -> None:
        """Load this module's section from a project-template file into the UI."""
        path = filedialog.askopenfilename(
            title=self._tr("dlg_tpl_load"),
            filetypes=[("JSON", "*.json"), ("*", "*.*")],
        )
        if not path:
            return
        try:
            envelope = project_template.load_template(Path(path))
            section = _parse_template_section(
                project_template.get_section(
                    envelope, project_template.MODULE_TRANSFORM_DATA
                )
            )
        except Exception as exc:
            self._log(self._tr("log_tpl_error").format(exc))
            return

        self._json_var.set(section["json_file"])
        self._workflow_var.set(section["workflow_file"])
        self._output_dir_var.set(section["output_dir"])
        self._prefix_var.set(section["prefix"])
        self._auto_prefix = section["prefix"]

        for key in ("json_file", "workflow_file"):
            p = section[key]
            if p and not Path(p).is_file():
                self._log(self._tr("log_tpl_missing").format(p))

        self._lang_var.set(envelope.get("language", self._lang_var.get()))
        self._loaded_template_path = Path(path)
        self._log(self._tr("log_tpl_loaded").format(Path(path).name))

    # -------------------------------------------------------------------------
    # Data hand-over to build_reports
    # -------------------------------------------------------------------------

    def _open_in_build_reports(self) -> None:
        """
        Hand the freshly transformed files over to build_reports.

        Writes a temporary project template with a pre-filled build_reports
        section (the three XLSX files plus the workflow file) and launches
        build_reports with it, so the user does not have to re-select the
        files manually. build_reports consumes and deletes the template.

        If a project template is loaded, its build_reports settings (PI
        config, filters) are merged into the hand-over so they carry over.
        """
        if self._last_result is None:
            return
        try:
            with tempfile.NamedTemporaryFile(
                prefix="situation_report_handover_", suffix=".json", delete=False
            ) as tf:
                tmp_path = Path(tf.name)

            write_handover_template(
                tmp_path,
                self._last_result,
                json_file=self._json_var.get(),
                workflow_file=self._workflow_var.get(),
                output_dir=self._output_dir_var.get(),
                prefix=self._prefix_var.get(),
                language=self._lang_var.get(),
                base_template=self._loaded_template_path,
            )
            subprocess.Popen(
                [sys.executable, "-m", "build_reports",
                 "--gui-template", str(tmp_path)]
            )
            self._log(self._tr("log_handover"))
        except Exception as exc:
            self._log(self._tr("log_handover_error").format(exc))

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
                result = run_transform(
                    Path(json_path),
                    Path(workflow_path),
                    output_dir=output_dir,
                    prefix=prefix,
                    log=self._log,
                )
                self._last_result = result
                self._log(self._tr("log_done"))
                self.after(0, lambda: self._open_br_btn.configure(state="normal"))
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
            # The hand-over button stays disabled until a run succeeds; the
            # worker re-enables it on success.
            self._open_br_btn.configure(state="disabled")
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
