# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       03.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für den JSON Merger im helper-Modul.
#   Erlaubt das Hinzufügen mehrerer Jira-JSON-Dateien über einen Datei-Dialog,
#   wählt eine Ausgabedatei und startet das Zusammenführen per Knopfdruck.
#   Die Verarbeitung läuft in einem separaten Thread; bei Operationen über
#   3 Sekunden erscheint ein Ladebalken. Ergebnisse und Warnungen werden im
#   Log-Bereich angezeigt.
# =============================================================================

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

try:
    from version import __version__ as _VERSION
except ImportError:
    _VERSION = "?"

from .cli import run_merge

_LANG_DE = "de"
_LANG_EN = "en"

_T: dict[str, dict[str, str]] = {
    _LANG_DE: {
        "title":           f"helper – JSON Merger  {_VERSION}",
        "menu_options":    "Optionen",
        "menu_language":   "Sprache",
        "lbl_inputs":      "Eingabedateien",
        "btn_add":         "Hinzufügen…",
        "btn_remove":      "Entfernen",
        "lbl_output":      "Ausgabedatei (JSON)",
        "btn_browse":      "Durchsuchen…",
        "lbl_dedup":       "Duplikate entfernen (nach Issue-ID)",
        "btn_run":         "Zusammenführen",
        "lbl_log":         "Log",
        "err_no_inputs":   "FEHLER: Mindestens eine Eingabedatei erforderlich.",
        "err_no_output":   "FEHLER: Keine Ausgabedatei angegeben.",
        "log_started":     "--- Zusammenführen gestartet ---",
        "log_done":        "--- Fertig ---",
        "log_error":       "FEHLER: {}",
        "dlg_add":         "JSON-Dateien hinzufügen",
        "dlg_output":      "Ausgabedatei wählen",
    },
    _LANG_EN: {
        "title":           f"helper – JSON Merger  {_VERSION}",
        "menu_options":    "Options",
        "menu_language":   "Language",
        "lbl_inputs":      "Input files",
        "btn_add":         "Add…",
        "btn_remove":      "Remove",
        "lbl_output":      "Output file (JSON)",
        "btn_browse":      "Browse…",
        "lbl_dedup":       "Remove duplicates (by issue id)",
        "btn_run":         "Merge",
        "lbl_log":         "Log",
        "err_no_inputs":   "ERROR: At least one input file is required.",
        "err_no_output":   "ERROR: No output file specified.",
        "log_started":     "--- Merge started ---",
        "log_done":        "--- Done ---",
        "log_error":       "ERROR: {}",
        "dlg_add":         "Add JSON files",
        "dlg_output":      "Select output file",
    },
}


