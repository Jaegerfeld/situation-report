# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       13.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für testdata_generator. Ermöglicht
#   die Konfiguration aller Generator-Parameter über Eingabefelder und startet
#   die Generierung per Knopfdruck. Unterstützt vier Flow-Muster (Triangle,
#   Flat Triangle, Cluster, Batch) sowie Cycle-Time-Steuerung per Slider.
#   Die Generierung läuft in einem separaten Thread; bei Operationen über
#   3 Sekunden erscheint ein Ladebalken. Ergebnisse und Fehler werden im
#   Log-Bereich angezeigt. Zusätzlich erzeugt der Demo-Portfolio-Bereich per
#   Knopfdruck das komplette Portfolio-Szenario (2 Solutions × 3 ARTs mit
#   allen Artefakten, scenario.py) und öffnet den Portfolio-Report im
#   Browser — der Evaluationspfad ohne Kommandozeile.
# =============================================================================

from __future__ import annotations

import json
import threading
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

import project_template

from .cli import run_generate
from .generator import (
    PATTERN_BATCH,
    PATTERN_CLUSTER,
    PATTERN_FLAT_TRIANGLE,
    PATTERN_NONE,
    PATTERN_TRIANGLE,
)

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_MANUAL_URLS: dict[str, str] = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/testdata_generator_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/testdata_generator_UserManual.pdf",
    LANG_RO: "https://jaegerfeld.github.io/situation-report/testdata_generator_UserManual.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/testdata_generator_UserManual.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/testdata_generator_UserManual.pdf",
}

_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

_PATTERN_LABELS = [
    (PATTERN_NONE,         "Kein Muster",    "No Pattern"),
    (PATTERN_TRIANGLE,     "Triangle",       "Triangle"),
    (PATTERN_FLAT_TRIANGLE,"Flat Triangle",  "Flat Triangle"),
    (PATTERN_CLUSTER,      "Cluster",        "Cluster"),
    (PATTERN_BATCH,        "Batch",          "Batch"),
]


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


