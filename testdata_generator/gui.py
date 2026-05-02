# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       02.05.2026
# Geändert:       02.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für testdata_generator. Ermöglicht
#   die Konfiguration aller Generator-Parameter über Eingabefelder und startet
#   die Generierung per Knopfdruck. Die Generierung läuft in einem separaten
#   Thread; bei Operationen über 3 Sekunden erscheint ein Ladebalken.
#   Ergebnisse und Fehler werden im Log-Bereich angezeigt.
# =============================================================================

from __future__ import annotations

import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

from .cli import run_generate

_LANG_DE = "de"
_LANG_EN = "en"

_T: dict[str, dict[str, str]] = {
    _LANG_DE: {
        "title":            f"testdata_generator {_VERSION}",
        "menu_options":     "Optionen",
        "menu_language":    "Sprache",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "lbl_workflow":     "Workflow-Datei",
        "lbl_output":       "Ausgabedatei (JSON)",
        "lbl_project":      "Projekt-Key",
        "lbl_issues":       "Anzahl Issues",
        "lbl_from_date":    "Von (YYYY-MM-DD)",
        "lbl_to_date":      "Bis (YYYY-MM-DD)",
        "lbl_issue_types":  "Issue-Typen (Typ:Gewicht …)",
        "lbl_completion":   "Completion-Rate (0–1)",
        "lbl_todo":         "To-Do-Rate (0–1)",
        "lbl_backflow":     "Backflow-Prob. (0–1)",
        "lbl_seed":         "Seed (leer = zufällig)",
        "lbl_log":          "Log",
        "btn_browse_wf":    "Durchsuchen…",
        "btn_browse_out":   "Durchsuchen…",
        "btn_run":          "Generieren",
        "err_no_workflow":  "FEHLER: Keine Workflow-Datei ausgewählt.",
        "err_no_output":    "FEHLER: Keine Ausgabedatei angegeben.",
        "err_issues":       "FEHLER: Anzahl Issues muss eine positive Ganzzahl sein.",
        "err_completion":   "FEHLER: Completion-Rate muss zwischen 0 und 1 liegen.",
        "err_todo":         "FEHLER: To-Do-Rate muss zwischen 0 und 1 liegen.",
        "err_backflow":     "FEHLER: Backflow-Prob. muss zwischen 0 und 1 liegen.",
        "err_seed":         "FEHLER: Seed muss eine ganze Zahl sein.",
        "err_issue_types":  "FEHLER: Issue-Typen müssen im Format 'Typ:Gewicht' angegeben sein, z.B. Feature:0.6 Bug:0.3.",
        "log_started":      "--- Generierung gestartet ---",
        "log_done":         "--- Fertig ---",
        "log_error":        "FEHLER: {}",
        "dlg_workflow":     "Workflow-Datei wählen",
        "dlg_output":       "Ausgabedatei wählen",
        "tip_issue_types":  "Leer = Feature:0.6 Bug:0.3 Enabler:0.1 (Standard)",
        "tip_seed":         "Gleicher Seed → identische Ausgabe (reproduzierbar)",
    },
    _LANG_EN: {
        "title":            f"testdata_generator {_VERSION}",
        "menu_options":     "Options",
        "menu_language":    "Language",
        "menu_lang_de":     "Deutsch",
        "menu_lang_en":     "English",
        "lbl_workflow":     "Workflow File",
        "lbl_output":       "Output File (JSON)",
        "lbl_project":      "Project Key",
        "lbl_issues":       "Issue Count",
        "lbl_from_date":    "From (YYYY-MM-DD)",
        "lbl_to_date":      "To (YYYY-MM-DD)",
        "lbl_issue_types":  "Issue Types (Type:weight …)",
        "lbl_completion":   "Completion Rate (0–1)",
        "lbl_todo":         "To-Do Rate (0–1)",
        "lbl_backflow":     "Backflow Prob. (0–1)",
        "lbl_seed":         "Seed (empty = random)",
        "lbl_log":          "Log",
        "btn_browse_wf":    "Browse…",
        "btn_browse_out":   "Browse…",
        "btn_run":          "Generate",
        "err_no_workflow":  "ERROR: No workflow file selected.",
        "err_no_output":    "ERROR: No output file specified.",
        "err_issues":       "ERROR: Issue count must be a positive integer.",
        "err_completion":   "ERROR: Completion rate must be between 0 and 1.",
        "err_todo":         "ERROR: To-Do rate must be between 0 and 1.",
        "err_backflow":     "ERROR: Backflow probability must be between 0 and 1.",
        "err_seed":         "ERROR: Seed must be an integer.",
        "err_issue_types":  "ERROR: Issue types must be in 'Type:weight' format, e.g. Feature:0.6 Bug:0.3.",
        "log_started":      "--- Generation started ---",
        "log_done":         "--- Done ---",
        "log_error":        "ERROR: {}",
        "dlg_workflow":     "Select workflow file",
        "dlg_output":       "Select output file",
        "tip_issue_types":  "Empty = Feature:0.6 Bug:0.3 Enabler:0.1 (default)",
        "tip_seed":         "Same seed → identical output (reproducible)",
    },
}


