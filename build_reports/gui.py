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
#   Issuetypen), Metrik-Auswahl (Checkboxen), SAFe/Global-Terminologie sowie
#   die Anzeige der Diagramme im Browser und den Export als PDF. Die Berechnung
#   läuft in einem separaten Thread, sodass die Oberfläche reaktionsfähig bleibt.
# =============================================================================

from __future__ import annotations

import tempfile
import threading
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

from .cli import run_reports
from .metrics import all_metrics
from .terminology import GLOBAL, SAFE, term


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


class BuildReportsApp(tk.Tk):
    """
    Main tkinter application window for build_reports.

    Provides file selection, filter controls, metric checkboxes, terminology
    toggle, a browser preview button, and PDF export. Computation runs in a
    background thread to keep the UI responsive.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("build_reports")
        self.resizable(True, True)
        self.minsize(520, 600)

        self._plugins = all_metrics()

        # --- StringVars / BooleanVars ---
        self._issue_times_var = tk.StringVar()
        self._cfd_var = tk.StringVar()
        self._from_date_var = tk.StringVar()
        self._to_date_var = tk.StringVar()
        self._projects_var = tk.StringVar()
        self._issuetypes_var = tk.StringVar()
        self._terminology_var = tk.StringVar(value=SAFE)
        self._metric_vars: dict[str, tk.BooleanVar] = {
            p.metric_id: tk.BooleanVar(value=True) for p in self._plugins
        }

        self._build_ui()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build and arrange all UI widgets."""
        pad = {"padx": 8, "pady": 3}
        self.columnconfigure(1, weight=1)
        row = 0

        # --- Files section ---
        row = self._section_header("Dateien", row)

        tk.Label(self, text="IssueTimes", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._issue_times_var, state="readonly", width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Durchsuchen…", command=self._pick_issue_times).grid(
            row=row, column=2, **pad
        )
        row += 1

        tk.Label(self, text="CFD (optional)", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._cfd_var, state="readonly", width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Durchsuchen…", command=self._pick_cfd).grid(
            row=row, column=2, **pad
        )
        row += 1

        # --- Filters section ---
        row = self._section_header("Filter", row)

        tk.Label(self, text="Von (YYYY-MM-DD)", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._from_date_var, width=20).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 1

        tk.Label(self, text="Bis (YYYY-MM-DD)", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._to_date_var, width=20).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 1

        tk.Label(self, text="Projekte", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._projects_var, width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        tk.Label(self, text="kommagetrennt", fg="gray", font=("", 8)).grid(
            row=row, column=2, sticky="w", **pad
        )
        row += 1

        tk.Label(self, text="Issuetypen", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        tk.Entry(self, textvariable=self._issuetypes_var, width=50).grid(
            row=row, column=1, sticky="ew", **pad
        )
        row += 1

        # --- Metrics section ---
        row = self._section_header("Metriken", row)

        for plugin in self._plugins:
            label = term(plugin.metric_id, SAFE)
            tk.Checkbutton(
                self,
                text=label,
                variable=self._metric_vars[plugin.metric_id],
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=16, pady=1)
            row += 1

        # Select-all / deselect-all buttons
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=16, pady=2)
        ttk.Button(btn_frame, text="Alle", width=6,
                   command=self._select_all_metrics).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Keine", width=6,
                   command=self._deselect_all_metrics).pack(side="left", padx=2)
        row += 1

        # --- Terminology section ---
        row = self._section_header("Terminologie", row)

        term_frame = tk.Frame(self)
        term_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=16, pady=4)
        for value, label in [(SAFE, "SAFe"), (GLOBAL, "Global")]:
            tk.Radiobutton(
                term_frame,
                text=label,
                variable=self._terminology_var,
                value=value,
            ).pack(side="left", padx=8)
        row += 1

        # --- Action buttons ---
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=6
        )
        row += 1

        action_frame = tk.Frame(self)
        action_frame.grid(row=row, column=0, columnspan=3, pady=4)
        self._show_btn = ttk.Button(
            action_frame, text="Anzeigen im Browser", command=self._run_show
        )
        self._show_btn.pack(side="left", padx=8)
        self._pdf_btn = ttk.Button(
            action_frame, text="Als PDF speichern", command=self._run_export_pdf
        )
        self._pdf_btn.pack(side="left", padx=8)
        row += 1

        # --- Log area ---
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=4
        )
        row += 1

        tk.Label(self, text="Log", anchor="w").grid(
            row=row, column=0, sticky="w", **pad
        )
        row += 1

        self._log_area = scrolledtext.ScrolledText(
            self, height=10, state="disabled", wrap="word"
        )
        self._log_area.grid(
            row=row, column=0, columnspan=3, sticky="nsew", **pad
        )
        self.rowconfigure(row, weight=1)

    def _section_header(self, title: str, row: int) -> int:
        """Insert a labelled separator and return the next available row index."""
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(8, 2)
        )
        row += 1
        tk.Label(self, text=title, font=("", 9, "bold"), anchor="w").grid(
            row=row, column=0, columnspan=3, sticky="w", padx=8
        )
        row += 1
        return row

    # -------------------------------------------------------------------------
    # File pickers
    # -------------------------------------------------------------------------

    def _pick_issue_times(self) -> None:
        """Open a file dialog to select the IssueTimes.xlsx file."""
        path = filedialog.askopenfilename(
            title="IssueTimes-Datei wählen",
            filetypes=[("Excel-Dateien", "*.xlsx"), ("Alle Dateien", "*.*")],
        )
        if path:
            self._issue_times_var.set(path)

    def _pick_cfd(self) -> None:
        """Open a file dialog to select the CFD.xlsx file."""
        path = filedialog.askopenfilename(
            title="CFD-Datei wählen",
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
            issuetypes, terminology, metrics. Returns None if validation fails.
        """
        issue_times_str = self._issue_times_var.get().strip()
        if not issue_times_str:
            self._log("FEHLER: Keine IssueTimes-Datei ausgewählt.")
            return None
        issue_times = Path(issue_times_str)
        if not issue_times.is_file():
            self._log(f"FEHLER: Datei nicht gefunden: {issue_times}")
            return None

        cfd_str = self._cfd_var.get().strip()
        cfd = Path(cfd_str) if cfd_str else None

        try:
            from_date = _parse_date_safe(self._from_date_var.get())
        except ValueError:
            self._log(
                f"FEHLER: Ungültiges Von-Datum '{self._from_date_var.get()}' "
                "(erwartet YYYY-MM-DD)."
            )
            return None

        try:
            to_date = _parse_date_safe(self._to_date_var.get())
        except ValueError:
            self._log(
                f"FEHLER: Ungültiges Bis-Datum '{self._to_date_var.get()}' "
                "(erwartet YYYY-MM-DD)."
            )
            return None

        projects = _split_csv(self._projects_var.get())
        issuetypes = _split_csv(self._issuetypes_var.get())
        terminology = self._terminology_var.get()

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
        self._log("--- Berechnung gestartet ---")
        self._show_in_browser_from_inputs(inputs)

    def _show_in_browser_from_inputs(self, inputs: dict) -> None:
        """
        Compute metrics and open results in the default browser.

        This method runs on the main thread (called via after()) to ensure
        the browser open is safe. Computation is lightweight here since the
        same data was already validated; figures are collected and rendered
        to a temporary HTML file.

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
                            self._log(f"  WARNING: Unbekannte Metrik '{mid}' — übersprungen.")
                else:
                    plugins = _all_metrics()

                all_figures = []
                for plugin in plugins:
                    result = plugin.compute(data, inputs["terminology"])
                    for w in result.warnings:
                        self._log(f"  WARNING: {w}")
                    all_figures.extend(plugin.render(result, inputs["terminology"]))

                if not all_figures:
                    self._log("Keine Diagramme erzeugt.")
                    return

                html = _build_combined_html(all_figures)
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as f:
                    f.write(html)
                    tmp_path = f.name

                self._log(f"  → {len(all_figures)} Diagramm(e) im Browser geöffnet.")
                webbrowser.open(f"file:///{tmp_path.replace(chr(92), '/')}")

            except Exception as exc:
                self._log(f"FEHLER: {exc}")
            finally:
                self.after(0, lambda: self._set_buttons_enabled(True))
                self.after(0, lambda: self._log("--- Fertig ---"))

        threading.Thread(target=worker, daemon=True).start()

    def _run_export_pdf(self) -> None:
        """Validate inputs, ask for save path, compute metrics, and export PDF."""
        inputs = self._read_inputs()
        if inputs is None:
            return

        out_path = filedialog.asksaveasfilename(
            title="PDF speichern unter",
            defaultextension=".pdf",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")],
        )
        if not out_path:
            return

        self._set_buttons_enabled(False)
        self._log("--- PDF-Export gestartet ---")

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
                    output_pdf=Path(out_path),
                    log=self._log,
                )
                self._log("--- Fertig ---")
            except Exception as exc:
                self._log(f"FEHLER: {exc}")
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