_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "title":              f"testdata_generator {_VERSION}",
        "menu_help":          "Hilfe",
        "menu_manual":        "Manual",
        "menu_template":      "Templates",
        "menu_tpl_save":      "Speichern…",
        "menu_tpl_load":      "Laden…",
        "dlg_tpl_save":       "Template speichern",
        "dlg_tpl_load":       "Template laden",
        "log_tpl_saved":      "Template gespeichert: {}",
        "log_tpl_loaded":     "Template geladen: {}",
        "log_tpl_error":      "Fehler beim Template: {}",
        "log_tpl_missing":    "Hinweis: Datei aus Template nicht gefunden: {}",
        "tip_language":       "Sprache wechseln",
        "lbl_workflow":       "Workflow-Datei",
        "lbl_output":         "Ausgabedatei (JSON)",
        "lbl_project":        "Projekt-Key",
        "lbl_issues":         "Anzahl Issues",
        "lbl_from_date":      "Von (YYYY-MM-DD)",
        "lbl_to_date":        "Bis (YYYY-MM-DD)",
        "lbl_issue_types":    "Issue-Typen (Typ:Gewicht …)",
        "lbl_completion":     "Completion-Rate (0–1)",
        "lbl_todo":           "To-Do-Rate (0–1)",
        "lbl_backflow":       "Backflow-Prob. (0–1)",
        "lbl_seed":           "Seed (leer = zufällig)",
        "lbl_mean_cycle":     "Ø Cycle Time (Tage, leer=auto)",
        "lbl_std_cycle":      "Std.-Abw. (Tage, leer=auto)",
        "lbl_pattern":          "Muster",
        "lbl_pattern_strength": "Musterstärke (0–100)",
        "lbl_pi_weeks":         "PI-Dauer (Wochen)",
        "lbl_log":            "Log",
        "btn_browse_wf":      "Durchsuchen…",
        "btn_browse_out":     "Durchsuchen…",
        "btn_run":            "Generieren",
        "btn_report":         "Report erstellen",
        "log_report_started": "--- Report wird erstellt (transform + build_reports) ---",
        "log_report_done":    "--- Report im Browser geöffnet ---",
        "log_report_error":   "FEHLER beim Report: {}",
        "err_no_workflow":    "FEHLER: Keine Workflow-Datei ausgewählt.",
        "err_no_output":      "FEHLER: Keine Ausgabedatei angegeben.",
        "err_issues":         "FEHLER: Anzahl Issues muss eine positive Ganzzahl sein.",
        "err_completion":     "FEHLER: Completion-Rate muss zwischen 0 und 1 liegen.",
        "err_todo":           "FEHLER: To-Do-Rate muss zwischen 0 und 1 liegen.",
        "err_backflow":       "FEHLER: Backflow-Prob. muss zwischen 0 und 1 liegen.",
        "err_seed":           "FEHLER: Seed muss eine ganze Zahl sein.",
        "err_issue_types":    "FEHLER: Issue-Typen müssen im Format 'Typ:Gewicht' angegeben sein, z.B. Feature:0.6 Bug:0.3.",
        "err_mean_cycle":     "FEHLER: Ø Cycle Time muss eine positive Zahl sein.",
        "err_std_cycle":      "FEHLER: Std.-Abw. muss eine positive Zahl sein.",
        "err_pattern_no_mean":   "FEHLER: Muster erfordert eine Angabe für Ø Cycle Time.",
        "err_pattern_strength":  "FEHLER: Musterstärke muss eine ganze Zahl zwischen 0 und 100 sein.",
        "err_pi_weeks":          "FEHLER: PI-Dauer muss eine positive Ganzzahl sein.",
        "log_started":        "--- Generierung gestartet ---",
        "log_done":           "--- Fertig ---",
        "log_error":          "FEHLER: {}",
        "dlg_workflow":       "Workflow-Datei wählen",
        "dlg_output":         "Ausgabedatei wählen",
        "tip_issue_types":    "Leer = Feature:0.6 Bug:0.3 Enabler:0.1 (Standard)",
        "tip_seed":           "Gleicher Seed → identische Ausgabe (reproduzierbar)",
        "lbl_scenario":       "Demo-Portfolio (2 Solutions × 3 ARTs, alle Artefakte)",
        "btn_scenario":       "Demo-Portfolio erzeugen…",
        "btn_scenario_report": "Portfolio-Report öffnen",
        "dlg_scenario_dir":   "Zielordner für das Demo-Portfolio wählen",
        "log_scenario_started": "--- Demo-Portfolio wird erzeugt ---",
        "log_scenario_done":  "--- Demo-Portfolio erzeugt: {} ---",
        "log_scenario_hint":  "Direkt verwendbar: portfolio.json im portfolio-Modul laden oder hier den Report öffnen.",
        "log_scenario_error": "FEHLER beim Demo-Portfolio: {}",
        "btn_scenario_delta": "Delta-Briefing öffnen",
        "log_delta_started":  "--- Delta-Briefing wird erstellt (snapshot_prev → snapshot_now) ---",
        "log_delta_done":     "--- Delta-Briefing im Browser geöffnet ---",
        "log_delta_error":    "FEHLER beim Delta-Briefing: {}",
    },
    LANG_EN: {
        "title":              f"testdata_generator {_VERSION}",
        "menu_help":          "Help",
        "menu_manual":        "Manual",
        "menu_template":      "Templates",
        "menu_tpl_save":      "Save…",
        "menu_tpl_load":      "Load…",
        "dlg_tpl_save":       "Save Template",
        "dlg_tpl_load":       "Load Template",
        "log_tpl_saved":      "Template saved: {}",
        "log_tpl_loaded":     "Template loaded: {}",
        "log_tpl_error":      "Template error: {}",
        "log_tpl_missing":    "Note: file from template not found: {}",
        "tip_language":       "Change language",
        "lbl_workflow":       "Workflow File",
        "lbl_output":         "Output File (JSON)",
        "lbl_project":        "Project Key",
        "lbl_issues":         "Issue Count",
        "lbl_from_date":      "From (YYYY-MM-DD)",
        "lbl_to_date":        "To (YYYY-MM-DD)",
        "lbl_issue_types":    "Issue Types (Type:weight …)",
        "lbl_completion":     "Completion Rate (0–1)",
        "lbl_todo":           "To-Do Rate (0–1)",
        "lbl_backflow":       "Backflow Prob. (0–1)",
        "lbl_seed":           "Seed (empty = random)",
        "lbl_mean_cycle":     "Avg Cycle Time (days, empty=auto)",
        "lbl_std_cycle":      "Std Dev (days, empty=auto)",
        "lbl_pattern":          "Pattern",
        "lbl_pattern_strength": "Pattern Strength (0–100)",
        "lbl_pi_weeks":         "PI Duration (weeks)",
        "lbl_log":            "Log",
        "btn_browse_wf":      "Browse…",
        "btn_browse_out":     "Browse…",
        "btn_run":            "Generate",
        "btn_report":         "Create Report",
        "log_report_started": "--- Building report (transform + build_reports) ---",
        "log_report_done":    "--- Report opened in browser ---",
        "log_report_error":   "ERROR building report: {}",
        "err_no_workflow":    "ERROR: No workflow file selected.",
        "err_no_output":      "ERROR: No output file specified.",
        "err_issues":         "ERROR: Issue count must be a positive integer.",
        "err_completion":     "ERROR: Completion rate must be between 0 and 1.",
        "err_todo":           "ERROR: To-Do rate must be between 0 and 1.",
        "err_backflow":       "ERROR: Backflow probability must be between 0 and 1.",
        "err_seed":           "ERROR: Seed must be an integer.",
        "err_issue_types":    "ERROR: Issue types must be in 'Type:weight' format, e.g. Feature:0.6 Bug:0.3.",
        "err_mean_cycle":     "ERROR: Avg cycle time must be a positive number.",
        "err_std_cycle":      "ERROR: Std dev must be a positive number.",
        "err_pattern_no_mean":   "ERROR: Pattern requires an average cycle time to be set.",
        "err_pattern_strength":  "ERROR: Pattern strength must be an integer between 0 and 100.",
        "err_pi_weeks":          "ERROR: PI duration must be a positive integer.",
        "log_started":        "--- Generation started ---",
        "log_done":           "--- Done ---",
        "log_error":          "ERROR: {}",
        "dlg_workflow":       "Select workflow file",
        "dlg_output":         "Select output file",
        "tip_issue_types":    "Empty = Feature:0.6 Bug:0.3 Enabler:0.1 (default)",
        "tip_seed":           "Same seed → identical output (reproducible)",
        "lbl_scenario":       "Demo portfolio (2 solutions × 3 ARTs, all artifacts)",
        "btn_scenario":       "Generate Demo Portfolio…",
        "btn_scenario_report": "Open Portfolio Report",
        "dlg_scenario_dir":   "Select target folder for the demo portfolio",
        "log_scenario_started": "--- Generating demo portfolio ---",
        "log_scenario_done":  "--- Demo portfolio generated: {} ---",
        "log_scenario_hint":  "Ready to use: load portfolio.json in the portfolio module, or open the report here.",
        "log_scenario_error": "ERROR generating demo portfolio: {}",
        "btn_scenario_delta": "Open Delta Briefing",
        "log_delta_started":  "--- Building delta briefing (snapshot_prev → snapshot_now) ---",
        "log_delta_done":     "--- Delta briefing opened in browser ---",
        "log_delta_error":    "ERROR building delta briefing: {}",
    },
}


