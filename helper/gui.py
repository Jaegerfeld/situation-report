# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.05.2026
# Geändert:       09.05.2026
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

import json
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

from .cli import run_merge

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]

_MANUAL_URLS: dict[str, str] = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/helper_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/helper_UserManual.pdf",
    LANG_RO: "https://jaegerfeld.github.io/situation-report/helper_UserManual.pdf",
    LANG_PT: "https://jaegerfeld.github.io/situation-report/helper_UserManual.pdf",
    LANG_FR: "https://jaegerfeld.github.io/situation-report/helper_UserManual.pdf",
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


_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "title":           f"helper – JSON Merger  {_VERSION}",
        "menu_help":       "Hilfe",
        "menu_manual":     "Manual",
        "menu_template":   "Templates",
        "menu_tpl_save":   "Speichern…",
        "menu_tpl_load":   "Laden…",
        "dlg_tpl_save":    "Template speichern",
        "dlg_tpl_load":    "Template laden",
        "log_tpl_saved":   "Template gespeichert: {}",
        "log_tpl_loaded":  "Template geladen: {}",
        "log_tpl_error":   "Fehler beim Template: {}",
        "log_tpl_missing": "Hinweis: Datei aus Template nicht gefunden: {}",
        "tip_language":    "Sprache wechseln",
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
    LANG_EN: {
        "title":           f"helper – JSON Merger  {_VERSION}",
        "menu_help":       "Help",
        "menu_manual":     "Manual",
        "menu_template":   "Templates",
        "menu_tpl_save":   "Save…",
        "menu_tpl_load":   "Load…",
        "dlg_tpl_save":    "Save Template",
        "dlg_tpl_load":    "Load Template",
        "log_tpl_saved":   "Template saved: {}",
        "log_tpl_loaded":  "Template loaded: {}",
        "log_tpl_error":   "Template error: {}",
        "log_tpl_missing": "Note: file from template not found: {}",
        "tip_language":    "Change language",
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


def _build_template_section(
    inputs: list[str], output: str, dedup: bool
) -> dict:
    """Assemble the helper section for the shared project template."""
    return {"inputs": list(inputs), "output": output, "dedup": bool(dedup)}


def _parse_template_section(data: dict) -> dict:
    """Normalise a helper template section; missing keys → sensible defaults."""
    raw_inputs = data.get("inputs", [])
    inputs = [str(p) for p in raw_inputs] if isinstance(raw_inputs, list) else []
    return {
        "inputs": inputs,
        "output": str(data.get("output", "")),
        "dedup": bool(data.get("dedup", True)),
    }


class _App:
    """Main application window for the helper JSON Merger GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._running = False
        self._var_output = tk.StringVar()
        self._var_dedup = tk.BooleanVar(value=True)
        self._labels: dict[str, tk.Widget] = {}
        self._lang_var = tk.StringVar(value=_load_lang_pref())
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._create_flag_imgs()

        self._build_menu()
        self._build_form()
        self._build_log()
        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._apply_language()

    def _t(self, key: str) -> str:
        """Look up a translation key for the current language."""
        return _T.get(self._lang_var.get(), _T[LANG_EN]).get(key, key)

    def _build_menu(self) -> None:
        """Build (or rebuild) the top menu bar with Help → Manual."""
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
        """Build the input file list, output path, dedup checkbox, and run button."""
        outer = ttk.Frame(self._root, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, minsize=44)

        self._flag_btn = tk.Button(
            outer,
            image=self._flag_imgs[self._lang_var.get()],
            command=self._toggle_language,
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=4,
            pady=2,
        )
        self._flag_btn.grid(row=0, column=1, sticky="ne", rowspan=4, padx=(2, 0))

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

    def _apply_language(self) -> None:
        """Update all translatable widgets for the current language."""
        _save_lang_pref(self._lang_var.get())
        self._root.title(self._t("title"))
        self._flag_btn.configure(image=self._flag_imgs[self._lang_var.get()])
        self._log_frame.configure(text=self._t("lbl_log"))
        for key, widget in self._labels.items():
            text = self._t(key)
            if hasattr(widget, "configure"):
                widget.configure(text=text)
        self._build_menu()

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

    def _save_template(self) -> None:
        """Write the current input list/output/dedup as this module's template section."""
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_tpl_save"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            section = _build_template_section(
                inputs=list(self._listbox.get(0, "end")),
                output=self._var_output.get(),
                dedup=self._var_dedup.get(),
            )
            project_template.save_template(
                Path(path),
                project_template.MODULE_HELPER,
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
                    envelope, project_template.MODULE_HELPER
                )
            )
        except Exception as exc:
            self._log_msg(self._t("log_tpl_error").format(exc))
            return

        self._listbox.delete(0, "end")
        for p in section["inputs"]:
            self._listbox.insert("end", p)
            if p and not Path(p).is_file():
                self._log_msg(self._t("log_tpl_missing").format(p))
        self._var_output.set(section["output"])
        self._var_dedup.set(section["dedup"])

        self._lang_var.set(envelope.get("language", self._lang_var.get()))
        self._log_msg(self._t("log_tpl_loaded").format(Path(path).name))

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
                msg = self._t("log_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
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
