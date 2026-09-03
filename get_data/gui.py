# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       03.09.2026
# Geändert:       03.09.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Oberfläche für get_data (Roadmap C3) mit BEIDEN
#   Erhebungswegen als umschaltbare Modi: „Jira REST-Abruf" (URL, Projekt/
#   JQL, API-Version, Auth, Token — nur im Speicher, nie persistiert) und
#   „Vorhandener Export" (JSON-Datei prüfen: Pflichtfelder, Changelog,
#   fehlende Folgeseiten). Der Export-Weg bleibt bewusst gleichwertig —
#   API-Freigaben können in großen Organisationen lange dauern. Abruf und
#   Prüfung laufen im Hintergrund-Thread; Ergebnisse erscheinen im Log.
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

from .client import (
    API_V2,
    API_V3,
    AUTH_BEARER,
    AUTH_CLOUD,
    JiraConfig,
    fetch_to_file,
)
from .validate import validate_export_file

LANG_DE = "de"
LANG_EN = "en"
_LANG_ORDER = [LANG_DE, LANG_EN]

_MANUAL_URLS = {
    LANG_DE: "https://jaegerfeld.github.io/situation-report/get_data_Benutzerhandbuch.pdf",
    LANG_EN: "https://jaegerfeld.github.io/situation-report/get_data_UserManual.pdf",
}

_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

MODE_REST = "rest"
MODE_EXPORT = "export"