_TEMPLATE_FIELDS = (
    "workflow", "output", "project", "issues", "from_date", "to_date",
    "issue_types", "completion", "todo", "backflow", "seed",
    "mean_cycle", "std_cycle", "pattern", "pattern_strength", "pi_weeks",
)


def _build_report_html_file(
    json_path: Path,
    workflow_path: Path,
    log=print,
) -> str:
    """
    Run transform_data + build_reports on a generated JSON file and write the
    combined report to a temporary HTML file covering the full date range.

    Imports transform_data/build_reports lazily so the testdata_generator GUI
    starts without pulling those modules until a report is actually requested.

    Args:
        json_path:     Path to the generated Jira JSON file.
        workflow_path: Workflow .txt file (same one used for generation).
        log:           Progress callback.

    Returns:
        Path to the written temporary .html file, or "" if no figures were
        produced.
    """
    import tempfile

    from build_reports.cli import render_combined_html
    from transform_data.transform import run_transform

    out_dir = json_path.parent
    prefix = json_path.stem

    run_transform(
        json_path, workflow_path,
        output_dir=out_dir, prefix=prefix, log=log,
    )

    html = render_combined_html(
        issue_times=out_dir / f"{prefix}_IssueTimes.xlsx",
        cfd=out_dir / f"{prefix}_CFD.xlsx",
        workflow=workflow_path,
        transitions=out_dir / f"{prefix}_Transitions.xlsx",
        from_date=None,
        to_date=None,
        log=log,
    )
    if not html:
        return ""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        return f.name


def _build_portfolio_report_html_file(portfolio_json: Path, log=print) -> str:
    """
    Render the portfolio report for a generated demo scenario and write it to
    a temporary HTML file.

    Imports the portfolio module lazily so the testdata_generator GUI starts
    without pulling it until a portfolio report is actually requested.

    Args:
        portfolio_json: Path to the scenario's portfolio.json.
        log:            Progress callback.

    Returns:
        Path to the written temporary .html file, or "" if no figures were
        produced.
    """
    import tempfile

    from portfolio.aggregator import render_html
    from portfolio.solution_config import load_solution_config

    html = render_html(load_solution_config(portfolio_json), log=log)
    if not html:
        return ""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        return f.name


def _build_delta_html_file(prev_path: Path, now_path: Path, log=print) -> str:
    """
    Render the delta briefing for the demo scenario's two snapshots into a
    temporary HTML file (lazy portfolio import, like the report helpers).

    Args:
        prev_path: Earlier snapshot JSON (scenario's snapshot_prev.json).
        now_path:  Later snapshot JSON (scenario's snapshot_now.json).
        log:       Progress callback.

    Returns:
        Path of the written temporary .html file.
    """
    import tempfile

    from portfolio.delta import compute_delta, render_delta_html
    from portfolio.snapshot import load_snapshot

    html = render_delta_html(
        compute_delta(load_snapshot(prev_path), load_snapshot(now_path)))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        return f.name


def _build_template_section(values: dict[str, str]) -> dict:
    """Assemble the testdata_generator section for the shared project template."""
    return {key: str(values.get(key, "")) for key in _TEMPLATE_FIELDS}


def _parse_template_section(data: dict) -> dict:
    """Normalise a testdata_generator template section; missing keys → empty string."""
    return {key: str(data.get(key, "")) for key in _TEMPLATE_FIELDS}