class _App:
    """Main application window for the helper JSON Merger GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._lang = _LANG_DE
        self._running = False
        self._var_output = tk.StringVar()
        self._var_dedup = tk.BooleanVar(value=True)
        self._labels: dict[str, tk.Widget] = {}

        self._build_menu()
        self._build_form()
        self._build_log()
        self._apply_lang()

    def _t(self, key: str) -> str:
        """Look up a translation key for the current language."""
        return _T[self._lang].get(key, key)

    def _build_menu(self) -> None:
        """Build the Options → Language menu."""
        menubar = tk.Menu(self._root)
        self._menu_options = tk.Menu(menubar, tearoff=False)
        lang_menu = tk.Menu(self._menu_options, tearoff=False)
        lang_menu.add_command(label="Deutsch", command=lambda: self._set_lang(_LANG_DE))
        lang_menu.add_command(label="English", command=lambda: self._set_lang(_LANG_EN))
        self._menu_options.add_cascade(label="Language / Sprache", menu=lang_menu)
        menubar.add_cascade(label="Optionen / Options", menu=self._menu_options)
        self._root.config(menu=menubar)

    def _build_form(self) -> None:
        """Build the input file list, output path, dedup checkbox, and run button."""
        outer = ttk.Frame(self._root, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        # --- Input files ---
        lbl_inputs = ttk.Label(outer, text="")
        lbl_inputs.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._labels["lbl_inputs"] = lbl_inputs

        list_frame = ttk.Frame(outer)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        self._listbox = tk.Listbox(list_frame, height=6, selectmode="extended")
        self._listbox.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb.set)

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=2, column=0, sticky="w", pady=(0, 8))
        self._btn_add = ttk.Button(btn_frame, text="", command=self._add_files)
        self._btn_add.pack(side="left", padx=(0, 4))
        self._btn_remove = ttk.Button(btn_frame, text="", command=self._remove_selected)
        self._btn_remove.pack(side="left")
        self._labels["btn_add"] = self._btn_add
        self._labels["btn_remove"] = self._btn_remove

        # --- Output file ---
        lbl_output = ttk.Label(outer, text="")
        lbl_output.grid(row=3, column=0, sticky="w", pady=(0, 2))
        self._labels["lbl_output"] = lbl_output

        out_frame = ttk.Frame(outer)
        out_frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        out_frame.columnconfigure(0, weight=1)
        ttk.Entry(out_frame, textvariable=self._var_output).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        self._btn_browse = ttk.Button(out_frame, text="", command=self._browse_output)
        self._btn_browse.grid(row=0, column=1)
        self._labels["btn_browse"] = self._btn_browse

        # --- Dedup checkbox ---
        self._chk_dedup = ttk.Checkbutton(outer, variable=self._var_dedup, text="")
        self._chk_dedup.grid(row=5, column=0, sticky="w", pady=(0, 8))
        self._labels["lbl_dedup"] = self._chk_dedup

        # --- Run button + progress bar ---
        self._btn_run = ttk.Button(outer, text="", command=self._run)
        self._btn_run.grid(row=6, column=0, pady=(0, 4))
        self._labels["btn_run"] = self._btn_run

        self._progress = ttk.Progressbar(outer, mode="indeterminate")
        self._progress.grid(row=7, column=0, sticky="ew")
        self._progress.grid_remove()

    def _build_log(self) -> None:
        """Build the scrollable log area."""
        log_frame = ttk.LabelFrame(self._root, text="Log", padding=4)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log_frame = log_frame
        self._log = scrolledtext.ScrolledText(
            log_frame, height=10, state="disabled", wrap="word"
        )
        self._log.grid(row=0, column=0, sticky="nsew")

    def _apply_lang(self) -> None:
        """Update all translatable widgets for the current language."""
        self._root.title(self._t("title"))
        self._log_frame.configure(text=self._t("lbl_log"))
        for key, widget in self._labels.items():
            text = self._t(key)
            if hasattr(widget, "configure"):
                widget.configure(text=text)

    def _set_lang(self, lang: str) -> None:
        self._lang = lang
        self._apply_lang()

    def _add_files(self) -> None:
        """Open a multi-file dialog and add selected JSON files to the list."""
        paths = filedialog.askopenfilenames(
            title=self._t("dlg_add"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        existing = set(self._listbox.get(0, "end"))
        for p in paths:
            if p not in existing:
                self._listbox.insert("end", p)
                existing.add(p)
        if paths and not self._var_output.get():
            first = Path(paths[0])
            self._var_output.set(str(first.parent / "merged.json"))

    def _remove_selected(self) -> None:
        """Remove selected entries from the input file list."""
        for idx in reversed(self._listbox.curselection()):
            self._listbox.delete(idx)

    def _browse_output(self) -> None:
        """Open a save-file dialog and set the output path."""
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_output"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._var_output.set(path)

    def _log_msg(self, msg: str) -> None:
        """Append a line to the log area (thread-safe via after())."""
        def _append():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self._root.after(0, _append)

    def _run(self) -> None:
        """Validate inputs and start the merge in a background thread."""
        if self._running:
            return

        input_paths = [Path(p) for p in self._listbox.get(0, "end")]
        output_str = self._var_output.get().strip()

        if not input_paths:
            self._log_msg(self._t("err_no_inputs"))
            return
        if not output_str:
            self._log_msg(self._t("err_no_output"))
            return

        self._running = True
        self._btn_run.configure(state="disabled")
        self._log_msg(self._t("log_started"))

        _progress_timer: list = []
        _progress_timer.append(
            self._root.after(3000, lambda: (self._progress.grid(), self._progress.start(10)))
        )

        def _do() -> None:
            try:
                run_merge(
                    inputs=input_paths,
                    output=Path(output_str),
                    deduplicate=self._var_dedup.get(),
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
        """Re-enable the run button and hide the progress bar."""
        self._running = False
        self._btn_run.configure(state="normal")
        self._progress.stop()
        self._progress.grid_remove()


def main() -> None:
    """Launch the helper JSON Merger GUI."""
    root = tk.Tk()
    root.resizable(True, True)
    root.minsize(500, 420)
    _App(root)
    root.mainloop()