def _load_lang_pref() -> str:
    """Load the shared language preference, defaulting to English."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _T else LANG_EN
    except Exception:
        return LANG_EN


_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "title": f"get_data {_VERSION}",
        "menu_help": "Hilfe",
        "menu_manual": "Manual",
        "lbl_mode": "Erhebungsweg",
        "mode_rest": "Jira REST-Abruf",
        "mode_export": "Vorhandener Export (JSON)",
        "lbl_url": "Jira-URL",
        "lbl_project": "Projekt-Key",
        "lbl_jql": "JQL (optional, ersetzt Projekt)",
        "lbl_api": "API-Version",
        "lbl_auth": "Anmeldung",
        "auth_cloud": "Cloud (E-Mail + API-Token)",
        "auth_bearer": "Server/DC (Bearer-PAT)",
        "lbl_email": "E-Mail (bei Cloud)",
        "lbl_token": "API-Token (wird nicht gespeichert)",
        "lbl_output": "Ausgabedatei (JSON)",
        "btn_browse": "…",
        "btn_fetch": "Abrufen",
        "lbl_export_file": "Export-Datei (JSON)",
        "btn_check": "Prüfen",
        "lbl_log": "Log",
        "log_fetch_started": "--- Jira-Abruf gestartet ---",
        "log_fetch_done": "--- Fertig: {} Issues → {} ---",
        "log_check_started": "--- Export wird geprüft ---",
        "log_check_ok": "OK: {} Issues, bereit für transform_data.",
        "log_check_failed": "Export NICHT verwendbar — Fehler siehe oben.",
        "log_error": "FEHLER: {}",
        "err_no_token": "FEHLER: Bitte ein API-Token eingeben.",
        "err_no_output": "FEHLER: Keine Ausgabedatei angegeben.",
        "err_no_file": "FEHLER: Keine Export-Datei gewählt.",
        "dlg_output": "Ausgabedatei wählen",
        "dlg_export": "Export-Datei wählen",
        "hint_paths": "Beide Wege liefern dasselbe JSON für transform_data — "
                      "der manuelle Export bleibt gleichwertig (Manual Kap. 1).",
    },
    LANG_EN: {
        "title": f"get_data {_VERSION}",
        "menu_help": "Help",
        "menu_manual": "Manual",
        "lbl_mode": "Acquisition path",
        "mode_rest": "Jira REST fetch",
        "mode_export": "Existing export (JSON)",
        "lbl_url": "Jira URL",
        "lbl_project": "Project key",
        "lbl_jql": "JQL (optional, overrides project)",
        "lbl_api": "API version",
        "lbl_auth": "Authentication",
        "auth_cloud": "Cloud (e-mail + API token)",
        "auth_bearer": "Server/DC (bearer PAT)",
        "lbl_email": "E-mail (for cloud)",
        "lbl_token": "API token (never stored)",
        "lbl_output": "Output file (JSON)",
        "btn_browse": "…",
        "btn_fetch": "Fetch",
        "lbl_export_file": "Export file (JSON)",
        "btn_check": "Check",
        "lbl_log": "Log",
        "log_fetch_started": "--- Jira fetch started ---",
        "log_fetch_done": "--- Done: {} issues → {} ---",
        "log_check_started": "--- Checking export ---",
        "log_check_ok": "OK: {} issues, ready for transform_data.",
        "log_check_failed": "Export NOT usable — see errors above.",
        "log_error": "ERROR: {}",
        "err_no_token": "ERROR: Please enter an API token.",
        "err_no_output": "ERROR: No output file specified.",
        "err_no_file": "ERROR: No export file selected.",
        "dlg_output": "Select output file",
        "dlg_export": "Select export file",
        "hint_paths": "Both paths yield the same JSON for transform_data — "
                      "the manual export stays a first-class option "
                      "(manual, ch. 1).",
    },
}


class _App:
    """Main window for get_data: two acquisition paths, one artifact."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._running = False

        self._var_mode = tk.StringVar(value=MODE_REST)
        self._var_url = tk.StringVar()
        self._var_project = tk.StringVar()
        self._var_jql = tk.StringVar()
        self._var_api = tk.StringVar(value=API_V3)
        self._var_auth = tk.StringVar(value=AUTH_CLOUD)
        self._var_email = tk.StringVar()
        self._var_token = tk.StringVar()
        self._var_output = tk.StringVar()
        self._var_export = tk.StringVar()
        self._lang_var = tk.StringVar(value=_load_lang_pref())

        self._labels: dict[str, ttk.Label] = {}
        self._build_ui()
        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._apply_language()
        self._on_mode_change()

    def _t(self, key: str) -> str:
        return _T.get(self._lang_var.get(), _T[LANG_EN]).get(key, key)

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self._root.minsize(560, 520)
        menubar = tk.Menu(self._root)
        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Manual", command=self._open_manual)
        self._root.config(menu=menubar)
        self._menubar = menubar
        self._help_menu = help_menu

        frame = ttk.Frame(self._root, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)
        frame.columnconfigure(1, weight=1)
        self._frame = frame

        lbl_mode = ttk.Label(frame, text="")
        lbl_mode.grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._labels["lbl_mode"] = lbl_mode
        mode_f = ttk.Frame(frame)
        mode_f.grid(row=0, column=1, columnspan=2, sticky="w", pady=(0, 4))
        self._rb_rest = ttk.Radiobutton(
            mode_f, text="", variable=self._var_mode, value=MODE_REST,
            command=self._on_mode_change)
        self._rb_rest.pack(side="left", padx=(0, 12))
        self._rb_export = ttk.Radiobutton(
            mode_f, text="", variable=self._var_mode, value=MODE_EXPORT,
            command=self._on_mode_change)
        self._rb_export.pack(side="left")

        self._hint = ttk.Label(frame, text="", foreground="#555555",
                               wraplength=520, justify="left")
        self._hint.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 6))

        # ── REST frame ────────────────────────────────────────────────────
        rest = ttk.LabelFrame(frame, text="", padding=8)
        rest.grid(row=2, column=0, columnspan=3, sticky="ew")
        rest.columnconfigure(1, weight=1)
        self._rest_frame = rest

        def rest_row(r: int, key: str, var: tk.StringVar, secret: bool = False,
                     browse=None) -> None:
            lbl = ttk.Label(rest, text="")
            lbl.grid(row=r, column=0, sticky="w", pady=2)
            self._labels[key] = lbl
            entry = ttk.Entry(rest, textvariable=var, width=44,
                              show="•" if secret else "")
            entry.grid(row=r, column=1, sticky="ew", padx=(4, 0))
            if browse:
                ttk.Button(rest, text="…", width=4, command=browse).grid(
                    row=r, column=2, padx=(2, 0))

        rest_row(0, "lbl_url", self._var_url)
        rest_row(1, "lbl_project", self._var_project)
        rest_row(2, "lbl_jql", self._var_jql)

        lbl_api = ttk.Label(rest, text="")
        lbl_api.grid(row=3, column=0, sticky="w", pady=2)
        self._labels["lbl_api"] = lbl_api
        api_f = ttk.Frame(rest)
        api_f.grid(row=3, column=1, sticky="w", padx=(4, 0))
        ttk.Radiobutton(api_f, text="v3", variable=self._var_api,
                        value=API_V3).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(api_f, text="v2", variable=self._var_api,
                        value=API_V2).pack(side="left")

        lbl_auth = ttk.Label(rest, text="")
        lbl_auth.grid(row=4, column=0, sticky="w", pady=2)
        self._labels["lbl_auth"] = lbl_auth
        auth_f = ttk.Frame(rest)
        auth_f.grid(row=4, column=1, sticky="w", padx=(4, 0))
        self._rb_cloud = ttk.Radiobutton(
            auth_f, text="", variable=self._var_auth, value=AUTH_CLOUD)
        self._rb_cloud.pack(side="left", padx=(0, 10))
        self._rb_bearer = ttk.Radiobutton(
            auth_f, text="", variable=self._var_auth, value=AUTH_BEARER)
        self._rb_bearer.pack(side="left")

        rest_row(5, "lbl_email", self._var_email)
        rest_row(6, "lbl_token", self._var_token, secret=True)
        rest_row(7, "lbl_output", self._var_output, browse=self._browse_output)

        self._btn_fetch = ttk.Button(rest, text="", command=self._fetch)
        self._btn_fetch.grid(row=8, column=0, columnspan=3, pady=(8, 2))

        # ── Export frame ──────────────────────────────────────────────────
        exp = ttk.LabelFrame(frame, text="", padding=8)
        exp.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        exp.columnconfigure(1, weight=1)
        self._export_frame = exp

        lbl_exp = ttk.Label(exp, text="")
        lbl_exp.grid(row=0, column=0, sticky="w", pady=2)
        self._labels["lbl_export_file"] = lbl_exp
        ttk.Entry(exp, textvariable=self._var_export, width=44).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(exp, text="…", width=4, command=self._browse_export).grid(
            row=0, column=2, padx=(2, 0))
        self._btn_check = ttk.Button(exp, text="", command=self._check)
        self._btn_check.grid(row=1, column=0, columnspan=3, pady=(8, 2))

        self._progress = ttk.Progressbar(frame, mode="indeterminate")
        self._progress.grid(row=4, column=0, columnspan=3, sticky="ew",
                            pady=(6, 0))
        self._progress.grid_remove()

        log_frame = ttk.LabelFrame(self._root, text="Log", padding=4)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self._log_frame = log_frame
        self._log_widget = scrolledtext.ScrolledText(
            log_frame, height=10, state="disabled", wrap="word")
        self._log_widget.grid(row=0, column=0, sticky="nsew")

    def _apply_language(self) -> None:
        self._root.title(self._t("title"))
        for key, lbl in self._labels.items():
            lbl.configure(text=self._t(key))
        self._rb_rest.configure(text=self._t("mode_rest"))
        self._rb_export.configure(text=self._t("mode_export"))
        self._rb_cloud.configure(text=self._t("auth_cloud"))
        self._rb_bearer.configure(text=self._t("auth_bearer"))
        self._rest_frame.configure(text=self._t("mode_rest"))
        self._export_frame.configure(text=self._t("mode_export"))
        self._btn_fetch.configure(text=self._t("btn_fetch"))
        self._btn_check.configure(text=self._t("btn_check"))
        self._log_frame.configure(text=self._t("lbl_log"))
        self._hint.configure(text=self._t("hint_paths"))
        self._menubar.entryconfigure(1, label=self._t("menu_help"))
        self._help_menu.entryconfigure(0, label=self._t("menu_manual"))

    def _on_mode_change(self) -> None:
        """Show only the frame of the selected acquisition path."""
        if self._var_mode.get() == MODE_REST:
            self._rest_frame.grid()
            self._export_frame.grid_remove()
        else:
            self._rest_frame.grid_remove()
            self._export_frame.grid()

    def _open_manual(self) -> None:
        webbrowser.open(_MANUAL_URLS.get(self._lang_var.get(),
                                         _MANUAL_URLS[LANG_EN]))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title=self._t("dlg_output"), defaultextension=".json",
            filetypes=[("JSON", "*.json")])
        if path:
            self._var_output.set(path)

    def _browse_export(self) -> None:
        path = filedialog.askopenfilename(
            title=self._t("dlg_export"),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self._var_export.set(path)

    def _log_msg(self, msg: str) -> None:
        self._log_widget.configure(state="normal")
        self._log_widget.insert("end", msg + "\n")
        self._log_widget.see("end")
        self._log_widget.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        self._btn_fetch.configure(state=state)
        self._btn_check.configure(state=state)
        if running:
            self._progress.grid()
            self._progress.start(10)
        else:
            self._progress.stop()
            self._progress.grid_remove()

    # ── Actions ───────────────────────────────────────────────────────────
    def _fetch(self) -> None:
        """Run the REST fetch in a background thread."""
        if self._running:
            return
        if not self._var_token.get():
            self._log_msg(self._t("err_no_token"))
            return
        output = self._var_output.get().strip()
        if not output:
            self._log_msg(self._t("err_no_output"))
            return
        config = JiraConfig(
            base_url=self._var_url.get().strip(),
            token=self._var_token.get(),
            project=self._var_project.get().strip(),
            jql=self._var_jql.get().strip(),
            api_version=self._var_api.get(),
            auth_mode=self._var_auth.get(),
            email=self._var_email.get().strip(),
        )
        self._set_running(True)
        self._log_msg(self._t("log_fetch_started"))

        def _do() -> None:
            try:
                count = fetch_to_file(config, Path(output), log=self._log_msg)
                done = self._t("log_fetch_done").format(count, output)
                self._root.after(0, lambda: self._log_msg(done))
            except (ValueError, RuntimeError) as exc:
                msg = self._t("log_error").format(exc)
                self._root.after(0, lambda: self._log_msg(msg))
            finally:
                self._root.after(0, lambda: self._set_running(False))

        threading.Thread(target=_do, daemon=True).start()

    def _check(self) -> None:
        """Validate the selected export file in a background thread."""
        if self._running:
            return
        export = self._var_export.get().strip()
        if not export:
            self._log_msg(self._t("err_no_file"))
            return
        self._set_running(True)
        self._log_msg(self._t("log_check_started"))

        def _do() -> None:
            check = validate_export_file(Path(export))

            def report() -> None:
                for warning in check.warnings:
                    self._log_msg(f"WARNUNG: {warning}"
                                  if self._lang_var.get() == LANG_DE
                                  else f"WARNING: {warning}")
                for error in check.errors:
                    self._log_msg(self._t("log_error").format(error))
                if check.ok:
                    self._log_msg(
                        self._t("log_check_ok").format(check.issue_count))
                else:
                    self._log_msg(self._t("log_check_failed"))
                self._set_running(False)

            self._root.after(0, report)

        threading.Thread(target=_do, daemon=True).start()


def main() -> None:  # pragma: no cover - requires a display
    """Launch the get_data GUI."""
    root = tk.Tk()
    root.resizable(True, True)
    _App(root)
    root.mainloop()
