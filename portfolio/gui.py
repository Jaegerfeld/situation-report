# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       22.06.2026
# Geändert:       22.06.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Verwaltungs-GUI für Large-Solution-/Portfolio-Reports (Phase 2). Erlaubt es,
#   eine Solution zu benennen, ARTs (über ihr Project-Template oder direkt eine
#   IssueTimes-Datei) zuzuordnen, den Modus (pooled/comparison) zu wählen, die
#   Konfiguration als JSON zu speichern/laden und den aggregierten HTML-Report
#   zu erzeugen. Die display-unabhängige Logik (Form → SolutionConfig, _T) ist
#   getrennt gehalten und unit-getestet; der tkinter-Teil wird nicht im Test
#   instanziiert (benötigt eine laufende Anzeige).
# =============================================================================

from __future__ import annotations

import json
import threading
import webbrowser
from datetime import date
from pathlib import Path
from typing import Any

from .aggregator import (
    DEFAULT_COMPARISON_METRICS,
    DEFAULT_POOLED_METRICS,
    render_comparison_html,
    render_pooled_html,
)
from .solution_config import (
    FRAMEWORK_LESS,
    FRAMEWORK_NEXUS,
    FRAMEWORK_SAFE,
    MODE_COMPARISON,
    MODE_POOLED,
    SolutionConfig,
    load_solution_config,
    parse_solution_config,
    save_solution_config,
)

# ---------------------------------------------------------------------------
# Language handling (shared preference file with the launcher)
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"

_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]
_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

FRAMEWORKS = [FRAMEWORK_SAFE, FRAMEWORK_LESS, FRAMEWORK_NEXUS]