class _App:
    """Main application window for testdata_generator GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._lang = _LANG_DE
        self._running = False

        self._var_workflow = tk.StringVar()
        self._var_output = tk.StringVar()
        self._var_project = tk.StringVar(value="TEST")
        self._var_issues = tk.StringVar(value="100")
        self._var_from_date = tk.StringVar(value="2025-01-01")
        self._var_to_date = tk.StringVar(value="2025-12-31")
        self._var_issue_types = tk.StringVar()
        self._var_completion = tk.StringVar(value="0.7")
        self._var_todo = tk.StringVar(value="0.15")
        self._var_backflow = tk.StringVar(value="0.1")
        self._var_seed = tk.StringVar()

        self._build_menu()
        self._build_form()
        self._build_log()
        self._apply_lang()

    def _t(self, key: str) -> str:
        return _T[self._lang].get(key, key)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self._root)
        self._menu_options = tk.Menu(menubar, tearoff=False)
        self._menu_language = tk.Menu(self._menu_options, tearoff=False)
        self._menu_language.add_command(
            label="Deutsch", command=lambda: self._set_lang(_LANG_DE)
        )
        self._menu_language.add_command(
            label="English", command=lambda: self._set_lang(_LANG_EN)
        )
        self._menu_options.add_cascade(label="Language / Sprache", menu=self._menu_language)
        menubar.add_cascade(label="Optionen / Options", menu=self._menu_options)
        self._root.config(menu=menubar)

    def _build_form(self) -> None:
        frame = ttk.Frame(self._root, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        def row(r: int, lbl_key: str, var: tk.StringVar, browse_cmd=None, tip: str = "") -> None:
            lbl = ttk.Label(frame, text="")
            lbl.grid(row=r, column=0, sticky="w", pady=2)
            self._labels[lbl_key] = lbl
            entry = ttk.Entry(frame, textvariable=var, width=48)
            entry.grid(row=r, column=1, sticky="ew", padx=(4, 0))
            if tip:
                entry.insert(0, "")
                entry.configure()
            if browse_cmd:
                btn = ttk.Button(frame, text="…", width=4, command=browse_cmd)
                btn.grid(row=r, column=2, padx=(2, 0))

        frame.columnconfigure(1, weight=1)
        self._labels: dict[str, ttk.Label] = {}

        row(0, "lbl_workflow", self._var_workflow, self._browse_workflow)
        row(1, "lbl_output", self._var_output, self._browse_output)
        row(2, "lbl_project", self._var_project)
        row(3, "lbl_issues", self._var_issues)
        row(4, "lbl_from_date", self._var_from_date)
        row(5, "lbl_to_date", self._var_to_date)
        row(6, "lbl_issue_types", self._var_issue_types)
        row(7, "lbl_completion", self._var_completion)
        row(8, "lbl_todo", self._var_todo)
        row(9, "lbl_backflow", self._var_backflow)
        row(10, "lbl_seed", self._var_seed)

        self._btn_run = ttk.Button(frame, text="Generate", command=self._run)
        self._btn_run.grid(row=11, column=0, columnspan=3, pady=(10, 4))

        self._progress = ttk.Progressbar(frame, mode="indeterminate")
        self._progress.grid(row=12, column=0, columnspan=3, sticky="ew")
        self._progress.grid_remove()

    def _build_log(self) -> None:
        log_frame = ttk.LabelFrame(self._root, text="Log", padding=4)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log_frame = log_frame
        self._log = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", wrap="word")
        self._log.grid(row=0, column=0, sticky="nsew")

    def _apply_lang(self) -> None:
        self._root.title(self._t("title"))
        for key, lbl in self._labels.items():
            lbl.configure(text=self._t(key))
        self._btn_run.configure(text=self._t("btn_run"))
        self._log_frame.configure(text=self._t("lbl_log"))

    def _set_lang(self, lang: str) -> None:
        self._lang = lang
        self._apply_lang()

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

    def _log_msg(self, msg: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

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

    def _run(self) -> None:
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

        try:
            completion_rate = float(self._var_completion.get())
            assert 0.0 <= completion_rate <= 1.0
        except (ValueError, AssertionError):
            self._log_msg(self._t("err_completion"))
            return

        try:
            todo_rate = float(self._var_todo.get())
            assert 0.0 <= todo_rate <= 1.0
        except (ValueError, AssertionError):
            self._log_msg(self._t("err_todo"))
            return

        try:
            backflow_prob = float(self._var_backflow.get())
            assert 0.0 <= backflow_prob <= 1.0
        except (ValueError, AssertionError):
            self._log_msg(self._t("err_backflow"))
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

        self._running = True
        self._btn_run.configure(state="disabled")
        self._log_msg(self._t("log_started"))

        _progress_timer: list = []

        def show_progress():
            self._progress.grid()
            self._progress.start(10)

        _progress_timer.append(self._root.after(3000, show_progress))

        def _do():
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
                    log=self._log_msg,
                )
                self._root.after(0, lambda: self._log_msg(self._t("log_done")))
            except Exception as exc:
                self._root.after(0, lambda: self._log_msg(self._t("log_error").format(exc)))
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


def main() -> None:
    """Launch the testdata_generator GUI."""
    root = tk.Tk()
    root.resizable(True, True)
    root.minsize(520, 400)
    app = _App(root)  # noqa: F841
    root.mainloop()