class _App:
    """Main application window for testdata_generator GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._running = False
        self._last_report: dict[str, Path] | None = None
        self._last_scenario: Path | None = None
        self._last_snapshots: tuple[Path, Path] | None = None

        self._var_workflow    = tk.StringVar()
        self._var_output      = tk.StringVar()
        self._var_project     = tk.StringVar(value="TEST")
        self._var_issues      = tk.StringVar(value="100")
        self._var_from_date   = tk.StringVar(value="2025-01-01")
        self._var_to_date     = tk.StringVar(value="2025-12-31")
        self._var_issue_types = tk.StringVar()
        self._var_completion  = tk.StringVar(value="0.7")
        self._var_todo        = tk.StringVar(value="0.15")
        self._var_backflow    = tk.StringVar(value="0.1")
        self._var_seed        = tk.StringVar()
        self._var_mean_cycle  = tk.StringVar(value="")
        self._var_std_cycle   = tk.StringVar(value="")
        self._var_pattern          = tk.StringVar(value=PATTERN_NONE)
        self._var_pattern_strength = tk.StringVar(value="50")
        self._var_pi_weeks         = tk.StringVar(value="12")
        self._lang_var        = tk.StringVar(value=_load_lang_pref())
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._create_flag_imgs()

        self._build_menu()
        self._build_form()
        self._build_log()
        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._apply_language()

    def _t(self, key: str) -> str:
        return _T.get(self._lang_var.get(), _T[LANG_EN]).get(key, key)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self._root)
        tpl_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=self._t("menu_template"), menu=tpl_menu)
        tpl_menu.add_command(label=self._t("menu_tpl_save"), command=self._save_template)
        tpl_menu.add_command(label=self._t("menu_tpl_load"), command=self._load_template)
        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=self._t("menu_help"), menu=help_menu)
        help_menu.add_command(label=self._t("menu_manual"), command=self._open_manual)
        self._root.config(menu=menubar)

    def _build_form(self) -> None:
        frame = ttk.Frame(self._root, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, minsize=44)
        self._labels: dict[str, ttk.Label] = {}

        # ── Flag button (top-right) ──────────────────────────────────────────
        self._flag_btn = tk.Button(
            frame,
            image=self._flag_imgs[self._lang_var.get()],
            command=self._toggle_language,
            relief="flat", cursor="hand2", bd=0, padx=4, pady=2,
        )
        self._flag_btn.grid(row=0, column=3, sticky="ne", rowspan=5, padx=(2, 0))

        # ── Standard field rows ──────────────────────────────────────────────
        def row(r: int, lbl_key: str, var: tk.StringVar, browse_cmd=None) -> None:
            lbl = ttk.Label(frame, text="")
            lbl.grid(row=r, column=0, sticky="w", pady=2)
            self._labels[lbl_key] = lbl
            entry = ttk.Entry(frame, textvariable=var, width=48)
            entry.grid(row=r, column=1, sticky="ew", padx=(4, 0))
            if browse_cmd:
                btn = ttk.Button(frame, text="…", width=4, command=browse_cmd)
                btn.grid(row=r, column=2, padx=(2, 0))

        row(0,  "lbl_workflow",    self._var_workflow,    self._browse_workflow)
        row(1,  "lbl_output",      self._var_output,      self._browse_output)
        row(2,  "lbl_project",     self._var_project)
        row(3,  "lbl_issues",      self._var_issues)
        row(4,  "lbl_from_date",   self._var_from_date)
        row(5,  "lbl_to_date",     self._var_to_date)
        row(6,  "lbl_issue_types", self._var_issue_types)
        row(7,  "lbl_completion",  self._var_completion)
        row(8,  "lbl_todo",        self._var_todo)
        row(9,  "lbl_backflow",    self._var_backflow)
        row(10, "lbl_seed",        self._var_seed)

        # ── Separator ────────────────────────────────────────────────────────
        ttk.Separator(frame, orient="horizontal").grid(
            row=11, column=0, columnspan=3, sticky="ew", pady=(8, 4)
        )

        # ── Cycle Time rows (with sliders) ───────────────────────────────────
        self._mean_scale, self._mean_entry = self._slider_row(
            frame, 12, "lbl_mean_cycle", self._var_mean_cycle, 1, 365
        )
        self._std_scale, self._std_entry = self._slider_row(
            frame, 13, "lbl_std_cycle", self._var_std_cycle, 1, 180
        )

        # ── Pattern row ───────────────────────────────────────────────────────
        lbl_pat = ttk.Label(frame, text="")
        lbl_pat.grid(row=14, column=0, sticky="w", pady=(6, 2))
        self._labels["lbl_pattern"] = lbl_pat

        pf = ttk.Frame(frame)
        pf.grid(row=14, column=1, columnspan=2, sticky="w", padx=(4, 0), pady=(6, 2))
        self._pattern_rbs: list[ttk.Radiobutton] = []
        lang = self._lang_var.get()
        for val, lbl_de, lbl_en in _PATTERN_LABELS:
            lbl_text = lbl_de if lang == LANG_DE else lbl_en
            rb = ttk.Radiobutton(
                pf, text=lbl_text, variable=self._var_pattern, value=val,
                command=self._on_pattern_change,
            )
            rb.pack(side="left", padx=(0, 8))
            self._pattern_rbs.append(rb)

        # ── Pattern Strength row ──────────────────────────────────────────────
        self._strength_scale, self._strength_entry = self._slider_row(
            frame, 15, "lbl_pattern_strength", self._var_pattern_strength, 0, 100
        )
        self._strength_scale.configure(state="disabled")
        self._strength_entry.configure(state="disabled")

        # ── PI Duration row ───────────────────────────────────────────────────
        self._pi_scale, self._pi_entry = self._slider_row(
            frame, 16, "lbl_pi_weeks", self._var_pi_weeks, 4, 26
        )

        # ── Run + Report + Progress ───────────────────────────────────────────
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=17, column=0, columnspan=3, pady=(10, 4))
        self._btn_run = ttk.Button(btn_frame, text="Generate", command=self._run)
        self._btn_run.pack(side="left", padx=(0, 6))
        self._btn_report = ttk.Button(
            btn_frame, text="Create Report", command=self._make_report,
            state="disabled",
        )
        self._btn_report.pack(side="left")

        # ── Demo portfolio section ────────────────────────────────────────────
        ttk.Separator(frame, orient="horizontal").grid(
            row=18, column=0, columnspan=3, sticky="ew", pady=(8, 4)
        )
        lbl_scen = ttk.Label(frame, text="")
        lbl_scen.grid(row=19, column=0, columnspan=3, sticky="w")
        self._labels["lbl_scenario"] = lbl_scen

        scen_frame = ttk.Frame(frame)
        scen_frame.grid(row=20, column=0, columnspan=3, pady=(4, 4))
        self._btn_scenario = ttk.Button(
            scen_frame, text="Generate Demo Portfolio…",
            command=self._make_scenario,
        )
        self._btn_scenario.pack(side="left", padx=(0, 6))
        self._btn_scenario_report = ttk.Button(
            scen_frame, text="Open Portfolio Report",
            command=self._open_portfolio_report, state="disabled",
        )
        self._btn_scenario_report.pack(side="left", padx=(0, 6))
        self._btn_scenario_delta = ttk.Button(
            scen_frame, text="Open Delta Briefing",
            command=self._open_delta_briefing, state="disabled",
        )
        self._btn_scenario_delta.pack(side="left")

        self._progress = ttk.Progressbar(frame, mode="indeterminate")
        self._progress.grid(row=21, column=0, columnspan=3, sticky="ew")
        self._progress.grid_remove()

    def _slider_row(
        self,
        frame: ttk.Frame,
        r: int,
        lbl_key: str,
        var: tk.StringVar,
        from_v: float,
        to_v: float,
    ) -> tuple[ttk.Scale, ttk.Entry]:
        """Create a label + scale + entry row with bidirectional sync."""
        lbl = ttk.Label(frame, text="")
        lbl.grid(row=r, column=0, sticky="w", pady=2)
        self._labels[lbl_key] = lbl

        sc = ttk.Scale(frame, from_=from_v, to=to_v, orient="horizontal")
        sc.grid(row=r, column=1, sticky="ew", padx=(4, 0))

        ent = ttk.Entry(frame, textvariable=var, width=7)
        ent.grid(row=r, column=2, sticky="e", padx=(2, 0))

        _guard = [False]

        def _on_scale(val: str) -> None:
            if _guard[0]:
                return
            _guard[0] = True
            try:
                var.set(str(round(float(val))))
            finally:
                _guard[0] = False

        def _on_var(*_: object) -> None:
            if _guard[0]:
                return
            _guard[0] = True
            try:
                sc.set(float(var.get()))
            except ValueError:
                pass
            finally:
                _guard[0] = False

        sc.configure(command=_on_scale)
        var.trace_add("write", _on_var)

        try:
            sc.set(float(var.get()))
        except ValueError:
            pass

        return sc, ent

    def _build_log(self) -> None:
        log_frame = ttk.LabelFrame(self._root, text="Log", padding=4)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log_frame = log_frame
        self._log_widget = scrolledtext.ScrolledText(
            log_frame, height=12, state="disabled", wrap="word"
        )
        self._log_widget.grid(row=0, column=0, sticky="nsew")

    def _apply_language(self) -> None:
        _save_lang_pref(self._lang_var.get())
        self._root.title(self._t("title"))
        self._flag_btn.configure(image=self._flag_imgs[self._lang_var.get()])
        for key, lbl in self._labels.items():
            lbl.configure(text=self._t(key))
        self._btn_run.configure(text=self._t("btn_run"))
        self._btn_report.configure(text=self._t("btn_report"))
        self._btn_scenario.configure(text=self._t("btn_scenario"))
        self._btn_scenario_report.configure(text=self._t("btn_scenario_report"))
        self._btn_scenario_delta.configure(text=self._t("btn_scenario_delta"))
        self._log_frame.configure(text=self._t("lbl_log"))
        lang = self._lang_var.get()
        for rb, (_val, lbl_de, lbl_en) in zip(self._pattern_rbs, _PATTERN_LABELS):
            rb.configure(text=lbl_de if lang == LANG_DE else lbl_en)
        self._build_menu()

    def _on_pattern_change(self) -> None:
        pattern = self._var_pattern.get()
        strength_state = "normal" if pattern != PATTERN_NONE else "disabled"
        self._strength_scale.configure(state=strength_state)
        self._strength_entry.configure(state=strength_state)

    def _open_manual(self) -> None:
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
            row_px: list[str] = []
            for x in range(W):
                cx = abs(x - (W - 1) / 2)
                cy = abs(y - (H - 1) / 2)
                nx, ny = x / (W - 1), y / (H - 1)
                if cx < W * 0.13 or cy < H * 0.13:
                    row_px.append("#C8102E")
                elif cx < W * 0.24 or cy < H * 0.24:
                    row_px.append("#FFFFFF")
                elif abs(nx - ny) < 0.16 or abs(nx - (1 - ny)) < 0.16:
                    row_px.append("#FFFFFF")
                else:
                    row_px.append("#012169")
            gb.put("{" + " ".join(row_px) + "}", to=(0, y))

        ro = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row_px = ["#002B7F" if x < W // 3 else "#FCD116" if x < 2 * W // 3 else "#CE1126"
                      for x in range(W)]
            ro.put("{" + " ".join(row_px) + "}", to=(0, y))

        pt = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row_px = ["#006600" if x < W * 2 // 5 else "#FF0000" for x in range(W)]
            pt.put("{" + " ".join(row_px) + "}", to=(0, y))

        fr = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row_px = ["#002395" if x < W // 3 else "#FFFFFF" if x < 2 * W // 3 else "#ED2939"
                      for x in range(W)]
            fr.put("{" + " ".join(row_px) + "}", to=(0, y))

        self._flag_imgs = {LANG_DE: de, LANG_EN: gb, LANG_RO: ro, LANG_PT: pt, LANG_FR: fr}

    def _toggle_language(self) -> None:
        """Cycle the UI language through all available languages."""
        current = self._lang_var.get()
        idx = _LANG_ORDER.index(current) if current in _LANG_ORDER else -1
        self._lang_var.set(_LANG_ORDER[(idx + 1) % len(_LANG_ORDER)])

    def _browse_workflow(self) -> None:
        path = filedialog.askopenfilename(
            title=self._t("dlg_workflow"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._var_workflow.set(path)
            if not self._var_output.get():
                stem = Path(path).stem.replace("workflow_", "").replace("_workflow", "")
                self._var_output.set(str(Path(path).parent / f"{stem}_generated.json"))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_output"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._var_output.set(path)

    def _template_vars(self) -> dict[str, tk.StringVar]:
        """Map project-template field names to their StringVars."""
        return {
            "workflow": self._var_workflow,
            "output": self._var_output,
            "project": self._var_project,
            "issues": self._var_issues,
            "from_date": self._var_from_date,
            "to_date": self._var_to_date,
            "issue_types": self._var_issue_types,
            "completion": self._var_completion,
            "todo": self._var_todo,
            "backflow": self._var_backflow,
            "seed": self._var_seed,
            "mean_cycle": self._var_mean_cycle,
            "std_cycle": self._var_std_cycle,
            "pattern": self._var_pattern,
            "pattern_strength": self._var_pattern_strength,
            "pi_weeks": self._var_pi_weeks,
        }

    def _save_template(self) -> None:
        """Write the current parameters as this module's project-template section."""
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_tpl_save"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            section = _build_template_section(
                {k: v.get() for k, v in self._template_vars().items()}
            )
            project_template.save_template(
                Path(path),
                project_template.MODULE_TESTDATA_GENERATOR,
                section,
                language=self._lang_var.get(),
            )
            self._log_msg(self._t("log_tpl_saved").format(Path(path).name))
        except Exception as exc:
            self._log_msg(self._t("log_tpl_error").format(exc))

    def _load_template(self) -> None:
        """Load this module's section from a project-template file into the UI."""
        path = filedialog.askopenfilename(
            title=self._t("dlg_tpl_load"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            envelope = project_template.load_template(Path(path))
            section = _parse_template_section(
                project_template.get_section(
                    envelope, project_template.MODULE_TESTDATA_GENERATOR
                )
            )
        except Exception as exc:
            self._log_msg(self._t("log_tpl_error").format(exc))
            return

        for key, var in self._template_vars().items():
            var.set(section[key])
        self._on_pattern_change()

        if section["workflow"] and not Path(section["workflow"]).is_file():
            self._log_msg(self._t("log_tpl_missing").format(section["workflow"]))

        self._lang_var.set(envelope.get("language", self._lang_var.get()))
        self._log_msg(self._t("log_tpl_loaded").format(Path(path).name))

    def _log_msg(self, msg: str) -> None:
        self._log_widget.configure(state="normal")
        self._log_widget.insert("end", msg + "\n")
        self._log_widget.see("end")
        self._log_widget.configure(state="disabled")

    def _parse_float_in_range(self, var: tk.StringVar, err_key: str) -> float | None:
        try:
            val = float(var.get())
            if not (0.0 <= val <= 1.0):
                raise ValueError
            return val
        except ValueError:
            self._log_msg(self._t(err_key))
            return None

    def _parse_positive_float(self, var: tk.StringVar, err_key: str) -> float | None:
        """Parse a positive float; return None (no error) if the field is empty."""
        raw = var.get().strip()
        if not raw:
            return None
        try:
            val = float(raw)
            if val <= 0:
                raise ValueError
            return val
        except ValueError:
            self._log_msg(self._t(err_key))
            return None

    def _parse_issue_types(self, raw: str) -> dict[str, float] | None:
        if not raw.strip():
            return None
        result: dict[str, float] = {}
        for token in raw.split():
            parts = token.split(":", 1)
            if len(parts) != 2:
                return None
            try:
                result[parts[0]] = float(parts[1])
            except ValueError:
                return None
        return result if result else None

    def _run(self) -> None:  # noqa: C901
        if self._running:
            return

        workflow_str = self._var_workflow.get().strip()
        output_str = self._var_output.get().strip()

        if not workflow_str:
            self._log_msg(self._t("err_no_workflow"))
            return
        if not output_str:
            self._log_msg(self._t("err_no_output"))
            return

        try:
            issue_count = int(self._var_issues.get())
            if issue_count <= 0:
                raise ValueError
        except ValueError:
            self._log_msg(self._t("err_issues"))
            return

        completion_rate = self._parse_float_in_range(self._var_completion, "err_completion")
        if completion_rate is None:
            return
        todo_rate = self._parse_float_in_range(self._var_todo, "err_todo")
        if todo_rate is None:
            return
        backflow_prob = self._parse_float_in_range(self._var_backflow, "err_backflow")
        if backflow_prob is None:
            return

        seed: int | None = None
        seed_str = self._var_seed.get().strip()
        if seed_str:
            try:
                seed = int(seed_str)
            except ValueError:
                self._log_msg(self._t("err_seed"))
                return

        issue_types = self._parse_issue_types(self._var_issue_types.get())
        if self._var_issue_types.get().strip() and issue_types is None:
            self._log_msg(self._t("err_issue_types"))
            return

        from_date: date | None = None
        to_date: date | None = None
        try:
            if self._var_from_date.get().strip():
                from_date = date.fromisoformat(self._var_from_date.get().strip())
            if self._var_to_date.get().strip():
                to_date = date.fromisoformat(self._var_to_date.get().strip())
        except ValueError:
            self._log_msg("ERROR: Invalid date format — expected YYYY-MM-DD.")
            return

        # ── New: cycle time + pattern ────────────────────────────────────────
        mean_cycle_days = self._parse_positive_float(self._var_mean_cycle, "err_mean_cycle")
        if self._var_mean_cycle.get().strip() and mean_cycle_days is None:
            return

        std_cycle_days = self._parse_positive_float(self._var_std_cycle, "err_std_cycle")
        if self._var_std_cycle.get().strip() and std_cycle_days is None:
            return

        pattern = self._var_pattern.get()
        if pattern != PATTERN_NONE and mean_cycle_days is None:
            self._log_msg(self._t("err_pattern_no_mean"))
            return

        pattern_strength = 0.5
        if pattern != PATTERN_NONE:
            try:
                raw_strength = int(self._var_pattern_strength.get())
                if not (0 <= raw_strength <= 100):
                    raise ValueError
                pattern_strength = raw_strength / 100.0
            except ValueError:
                self._log_msg(self._t("err_pattern_strength"))
                return

        try:
            pi_duration_weeks = int(self._var_pi_weeks.get())
            if pi_duration_weeks <= 0:
                raise ValueError
        except ValueError:
            self._log_msg(self._t("err_pi_weeks"))
            return

        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_report.configure(state="disabled")
        self._last_report = None
        self._log_msg(self._t("log_started"))

        _progress_timer: list = []

        def show_progress() -> None:
            self._progress.grid()
            self._progress.start(10)

        _progress_timer.append(self._root.after(3000, show_progress))

        def _do() -> None:
            try:
                run_generate(
                    workflow=Path(workflow_str),
                    output=Path(output_str),
                    project_key=self._var_project.get().strip() or "TEST",
                    issue_count=issue_count,
                    from_date=from_date,
                    to_date=to_date,
                    issue_types=issue_types,
                    completion_rate=completion_rate,
                    todo_rate=todo_rate,
                    backflow_prob=backflow_prob,
                    seed=seed,
                    mean_cycle_days=mean_cycle_days,
                    std_cycle_days=std_cycle_days,
                    pattern=pattern,
                    pi_duration_weeks=pi_duration_weeks,
                    pattern_strength=pattern_strength,
                    log=self._log_msg,
                )
                self._last_report = {
                    "json": Path(output_str),
                    "workflow": Path(workflow_str),
                }
                self._root.after(0, lambda: self._log_msg(self._t("log_done")))
                self._root.after(
                    0, lambda: self._btn_report.configure(state="normal")
                )
            except Exception as exc:
                msg = self._t("log_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                for timer in _progress_timer:
                    self._root.after_cancel(timer)
                self._root.after(0, self._reset_ui)

        threading.Thread(target=_do, daemon=True).start()

    def _reset_ui(self) -> None:
        self._running = False
        self._btn_run.configure(state="normal")
        self._progress.stop()
        self._progress.grid_remove()

    def _reset_after_report(self) -> None:
        self._running = False
        self._btn_run.configure(state="normal")
        self._btn_report.configure(state="normal")
        self._progress.stop()
        self._progress.grid_remove()

    def _make_scenario(self) -> None:
        """Generate the complete demo portfolio (2 solutions x 3 ARTs) into a
        user-chosen folder; the seed field is honoured (default 42 so the
        demo stays reproducible)."""
        if self._running:
            return

        seed = 42
        seed_str = self._var_seed.get().strip()
        if seed_str:
            try:
                seed = int(seed_str)
            except ValueError:
                self._log_msg(self._t("err_seed"))
                return

        target = filedialog.askdirectory(title=self._t("dlg_scenario_dir"))
        if not target:
            return

        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_scenario.configure(state="disabled")
        self._btn_scenario_report.configure(state="disabled")
        self._btn_scenario_delta.configure(state="disabled")
        self._log_msg(self._t("log_scenario_started"))

        _timer: list = []

        def show_progress() -> None:
            self._progress.grid()
            self._progress.start(10)

        _timer.append(self._root.after(3000, show_progress))

        def _do() -> None:
            try:
                from .scenario import build_portfolio_scenario

                paths = build_portfolio_scenario(
                    Path(target), seed=seed, log=self._log_msg
                )
                self._last_scenario = paths["portfolio"]
                self._last_snapshots = (paths["snapshot_prev"],
                                        paths["snapshot_now"])
                done = self._t("log_scenario_done").format(target)
                self._root.after(0, lambda: self._log_msg(done))
                self._root.after(
                    0, lambda: self._log_msg(self._t("log_scenario_hint"))
                )
                self._root.after(
                    0,
                    lambda: self._btn_scenario_report.configure(state="normal"),
                )
            except Exception as exc:
                msg = self._t("log_scenario_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                for t in _timer:
                    self._root.after_cancel(t)
                self._root.after(0, self._reset_after_scenario)

        threading.Thread(target=_do, daemon=True).start()

    def _reset_after_scenario(self) -> None:
        self._running = False
        self._btn_run.configure(state="normal")
        self._btn_scenario.configure(state="normal")
        if self._last_scenario is not None:
            self._btn_scenario_report.configure(state="normal")
        if self._last_snapshots is not None:
            self._btn_scenario_delta.configure(state="normal")
        self._progress.stop()
        self._progress.grid_remove()

    def _open_portfolio_report(self) -> None:
        """Render the portfolio report for the last generated demo scenario
        and open it in the browser."""
        if self._running or self._last_scenario is None:
            return
        portfolio_json = self._last_scenario

        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_scenario.configure(state="disabled")
        self._btn_scenario_report.configure(state="disabled")
        self._btn_scenario_delta.configure(state="disabled")
        self._log_msg(self._t("log_report_started"))

        _timer: list = []

        def show_progress() -> None:
            self._progress.grid()
            self._progress.start(10)

        _timer.append(self._root.after(3000, show_progress))

        def _do() -> None:
            try:
                tmp_path = _build_portfolio_report_html_file(
                    portfolio_json, log=self._log_msg
                )
                if not tmp_path:
                    self._root.after(0, lambda: self._log_msg(
                        self._t("log_report_error").format("no figures")))
                    return

                webbrowser.open(f"file:///{tmp_path.replace(chr(92), '/')}")
                self._root.after(
                    0, lambda: self._log_msg(self._t("log_report_done"))
                )
            except Exception as exc:
                msg = self._t("log_report_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                for t in _timer:
                    self._root.after_cancel(t)
                self._root.after(0, self._reset_after_scenario)

        threading.Thread(target=_do, daemon=True).start()

    def _open_delta_briefing(self) -> None:
        """Render the delta briefing for the demo scenario's snapshot pair
        (prev → now) and open it in the browser."""
        if self._running or self._last_snapshots is None:
            return
        prev_path, now_path = self._last_snapshots

        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_scenario.configure(state="disabled")
        self._btn_scenario_report.configure(state="disabled")
        self._btn_scenario_delta.configure(state="disabled")
        self._log_msg(self._t("log_delta_started"))

        _timer: list = []

        def show_progress() -> None:
            self._progress.grid()
            self._progress.start(10)

        _timer.append(self._root.after(3000, show_progress))

        def _do() -> None:
            try:
                tmp_path = _build_delta_html_file(
                    prev_path, now_path, log=self._log_msg
                )
                webbrowser.open(f"file:///{tmp_path.replace(chr(92), '/')}")
                self._root.after(
                    0, lambda: self._log_msg(self._t("log_delta_done"))
                )
            except Exception as exc:
                msg = self._t("log_delta_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                for t in _timer:
                    self._root.after_cancel(t)
                self._root.after(0, self._reset_after_scenario)

        threading.Thread(target=_do, daemon=True).start()

    def _make_report(self) -> None:
        """Run transform_data + build_reports on the last generated file and
        open a single combined HTML report covering the full date range."""
        if self._running or self._last_report is None:
            return
        ctx = self._last_report

        self._running = True
        self._btn_run.configure(state="disabled")
        self._btn_report.configure(state="disabled")
        self._log_msg(self._t("log_report_started"))

        _timer: list = []

        def show_progress() -> None:
            self._progress.grid()
            self._progress.start(10)

        _timer.append(self._root.after(3000, show_progress))

        def _do() -> None:
            try:
                tmp_path = _build_report_html_file(
                    ctx["json"], ctx["workflow"], log=self._log_msg
                )
                if not tmp_path:
                    self._root.after(0, lambda: self._log_msg(
                        self._t("log_report_error").format("no figures")))
                    return

                webbrowser.open(f"file:///{tmp_path.replace(chr(92), '/')}")
                self._root.after(
                    0, lambda: self._log_msg(self._t("log_report_done"))
                )
            except Exception as exc:
                msg = self._t("log_report_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                for t in _timer:
                    self._root.after_cancel(t)
                self._root.after(0, self._reset_after_report)

        threading.Thread(target=_do, daemon=True).start()


def main() -> None:
    """Launch the testdata_generator GUI."""
    root = tk.Tk()
    root.resizable(True, True)
    root.minsize(520, 480)
    app = _App(root)  # noqa: F841
    root.mainloop()
