# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       16.04.2026
# Geändert:       16.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für build_reports. Ermöglicht die
#   Auswahl von IssueTimes- und CFD-XLSX, optionale Filter (Datum, Projekte,
#   Issuetypen), Metrik-Auswahl (Checkboxen) sowie CT-Methode (A/B). Sprache
#   (DE/EN) und Terminologie (SAFe/Global) werden über ein Optionsmenü gewählt.
#   Die Berechnung läuft in einem separaten Thread, sodass die Oberfläche
#   reaktionsfähig bleibt.
# =============================================================================

from __future__ import annotations

import tempfile
import threading
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import Any

from .cli import run_reports
from .metrics import all_metrics
from .metrics.flow_time import CT_METHOD_A, CT_METHOD_B, FlowTimeMetric
from .terminology import GLOBAL, SAFE, term

# ---------------------------------------------------------------------------
# Language constants
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"

# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title":      "build_reports",
        "menu_options":      "Optionen",
        "menu_language":     "Sprache",
        "menu_lang_de":      "Deutsch",
        "menu_lang_en":      "English",
        "menu_terminology":  "Terminologie",
        "sec_files":         "Dateien",
        "sec_filter":        "Filter",
        "sec_metrics":       "Metriken",
        "sec_ct":            "CT-Methode (Flow Time)",
        "lbl_issue_times":   "IssueTimes",
        "lbl_cfd":           "CFD (optional)",
        "lbl_from":          "Von (YYYY-MM-DD)",
        "lbl_to":            "Bis (YYYY-MM-DD)",
        "lbl_projects":      "Projekte",
        "lbl_issuetypes":    "Issuetypen",
        "btn_browse":        "Durchsuchen\u2026",
        "btn_all":           "Alle",
        "btn_none":          "Keine",
        "btn_show":          "Anzeigen im Browser",
        "btn_pdf":           "Als PDF speichern",
        "hint_csv":          "kommagetrennt",
        "lbl_log":           "Log",
        "ct_a":              "A \u2013 Kalendertage (Closed Date \u2212 First Date)",
        "ct_b":              "B \u2013 Stage-Minuten (First bis Closed, exkl.)",
        "dlg_issue_times":   "IssueTimes-Datei w\u00e4hlen",
        "dlg_cfd":           "CFD-Datei w\u00e4hlen",
        "dlg_pdf":           "PDF speichern unter",
        "err_no_file":       "FEHLER: Keine IssueTimes-Datei ausgew\u00e4hlt.",
        "err_not_found":     "FEHLER: Datei nicht gefunden: {}",
        "err_from_date":     "FEHLER: Ung\u00fcltiges Von-Datum '{}' (erwartet YYYY-MM-DD).",
        "err_to_date":       "FEHLER: Ung\u00fcltiges Bis-Datum '{}' (erwartet YYYY-MM-DD).",
        "log_started":       "--- Berechnung gestartet ---",
        "log_done":          "--- Fertig ---",
        "log_pdf_started":   "--- PDF-Export gestartet ---",
        "log_no_figs":       "Keine Diagramme erzeugt.",
        "log_figs_opened":   "  \u2192 {} Diagramm(e) im Browser ge\u00f6ffnet.",
        "log_unk_metric":    "  WARNING: Unbekannte Metrik '{}' \u2014 \u00fcbersprungen.",
        "log_error":         "FEHLER: {}",
    },
    LANG_EN: {
        "window_title":      "build_reports",
        "menu_options":      "Options",
        "menu_language":     "Language",
        "menu_lang_de":      "Deutsch",
        "menu_lang_en":      "English",
        "menu_terminology":  "Terminology",
        "sec_files":         "Files",
        "sec_filter":        "Filter",
        "sec_metrics":       "Metrics",
        "sec_ct":            "CT Method (Flow Time)",
        "lbl_issue_times":   "IssueTimes",
        "lbl_cfd":           "CFD (optional)",
        "lbl_from":          "From (YYYY-MM-DD)",
        "lbl_to":            "To (YYYY-MM-DD)",
        "lbl_projects":      "Projects",
        "lbl_issuetypes":    "Issue Types",
        "btn_browse":        "Browse\u2026",
        "btn_all":           "All",
        "btn_none":          "None",
        "btn_show":          "Show in Browser",
        "btn_pdf":           "Save as PDF",
        "hint_csv":          "comma-separated",
        "lbl_log":           "Log",
        "ct_a":              "A \u2013 Calendar days (Closed Date \u2212 First Date)",
        "ct_b":              "B \u2013 Stage minutes (First to Closed, excl.)",
        "dlg_issue_times":   "Select IssueTimes file",
        "dlg_cfd":           "Select CFD file",
        "dlg_pdf":           "Save PDF as",
        "err_no_file":       "ERROR: No IssueTimes file selected.",
        "err_not_found":     "ERROR: File not found: {}",
        "err_from_date":     "ERROR: Invalid From date '{}' (expected YYYY-MM-DD).",
        "err_to_date":       "ERROR: Invalid To date '{}' (expected YYYY-MM-DD).",
        "log_started":       "--- Computation started ---",
        "log_done":          "--- Done ---",
        "log_pdf_started":   "--- PDF export started ---",
        "log_no_figs":       "No figures produced.",
        "log_figs_opened":   "  \u2192 {} figure(s) opened in browser.",
        "log_unk_metric":    "  WARNING: Unknown metric '{}' \u2014 skipped.",
        "log_error":         "ERROR: {}",
    },
}