def _load_lang_pref() -> str:
    """Load the shared language preference, defaulting to English."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _LANG_ORDER else LANG_EN
    except Exception:
        return LANG_EN


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title": "Solutions & Portfolios",
        "lbl_name": "Name der Solution",
        "lbl_framework": "Framework",
        "lbl_lang": "Sprache",
        "lbl_from": "Von (JJJJ-MM-TT)",
        "lbl_to": "Bis (JJJJ-MM-TT)",
        "sec_members": "ARTs in dieser Solution",
        "col_name": "ART-Name",
        "col_source": "Template (.json) oder IssueTimes (.xlsx)",
        "btn_add": "ART hinzufügen",
        "btn_remove": "Entfernen",
        "btn_browse": "Durchsuchen …",
        "lbl_mode": "Report-Modus",
        "mode_pooled": "Pooled (Solution als ein System)",
        "mode_comparison": "Comparison (ARTs nebeneinander)",
        "btn_new": "Neu",
        "btn_load": "Laden …",
        "btn_save": "Speichern …",
        "btn_generate": "Report erzeugen …",
        "tip_source": "Pfad zum Project-Template des ARTs oder direkt zur IssueTimes.xlsx",
        "tip_generate": "Aggregierten HTML-Report erzeugen und im Browser öffnen",
        "msg_saved": "Konfiguration gespeichert: {path}",
        "msg_loaded": "Konfiguration geladen: {path}",
        "msg_load_error": "Laden fehlgeschlagen: {error}",
        "msg_need_name": "Bitte einen Namen für die Solution angeben.",
        "msg_need_members": "Bitte mindestens einen ART hinzufügen.",
        "msg_generating": "Report wird erzeugt …",
        "msg_report_done": "Report erzeugt: {path}",
        "msg_no_figures": "Kein Report erzeugt (keine Diagramme).",
        "msg_invalid": "Ungültige Konfiguration: {error}",
        "dlg_open_config": "Solution-Konfiguration öffnen",
        "dlg_save_config": "Solution-Konfiguration speichern",
        "dlg_save_report": "Report speichern",
    },
    LANG_EN: {
        "window_title": "Solutions & Portfolios",
        "lbl_name": "Solution name",
        "lbl_framework": "Framework",
        "lbl_lang": "Language",
        "lbl_from": "From (YYYY-MM-DD)",
        "lbl_to": "To (YYYY-MM-DD)",
        "sec_members": "ARTs in this solution",
        "col_name": "ART name",
        "col_source": "Template (.json) or IssueTimes (.xlsx)",
        "btn_add": "Add ART",
        "btn_remove": "Remove",
        "btn_browse": "Browse …",
        "lbl_mode": "Report mode",
        "mode_pooled": "Pooled (solution as one system)",
        "mode_comparison": "Comparison (ARTs side by side)",
        "btn_new": "New",
        "btn_load": "Load …",
        "btn_save": "Save …",
        "btn_generate": "Generate report …",
        "tip_source": "Path to the ART's project template or directly to IssueTimes.xlsx",
        "tip_generate": "Generate the aggregated HTML report and open it in the browser",
        "msg_saved": "Configuration saved: {path}",
        "msg_loaded": "Configuration loaded: {path}",
        "msg_load_error": "Load failed: {error}",
        "msg_need_name": "Please enter a name for the solution.",
        "msg_need_members": "Please add at least one ART.",
        "msg_generating": "Generating report …",
        "msg_report_done": "Report generated: {path}",
        "msg_no_figures": "No report produced (no figures).",
        "msg_invalid": "Invalid configuration: {error}",
        "dlg_open_config": "Open solution configuration",
        "dlg_save_config": "Save solution configuration",
        "dlg_save_report": "Save report",
    },
    LANG_RO: {
        "window_title": "Soluții & Portofolii",
        "lbl_name": "Numele soluției",
        "lbl_framework": "Framework",
        "lbl_lang": "Limbă",
        "lbl_from": "De la (AAAA-LL-ZZ)",
        "lbl_to": "Până la (AAAA-LL-ZZ)",
        "sec_members": "ART-uri în această soluție",
        "col_name": "Nume ART",
        "col_source": "Template (.json) sau IssueTimes (.xlsx)",
        "btn_add": "Adaugă ART",
        "btn_remove": "Elimină",
        "btn_browse": "Răsfoiește …",
        "lbl_mode": "Mod raport",
        "mode_pooled": "Pooled (soluția ca un sistem)",
        "mode_comparison": "Comparison (ART-uri alăturate)",
        "btn_new": "Nou",
        "btn_load": "Încarcă …",
        "btn_save": "Salvează …",
        "btn_generate": "Generează raport …",
        "tip_source": "Calea către template-ul ART-ului sau direct către IssueTimes.xlsx",
        "tip_generate": "Generează raportul HTML agregat și deschide-l în browser",
        "msg_saved": "Configurație salvată: {path}",
        "msg_loaded": "Configurație încărcată: {path}",
        "msg_load_error": "Încărcare eșuată: {error}",
        "msg_need_name": "Introduceți un nume pentru soluție.",
        "msg_need_members": "Adăugați cel puțin un ART.",
        "msg_generating": "Se generează raportul …",
        "msg_report_done": "Raport generat: {path}",
        "msg_no_figures": "Niciun raport generat (fără diagrame).",
        "msg_invalid": "Configurație invalidă: {error}",
        "dlg_open_config": "Deschide configurația soluției",
        "dlg_save_config": "Salvează configurația soluției",
        "dlg_save_report": "Salvează raportul",
    },
    LANG_PT: {
        "window_title": "Soluções & Portefólios",
        "lbl_name": "Nome da solução",
        "lbl_framework": "Framework",
        "lbl_lang": "Idioma",
        "lbl_from": "De (AAAA-MM-DD)",
        "lbl_to": "Até (AAAA-MM-DD)",
        "sec_members": "ARTs nesta solução",
        "col_name": "Nome do ART",
        "col_source": "Template (.json) ou IssueTimes (.xlsx)",
        "btn_add": "Adicionar ART",
        "btn_remove": "Remover",
        "btn_browse": "Procurar …",
        "lbl_mode": "Modo de relatório",
        "mode_pooled": "Pooled (solução como um sistema)",
        "mode_comparison": "Comparison (ARTs lado a lado)",
        "btn_new": "Novo",
        "btn_load": "Carregar …",
        "btn_save": "Guardar …",
        "btn_generate": "Gerar relatório …",
        "tip_source": "Caminho para o template do ART ou diretamente para IssueTimes.xlsx",
        "tip_generate": "Gerar o relatório HTML agregado e abri-lo no browser",
        "msg_saved": "Configuração guardada: {path}",
        "msg_loaded": "Configuração carregada: {path}",
        "msg_load_error": "Falha ao carregar: {error}",
        "msg_need_name": "Introduza um nome para a solução.",
        "msg_need_members": "Adicione pelo menos um ART.",
        "msg_generating": "A gerar relatório …",
        "msg_report_done": "Relatório gerado: {path}",
        "msg_no_figures": "Nenhum relatório produzido (sem gráficos).",
        "msg_invalid": "Configuração inválida: {error}",
        "dlg_open_config": "Abrir configuração da solução",
        "dlg_save_config": "Guardar configuração da solução",
        "dlg_save_report": "Guardar relatório",
    },
    LANG_FR: {
        "window_title": "Solutions & Portefeuilles",
        "lbl_name": "Nom de la solution",
        "lbl_framework": "Framework",
        "lbl_lang": "Langue",
        "lbl_from": "De (AAAA-MM-JJ)",
        "lbl_to": "À (AAAA-MM-JJ)",
        "sec_members": "ARTs dans cette solution",
        "col_name": "Nom de l'ART",
        "col_source": "Template (.json) ou IssueTimes (.xlsx)",
        "btn_add": "Ajouter un ART",
        "btn_remove": "Supprimer",
        "btn_browse": "Parcourir …",
        "lbl_mode": "Mode de rapport",
        "mode_pooled": "Pooled (la solution comme un système)",
        "mode_comparison": "Comparison (ARTs côte à côte)",
        "btn_new": "Nouveau",
        "btn_load": "Charger …",
        "btn_save": "Enregistrer …",
        "btn_generate": "Générer le rapport …",
        "tip_source": "Chemin vers le template de l'ART ou directement vers IssueTimes.xlsx",
        "tip_generate": "Générer le rapport HTML agrégé et l'ouvrir dans le navigateur",
        "msg_saved": "Configuration enregistrée : {path}",
        "msg_loaded": "Configuration chargée : {path}",
        "msg_load_error": "Échec du chargement : {error}",
        "msg_need_name": "Veuillez saisir un nom pour la solution.",
        "msg_need_members": "Veuillez ajouter au moins un ART.",
        "msg_generating": "Génération du rapport …",
        "msg_report_done": "Rapport généré : {path}",
        "msg_no_figures": "Aucun rapport produit (aucun graphique).",
        "msg_invalid": "Configuration invalide : {error}",
        "dlg_open_config": "Ouvrir la configuration de la solution",
        "dlg_save_config": "Enregistrer la configuration de la solution",
        "dlg_save_report": "Enregistrer le rapport",
    },
}


# ---------------------------------------------------------------------------
# Display-independent logic (unit-tested without tkinter)
# ---------------------------------------------------------------------------

def _member_dict(name: str, source: str) -> dict[str, str]:
    """
    Map a (name, source path) pair to a member dict.

    A ``.json`` source is treated as a project template; anything else is taken
    as a direct IssueTimes path.

    Args:
        name:   ART display name.
        source: Path string (template .json or IssueTimes .xlsx).

    Returns:
        Member dict with ``name`` plus either ``template`` or ``issue_times``.
    """
    source = source.strip()
    key = "template" if source.lower().endswith(".json") else "issue_times"
    return {"name": name.strip(), key: source}


def build_config_from_fields(
    name: str,
    framework: str,
    from_str: str,
    to_str: str,
    members: list[tuple[str, str]],
    mode: str,
) -> SolutionConfig:
    """
    Build (and validate) a SolutionConfig from raw form field values.

    Empty member rows (no source path) are ignored. Date strings are passed
    through as-is; validation/parsing is delegated to parse_solution_config.

    Args:
        name:      Solution name.
        framework: SAFe / LeSS / Nexus.
        from_str:  Optional from-date string (YYYY-MM-DD) or "".
        to_str:    Optional to-date string or "".
        members:   List of (art_name, source_path) pairs.
        mode:      MODE_POOLED or MODE_COMPARISON.

    Returns:
        Validated SolutionConfig.

    Raises:
        ValueError: If the resulting configuration is invalid.
    """
    member_dicts = [_member_dict(n, s) for n, s in members if s.strip()]
    report: dict[str, Any] = {"modes": [mode]}
    if from_str.strip():
        report["from_date"] = from_str.strip()
    if to_str.strip():
        report["to_date"] = to_str.strip()
    return parse_solution_config({
        "schema": 1,
        "app": "situation_report",
        "kind": "solution",
        "name": name,
        "framework": framework,
        "members": member_dicts,
        "report": report,
    })


def default_metrics_for_mode(mode: str) -> list[str]:
    """Return the default metric set used for the given report mode."""
    return (DEFAULT_COMPARISON_METRICS if mode == MODE_COMPARISON
            else DEFAULT_POOLED_METRICS)


# ---------------------------------------------------------------------------
# tkinter application (not unit-tested — requires a display)
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover - requires a display
    """Launch the Solutions & Portfolios manager window."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class SolutionManagerApp(tk.Tk):
        """tkinter window to build, save/load and run a solution configuration."""

        def __init__(self) -> None:
            super().__init__()
            self._lang = _load_lang_pref()
            self.title(self._tr("window_title"))
            self.configure(padx=14, pady=12)
            self.minsize(640, 480)

            self._name = tk.StringVar()
            self._framework = tk.StringVar(value=FRAMEWORK_SAFE)
            self._from = tk.StringVar()
            self._to = tk.StringVar()
            self._mode = tk.StringVar(value=MODE_POOLED)
            self._lang_var = tk.StringVar(value=self._lang)
            self._member_rows: list[dict] = []
            self._status = tk.StringVar()

            self._build_ui()

        def _tr(self, key: str) -> str:
            return _T.get(self._lang, _T[LANG_EN]).get(key, key)

        # -- UI construction -------------------------------------------------
        def _build_ui(self) -> None:
            top = tk.Frame(self)
            top.pack(fill="x")
            tk.Label(top, text=self._tr("lbl_name")).grid(row=0, column=0, sticky="w")
            tk.Entry(top, textvariable=self._name, width=34).grid(
                row=0, column=1, sticky="we", padx=(6, 16))
            tk.Label(top, text=self._tr("lbl_framework")).grid(row=0, column=2, sticky="w")
            ttk.Combobox(top, textvariable=self._framework, values=FRAMEWORKS,
                         width=8, state="readonly").grid(row=0, column=3, padx=(6, 16))
            tk.Label(top, text=self._tr("lbl_lang")).grid(row=0, column=4, sticky="w")
            lang_box = ttk.Combobox(top, textvariable=self._lang_var, values=_LANG_ORDER,
                                    width=4, state="readonly")
            lang_box.grid(row=0, column=5)
            lang_box.bind("<<ComboboxSelected>>", lambda *_: self._switch_lang())

            tk.Label(top, text=self._tr("lbl_from")).grid(row=1, column=0, sticky="w", pady=(6, 0))
            tk.Entry(top, textvariable=self._from, width=16).grid(
                row=1, column=1, sticky="w", padx=(6, 16), pady=(6, 0))
            tk.Label(top, text=self._tr("lbl_to")).grid(row=1, column=2, sticky="w", pady=(6, 0))
            tk.Entry(top, textvariable=self._to, width=16).grid(
                row=1, column=3, sticky="w", padx=(6, 16), pady=(6, 0))
            top.columnconfigure(1, weight=1)

            tk.Label(self, text=self._tr("sec_members"),
                     font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(12, 2))
            head = tk.Frame(self)
            head.pack(fill="x")
            tk.Label(head, text=self._tr("col_name"), width=20, anchor="w").grid(row=0, column=0)
            tk.Label(head, text=self._tr("col_source"), anchor="w").grid(row=0, column=1, sticky="w")
            self._members_frame = tk.Frame(self)
            self._members_frame.pack(fill="both", expand=True)
            ttk.Button(self, text=self._tr("btn_add"), command=self._add_member_row).pack(
                anchor="w", pady=(4, 0))

            mode_frame = tk.Frame(self)
            mode_frame.pack(fill="x", pady=(12, 0))
            tk.Label(mode_frame, text=self._tr("lbl_mode")).pack(side="left")
            ttk.Radiobutton(mode_frame, text=self._tr("mode_pooled"),
                            variable=self._mode, value=MODE_POOLED).pack(side="left", padx=(8, 0))
            ttk.Radiobutton(mode_frame, text=self._tr("mode_comparison"),
                            variable=self._mode, value=MODE_COMPARISON).pack(side="left", padx=(8, 0))

            btns = tk.Frame(self)
            btns.pack(fill="x", pady=(12, 0))
            ttk.Button(btns, text=self._tr("btn_new"), command=self._new).pack(side="left")
            ttk.Button(btns, text=self._tr("btn_load"), command=self._load).pack(side="left", padx=(6, 0))
            ttk.Button(btns, text=self._tr("btn_save"), command=self._save).pack(side="left", padx=(6, 0))
            ttk.Button(btns, text=self._tr("btn_generate"), command=self._generate).pack(
                side="right")

            tk.Label(self, textvariable=self._status, fg="#2980b9", anchor="w").pack(
                fill="x", pady=(10, 0))

            self._add_member_row()

        def _switch_lang(self) -> None:
            self._lang = self._lang_var.get()
            for child in list(self.children.values()):
                child.destroy()
            self.title(self._tr("window_title"))
            rows = [(r["name"].get(), r["source"].get()) for r in self._member_rows]
            self._member_rows = []
            self._build_ui()
            # restore member rows
            self._member_rows[0]["name"].set(rows[0][0] if rows else "")
            if rows:
                self._member_rows[0]["source"].set(rows[0][1])
            for n, s in rows[1:]:
                self._add_member_row()
                self._member_rows[-1]["name"].set(n)
                self._member_rows[-1]["source"].set(s)

        def _add_member_row(self) -> None:
            row = tk.Frame(self._members_frame)
            row.pack(fill="x", pady=1)
            name_var, src_var = tk.StringVar(), tk.StringVar()
            tk.Entry(row, textvariable=name_var, width=20).grid(row=0, column=0, sticky="w")
            tk.Entry(row, textvariable=src_var).grid(row=0, column=1, sticky="we", padx=(4, 4))
            ttk.Button(row, text=self._tr("btn_browse"),
                       command=lambda v=src_var: self._browse(v)).grid(row=0, column=2)
            entry = {"frame": row, "name": name_var, "source": src_var}
            ttk.Button(row, text=self._tr("btn_remove"),
                       command=lambda e=entry: self._remove_member_row(e)).grid(
                row=0, column=3, padx=(4, 0))
            row.columnconfigure(1, weight=1)
            self._member_rows.append(entry)

        def _remove_member_row(self, entry: dict) -> None:
            if len(self._member_rows) <= 1:
                return
            entry["frame"].destroy()
            self._member_rows.remove(entry)

        def _browse(self, var: tk.StringVar) -> None:
            path = filedialog.askopenfilename(
                filetypes=[("Solution member", "*.json *.xlsx"),
                           ("Project template", "*.json"),
                           ("IssueTimes", "*.xlsx"), ("All files", "*.*")])
            if path:
                var.set(path)

        # -- actions ---------------------------------------------------------
        def _collect_members(self) -> list[tuple[str, str]]:
            return [(r["name"].get(), r["source"].get()) for r in self._member_rows]

        def _new(self) -> None:
            self._name.set("")
            self._from.set("")
            self._to.set("")
            self._mode.set(MODE_POOLED)
            for entry in list(self._member_rows[1:]):
                self._remove_member_row(entry)
            self._member_rows[0]["name"].set("")
            self._member_rows[0]["source"].set("")
            self._status.set("")

        def _load(self) -> None:
            path = filedialog.askopenfilename(
                title=self._tr("dlg_open_config"), filetypes=[("JSON", "*.json")])
            if not path:
                return
            try:
                cfg = load_solution_config(Path(path))
            except Exception as exc:  # noqa: BLE001 - surface any load error to the user
                messagebox.showerror(self._tr("window_title"),
                                     self._tr("msg_load_error").format(error=exc))
                return
            self._name.set(cfg.name)
            self._framework.set(cfg.framework)
            self._from.set(cfg.from_date.isoformat() if cfg.from_date else "")
            self._to.set(cfg.to_date.isoformat() if cfg.to_date else "")
            self._mode.set(cfg.modes[0] if cfg.modes else MODE_POOLED)
            for entry in list(self._member_rows[1:]):
                self._remove_member_row(entry)
            self._member_rows[0]["name"].set("")
            self._member_rows[0]["source"].set("")
            for i, m in enumerate(cfg.members):
                if i > 0:
                    self._add_member_row()
                self._member_rows[i]["name"].set(m.name)
                self._member_rows[i]["source"].set(m.template or m.issue_times)
            self._status.set(self._tr("msg_loaded").format(path=path))

        def _build_config(self) -> SolutionConfig | None:
            try:
                return build_config_from_fields(
                    self._name.get(), self._framework.get(),
                    self._from.get(), self._to.get(),
                    self._collect_members(), self._mode.get())
            except ValueError as exc:
                messagebox.showwarning(self._tr("window_title"),
                                       self._tr("msg_invalid").format(error=exc))
                return None

        def _save(self) -> None:
            cfg = self._build_config()
            if cfg is None:
                return
            path = filedialog.asksaveasfilename(
                title=self._tr("dlg_save_config"), defaultextension=".json",
                filetypes=[("JSON", "*.json")])
            if not path:
                return
            save_solution_config(Path(path), cfg)
            self._status.set(self._tr("msg_saved").format(path=path))

        def _generate(self) -> None:
            cfg = self._build_config()
            if cfg is None:
                return
            out = filedialog.asksaveasfilename(
                title=self._tr("dlg_save_report"), defaultextension=".html",
                initialfile=f"{cfg.name}_{self._mode.get()}.html",
                filetypes=[("HTML", "*.html")])
            if not out:
                return
            self._status.set(self._tr("msg_generating"))
            self.update_idletasks()

            render = (render_comparison_html if self._mode.get() == MODE_COMPARISON
                      else render_pooled_html)

            def worker() -> None:
                html = render(cfg, log=lambda *_: None)
                if html:
                    Path(out).write_text(html, encoding="utf-8")
                self.after(0, lambda: self._done(out, bool(html)))

            threading.Thread(target=worker, daemon=True).start()

        def _done(self, out: str, ok: bool) -> None:
            if ok:
                self._status.set(self._tr("msg_report_done").format(path=out))
                webbrowser.open(Path(out).resolve().as_uri())
            else:
                self._status.set(self._tr("msg_no_figures"))

    SolutionManagerApp().mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
