# =============================================================================
# Autor:          Robert Seebauer
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       10.04.2026
# Geändert:       10.04.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Grafische Benutzeroberfläche (tkinter) für transform_data. Ermöglicht die
#   Auswahl von Jira-JSON-Export, Workflow-Definitionsdatei und Ausgabeordner
#   über Dateidialoge. Ausgabeordner und Präfix werden beim Öffnen der JSON-
#   Datei automatisch vorbelegt. Die Transformation läuft in einem separaten
#   Thread, sodass die Oberfläche während der Verarbeitung reaktionsfähig
#   bleibt. Warnungen und Ergebnisse werden im Log-Bereich angezeigt.
# =============================================================================

import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path

from .transform import run_transform


class TransformApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("transform_data")
        self.resizable(True, True)

        self._json_var = tk.StringVar()
        self._workflow_var = tk.StringVar()
        self._output_dir_var = tk.StringVar()
        self._prefix_var = tk.StringVar()
        self._auto_prefix: str = ""   # tracks the last auto-filled prefix value

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        self.columnconfigure(1, weight=1)

        # --- Input rows ---
        tk.Label(self, text="JSON-Datei", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._json_var, state="readonly", width=55).grid(
            row=0, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Durchsuchen…", command=self._pick_json).grid(
            row=0, column=2, **pad
        )

        tk.Label(self, text="Workflow-Datei", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._workflow_var, state="readonly", width=55).grid(
            row=1, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Durchsuchen…", command=self._pick_workflow).grid(
            row=1, column=2, **pad
        )

        tk.Label(self, text="Ausgabeordner", anchor="w").grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._output_dir_var, state="readonly", width=55).grid(
            row=2, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Durchsuchen…", command=self._pick_output_dir).grid(
            row=2, column=2, **pad
        )

        # --- Prefix row ---
        tk.Label(self, text="Präfix", anchor="w").grid(row=3, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self._prefix_var, width=55).grid(
            row=3, column=1, sticky="ew", **pad
        )

        # --- Run button ---
        self._run_btn = ttk.Button(self, text="Ausführen", command=self._run)
        self._run_btn.grid(row=4, column=0, columnspan=3, pady=8)

        # --- Log area ---
        tk.Label(self, text="Log", anchor="w").grid(row=5, column=0, sticky="w", **pad)
        self._log_area = scrolledtext.ScrolledText(
            self, height=12, state="disabled", wrap="word"
        )
        self._log_area.grid(row=6, column=0, columnspan=3, sticky="nsew", **pad)
        self.rowconfigure(6, weight=1)

    # --- File pickers ---

    def _pick_json(self) -> None:
        path = filedialog.askopenfilename(
            title="JSON-Datei wählen",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        self._json_var.set(path)

        # Auto-fill output dir if still empty
        if not self._output_dir_var.get():
            self._output_dir_var.set(str(Path(path).parent))

        # Auto-fill prefix if still empty or matches the previous auto-value
        stem = Path(path).stem
        current_prefix = self._prefix_var.get()
        if not current_prefix or current_prefix == self._auto_prefix:
            self._prefix_var.set(stem)
            self._auto_prefix = stem

    def _pick_workflow(self) -> None:
        path = filedialog.askopenfilename(
            title="Workflow-Datei wählen",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")],
        )
        if path:
            self._workflow_var.set(path)

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Ausgabeordner wählen")
        if path:
            self._output_dir_var.set(path)

    # --- Run ---

    def _run(self) -> None:
        json_path = self._json_var.get().strip()
        workflow_path = self._workflow_var.get().strip()

        if not json_path:
            self._log("FEHLER: Keine JSON-Datei ausgewählt.")
            return
        if not workflow_path:
            self._log("FEHLER: Keine Workflow-Datei ausgewählt.")
            return
        if not Path(json_path).is_file():
            self._log(f"FEHLER: JSON-Datei nicht gefunden: {json_path}")
            return
        if not Path(workflow_path).is_file():
            self._log(f"FEHLER: Workflow-Datei nicht gefunden: {workflow_path}")
            return

        output_dir_str = self._output_dir_var.get().strip()
        output_dir = Path(output_dir_str) if output_dir_str else None
        prefix = self._prefix_var.get().strip() or None

        self._set_running(True)
        self._log("--- Transformation gestartet ---")

        def worker() -> None:
            try:
                run_transform(
                    Path(json_path),
                    Path(workflow_path),
                    output_dir=output_dir,
                    prefix=prefix,
                    log=self._log,
                )
                self._log("--- Fertig ---")
            except Exception as exc:
                self._log(f"FEHLER: {exc}")
            finally:
                self.after(0, lambda: self._set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    # --- Helpers ---

    def _log(self, msg: str) -> None:
        def _append() -> None:
            self._log_area.configure(state="normal")
            self._log_area.insert("end", msg + "\n")
            self._log_area.see("end")
            self._log_area.configure(state="disabled")
        self.after(0, _append)

    def _set_running(self, running: bool) -> None:
        self._run_btn.configure(state="disabled" if running else "normal")


if __name__ == "__main__":
    TransformApp().mainloop()