# ---------------------------------------------------------------------------
# Module-level helpers (testable without a running display)
# ---------------------------------------------------------------------------

def _parse_date_safe(value: str) -> date | None:
    """
    Parse a date string in YYYY-MM-DD format, returning None on empty input.

    Args:
        value: Date string; empty string returns None.

    Returns:
        Parsed date or None.

    Raises:
        ValueError: If the string is non-empty but not a valid ISO date.
    """
    stripped = value.strip()
    if not stripped:
        return None
    return date.fromisoformat(stripped)


def _split_csv(value: str) -> list[str]:
    """
    Split a comma-separated string into a list of non-empty, stripped items.

    Args:
        value: Comma-separated string from a GUI entry widget.

    Returns:
        List of non-empty strings.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_combined_html(figures: list) -> str:
    """
    Combine multiple plotly Figure objects into a single self-contained HTML string.

    The first figure includes the full Plotly.js CDN bundle; subsequent figures
    reuse the already-loaded library to keep file size reasonable.

    Args:
        figures: List of plotly Figure objects to embed.

    Returns:
        Complete HTML document as a string.
    """
    parts = []
    for i, fig in enumerate(figures):
        parts.append(
            fig.to_html(
                include_plotlyjs="cdn" if i == 0 else False,
                full_html=False,
                config={"responsive": True},
            )
        )
    body = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<style>body{margin:16px;font-family:sans-serif;background:#fff;}"
        "div.plotly-graph-div{margin-bottom:32px;}</style>"
        "</head>"
        f"<body>{body}</body></html>"
    )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class BuildReportsApp(tk.Tk):
    """
    Main tkinter application window for build_reports.

    Provides file selection, filter controls, metric checkboxes, CT method
    toggle, a browser preview button, and PDF export. Language (DE/EN) and
    terminology (SAFe/Global) are controlled via the Options menu. Computation
    runs in a background thread to keep the UI responsive.
    """

    def __init__(self) -> None:
        super().__init__()
        self.resizable(True, True)
        self.minsize(520, 600)

        self._plugins = all_metrics()

        # --- State variables ---
        self._lang_var = tk.StringVar(value=LANG_DE)
        self._issue_times_var = tk.StringVar()
        self._cfd_var = tk.StringVar()
        self._from_date_var = tk.StringVar()
        self._to_date_var = tk.StringVar()
        self._projects_var = tk.StringVar()
        self._issuetypes_var = tk.StringVar()
        self._terminology_var = tk.StringVar(value=SAFE)
        self._ct_method_var = tk.StringVar(value=CT_METHOD_A)
        self._metric_vars: dict[str, tk.BooleanVar] = {
            p.metric_id: tk.BooleanVar(value=True) for p in self._plugins
        }

        # Translatable widget references: list of (widget, tr_key)
        self._i18n: list[tuple[Any, str]] = []
        # Metric checkbuttons for terminology-driven label updates
        self._metric_checkbuttons: list[tuple[tk.Checkbutton, str]] = []

        # React to language / terminology changes
        self._lang_var.trace_add("write", lambda *_: self._apply_language())
        self._terminology_var.trace_add("write", lambda *_: self._apply_terminology())

        self._build_menubar()
        self._build_ui()
        self._apply_language()  # set initial titles / labels

    # -------------------------------------------------------------------------
    # Translation helper
    # -------------------------------------------------------------------------

    def _tr(self, key: str) -> str:
        """
        Return the translated string for the current language.

        Args:
            key: Translation key defined in _T.

        Returns:
            Translated string, or key itself as fallback.
        """
        return _T.get(self._lang_var.get(), _T[LANG_DE]).get(key, key)

    # -------------------------------------------------------------------------
    # Menu bar
    # -------------------------------------------------------------------------

    def _build_menubar(self) -> None:
        """Build (or rebuild) the top menu bar with Options → Language + Terminology."""
        menubar = tk.Menu(self)

        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._tr("menu_options"), menu=options_menu)

        # Language submenu
        lang_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label=self._tr("menu_language"), menu=lang_menu)
        lang_menu.add_radiobutton(
            label=self._tr("menu_lang_de"),
            variable=self._lang_var,
            value=LANG_DE,
        )
        lang_menu.add_radiobutton(
            label=self._tr("menu_lang_en"),
            variable=self._lang_var,
            value=LANG_EN,
        )

        # Terminology submenu
        options_menu.add_separator()
        options_menu.add_cascade(
            label=self._tr("menu_terminology"),
            menu=self._build_terminology_menu(options_menu),
        )

        self.config(menu=menubar)

    def _build_terminology_menu(self, parent: tk.Menu) -> tk.Menu:
        """Create and return the Terminology sub-menu."""
        term_menu = tk.Menu(parent, tearoff=0)
        term_menu.add_radiobutton(label="SAFe",   variable=self._terminology_var, value=SAFE)
        term_menu.add_radiobutton(label="Global", variable=self._terminology_var, value=GLOBAL)
        return term_menu

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build and arrange all main window widgets."""
        pad = {"padx": 8, "pady": 3}
        self.columnconfigure(1, weight=1)
        row = 0

        # --- Files ---
        row = self._section_header("sec_files", row)

        lbl = tk.Label(self, text=self._tr("lbl_issue_times"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_issue_times"))

        tk.Entry(self, textvariable=self._issue_times_var, state="readonly", width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        btn = ttk.Button(self, text=self._tr("btn_browse"), command=self._pick_issue_times)
        btn.grid(row=row, column=2, **pad)
        self._i18n.append((btn, "btn_browse"))
        row += 1

        lbl = tk.Label(self, text=self._tr("lbl_cfd"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_cfd"))

        tk.Entry(self, textvariable=self._cfd_var, state="readonly", width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        btn = ttk.Button(self, text=self._tr("btn_browse"), command=self._pick_cfd)
        btn.grid(row=row, column=2, **pad)
        self._i18n.append((btn, "btn_browse"))
        row += 1

        # --- Filter ---
        row = self._section_header("sec_filter", row)

        lbl = tk.Label(self, text=self._tr("lbl_from"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_from"))
        tk.Entry(self, textvariable=self._from_date_var, width=20).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 1

        lbl = tk.Label(self, text=self._tr("lbl_to"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_to"))
        tk.Entry(self, textvariable=self._to_date_var, width=20).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 1

        lbl = tk.Label(self, text=self._tr("lbl_projects"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_projects"))
        tk.Entry(self, textvariable=self._projects_var, width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        hint = tk.Label(self, text=self._tr("hint_csv"), fg="gray", font=("", 8))
        hint.grid(row=row, column=2, sticky="w", **pad)
        self._i18n.append((hint, "hint_csv"))
        row += 1

        lbl = tk.Label(self, text=self._tr("lbl_issuetypes"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_issuetypes"))
        tk.Entry(self, textvariable=self._issuetypes_var, width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        row += 1

        # --- Metrics ---
        row = self._section_header("sec_metrics", row)

        self._metric_checkbuttons.clear()
        for plugin in self._plugins:
            cb = tk.Checkbutton(
                self,
                text=term(plugin.metric_id, self._terminology_var.get()),
                variable=self._metric_vars[plugin.metric_id],
                anchor="w",
            )
            cb.grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=1)
            self._metric_checkbuttons.append((cb, plugin.metric_id))
            row += 1

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=16, pady=2)
        btn_all = ttk.Button(btn_frame, text=self._tr("btn_all"), width=6,
                             command=self._select_all_metrics)
        btn_all.pack(side="left", padx=2)
        self._i18n.append((btn_all, "btn_all"))
        btn_none = ttk.Button(btn_frame, text=self._tr("btn_none"), width=6,
                              command=self._deselect_all_metrics)
        btn_none.pack(side="left", padx=2)
        self._i18n.append((btn_none, "btn_none"))
        row += 1

        # --- CT Method ---
        row = self._section_header("sec_ct", row)

        ct_frame = tk.Frame(self)
        ct_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=16, pady=4)
        for value, key in [(CT_METHOD_A, "ct_a"), (CT_METHOD_B, "ct_b")]:
            rb = tk.Radiobutton(
                ct_frame,
                text=self._tr(key),
                variable=self._ct_method_var,
                value=value,
            )
            rb.pack(anchor="w", padx=8)
            self._i18n.append((rb, key))
        row += 1

        # --- Action buttons ---
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6
        )
        row += 1

        action_frame = tk.Frame(self)
        action_frame.grid(row=row, column=0, columnspan=3, pady=4)
        self._show_btn = ttk.Button(
            action_frame, text=self._tr("btn_show"), command=self._run_show
        )
        self._show_btn.pack(side="left", padx=8)
        self._i18n.append((self._show_btn, "btn_show"))
        self._pdf_btn = ttk.Button(
            action_frame, text=self._tr("btn_pdf"), command=self._run_export_pdf
        )
        self._pdf_btn.pack(side="left", padx=8)
        self._i18n.append((self._pdf_btn, "btn_pdf"))
        row += 1

        # --- Log area ---
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=4
        )
        row += 1

        lbl = tk.Label(self, text=self._tr("lbl_log"), anchor="w")
        lbl.grid(row=row, column=0, sticky="w", **pad)
        self._i18n.append((lbl, "lbl_log"))
        row += 1

        self._log_area = scrolledtext.ScrolledText(
            self, height=10, state="disabled", wrap="word"
        )
        self._log_area.grid(
            row=row, column=0, columnspan=3, sticky="nsew", **pad
        )
        self.rowconfigure(row, weight=1)

    def _section_header(self, tr_key: str, row: int) -> int:
        """Insert a labelled separator, store the Label for i18n, and return next row."""
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(8, 2)
        )
        row += 1
        lbl = tk.Label(self, text=self._tr(tr_key), font=("", 9, "bold"), anchor="w")
        lbl.grid(row=row, column=0, columnspan=3, sticky="w", padx=8)
        self._i18n.append((lbl, tr_key))
        row += 1
        return row

    # -------------------------------------------------------------------------
    # Language / terminology updates
    # -------------------------------------------------------------------------

    def _apply_language(self) -> None:
        """Update all translatable widgets and the window title."""
        self.title(self._tr("window_title"))
        for widget, key in self._i18n:
            widget.config(text=self._tr(key))
        self._build_menubar()

    def _apply_terminology(self) -> None:
        """Update metric checkbutton labels to reflect the current terminology."""
        current_term = self._terminology_var.get()
        for cb, metric_id in self._metric_checkbuttons:
            cb.config(text=term(metric_id, current_term))

    # -------------------------------------------------------------------------
    # File pickers
    # -------------------------------------------------------------------------

    def _pick_issue_times(self) -> None:
        """Open a file dialog to select the IssueTimes.xlsx file."""
        path = filedialog.askopenfilename(
            title=self._tr("dlg_issue_times"),
            filetypes=[("Excel-Dateien", "*.xlsx"), ("Alle Dateien", "*.*")],
        )
        if path:
            self._issue_times_var.set(path)

    def _pick_cfd(self) -> None:
        """Open a file dialog to select the CFD.xlsx file."""
        path = filedialog.askopenfilename(
            title=self._tr("dlg_cfd"),
            filetypes=[("Excel-Dateien", "*.xlsx"), ("Alle Dateien", "*.*")],
        )
        if path:
            self._cfd_var.set(path)

    # -------------------------------------------------------------------------
    # Metric selection helpers
    # -------------------------------------------------------------------------

    def _select_all_metrics(self) -> None:
        """Set all metric checkboxes to checked."""
        for var in self._metric_vars.values():
            var.set(True)

    def _deselect_all_metrics(self) -> None:
        """Set all metric checkboxes to unchecked."""
        for var in self._metric_vars.values():
            var.set(False)

    # -------------------------------------------------------------------------
    # Input parsing
    # -------------------------------------------------------------------------

    def _read_inputs(self) -> dict | None:
        """
        Validate and read all user inputs from the UI.

        Returns:
            Dict with keys: issue_times, cfd, from_date, to_date, projects,
            issuetypes, terminology, ct_method, metrics.
            Returns None if validation fails.
        """
        issue_times_str = self._issue_times_var.get().strip()
        if not issue_times_str:
            self._log(self._tr("err_no_file"))
            return None
        issue_times = Path(issue_times_str)
        if not issue_times.is_file():
            self._log(self._tr("err_not_found").format(issue_times))
            return None

        cfd_str = self._cfd_var.get().strip()
        cfd = Path(cfd_str) if cfd_str else None

        try:
            from_date = _parse_date_safe(self._from_date_var.get())
        except ValueError:
            self._log(self._tr("err_from_date").format(self._from_date_var.get()))
            return None

        try:
            to_date = _parse_date_safe(self._to_date_var.get())
        except ValueError:
            self._log(self._tr("err_to_date").format(self._to_date_var.get()))
            return None

        projects = _split_csv(self._projects_var.get())
        issuetypes = _split_csv(self._issuetypes_var.get())
        terminology = self._terminology_var.get()
        ct_method = self._ct_method_var.get()

        selected = [mid for mid, var in self._metric_vars.items() if var.get()]
        metrics = selected if selected else None

        return dict(
            issue_times=issue_times,
            cfd=cfd,
            from_date=from_date,
            to_date=to_date,
            projects=projects,
            issuetypes=issuetypes,
            terminology=terminology,
            ct_method=ct_method,
            metrics=metrics,
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _run_show(self) -> None:
        """Validate inputs, compute metrics, and display charts in the browser."""
        inputs = self._read_inputs()
        if inputs is None:
            return
        self._log(self._tr("log_started"))
        self._show_in_browser_from_inputs(inputs)

    def _show_in_browser_from_inputs(self, inputs: dict) -> None:
        """
        Compute metrics in a background thread and open results in the browser.

        Args:
            inputs: Dict of validated pipeline inputs from _read_inputs().
        """
        self._set_buttons_enabled(False)

        def worker() -> None:
            from .filters import FilterConfig, apply_filters
            from .loader import load_report_data
            from .metrics import all_metrics as _all_metrics
            from .metrics import get_metric

            try:
                data = load_report_data(inputs["issue_times"], inputs["cfd"])
                cfg = FilterConfig(
                    from_date=inputs["from_date"],
                    to_date=inputs["to_date"],
                    projects=inputs["projects"] or [],
                    issuetypes=inputs["issuetypes"] or [],
                )
                data = apply_filters(data, cfg)

                if inputs["metrics"]:
                    plugins = []
                    for mid in inputs["metrics"]:
                        try:
                            plugins.append(get_metric(mid))
                        except KeyError:
                            self._log(self._tr("log_unk_metric").format(mid))
                else:
                    plugins = _all_metrics()

                for plugin in plugins:
                    if isinstance(plugin, FlowTimeMetric):
                        plugin.ct_method = inputs.get("ct_method", CT_METHOD_A)

                all_figures = []
                for plugin in plugins:
                    result = plugin.compute(data, inputs["terminology"])
                    for w in result.warnings:
                        self._log(f"  WARNING: {w}")
                    all_figures.extend(plugin.render(result, inputs["terminology"]))

                if not all_figures:
                    self._log(self._tr("log_no_figs"))
                    return

                html = _build_combined_html(all_figures)
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as f:
                    f.write(html)
                    tmp_path = f.name

                self._log(self._tr("log_figs_opened").format(len(all_figures)))
                webbrowser.open(f"file:///{tmp_path.replace(chr(92), '/')}")

            except Exception as exc:
                self._log(self._tr("log_error").format(exc))
            finally:
                self.after(0, lambda: self._set_buttons_enabled(True))
                self.after(0, lambda: self._log(self._tr("log_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _run_export_pdf(self) -> None:
        """Validate inputs, ask for save path, compute metrics, and export PDF."""
        inputs = self._read_inputs()
        if inputs is None:
            return

        out_path = filedialog.asksaveasfilename(
            title=self._tr("dlg_pdf"),
            defaultextension=".pdf",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")],
        )
        if not out_path:
            return

        self._set_buttons_enabled(False)
        self._log(self._tr("log_pdf_started"))

        def worker() -> None:
            try:
                run_reports(
                    issue_times=inputs["issue_times"],
                    cfd=inputs["cfd"],
                    metrics=inputs["metrics"],
                    from_date=inputs["from_date"],
                    to_date=inputs["to_date"],
                    projects=inputs["projects"],
                    issuetypes=inputs["issuetypes"],
                    terminology=inputs["terminology"],
                    ct_method=inputs["ct_method"],
                    output_pdf=Path(out_path),
                    log=self._log,
                )
                self._log(self._tr("log_done"))
            except Exception as exc:
                self._log(self._tr("log_error").format(exc))
            finally:
                self.after(0, lambda: self._set_buttons_enabled(True))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        """
        Append a message to the log area in a thread-safe manner.

        Args:
            msg: Text to append.
        """
        def _append() -> None:
            self._log_area.configure(state="normal")
            self._log_area.insert("end", msg + "\n")
            self._log_area.see("end")
            self._log_area.configure(state="disabled")

        self.after(0, _append)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the action buttons.

        Args:
            enabled: True to enable, False to disable.
        """
        state = "normal" if enabled else "disabled"
        self._show_btn.configure(state=state)
        self._pdf_btn.configure(state=state)


def main() -> None:
    """
    Launch the build_reports GUI.

    Entry point called by __main__.py when no CLI arguments are provided.
    """
    BuildReportsApp().mainloop()


if __name__ == "__main__":
    main()
