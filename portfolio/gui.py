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
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .aggregator import (
    DEFAULT_COMPARISON_METRICS,
    DEFAULT_POOLED_METRICS,
    render_comparison_html,
    render_pdf,
    render_pooled_html,
)
from .solution_config import (
    FRAMEWORK_SAFE,
    KIND_PORTFOLIO,
    KIND_SOLUTION,
    MODE_COMPARISON,
    MODE_POOLED,
    TERMINOLOGY_GLOBAL,
    TERMINOLOGY_SAFE,
    SolutionConfig,
    load_solution_config,
    parse_solution_config,
    save_solution_config,
)

KINDS = [KIND_SOLUTION, KIND_PORTFOLIO]
TERMINOLOGIES = [TERMINOLOGY_SAFE, TERMINOLOGY_GLOBAL]

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

#: Hosted user-manual PDF per language (GitHub Pages, deployed from docs/).
_MANUAL_BASE = "https://jaegerfeld.github.io/situation-report/"
_MANUAL_URLS: dict[str, str] = {
    LANG_DE: _MANUAL_BASE + "portfolio_Benutzerhandbuch.pdf",
    LANG_EN: _MANUAL_BASE + "portfolio_UserManual.pdf",
    LANG_RO: _MANUAL_BASE + "portfolio_ManualUtilizator.pdf",
    LANG_PT: _MANUAL_BASE + "portfolio_ManualUtilizador.pdf",
    LANG_FR: _MANUAL_BASE + "portfolio_ManuelUtilisateur.pdf",
}


def _load_lang_pref() -> str:
    """Load the shared language preference, defaulting to English."""
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _LANG_ORDER else LANG_EN
    except Exception:
        return LANG_EN


def _save_lang_pref(lang: str) -> None:
    """Persist the language preference to the shared preferences file."""
    try:
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
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title": "Solutions & Portfolios",
        "lbl_name": "Name der Solution",
        "lbl_terminology": "Terminologie",
        "lbl_lang": "Sprache",
        "dlg_pick_date": "Datum wählen",
        "btn_ok": "OK",
        "lbl_from": "Von (JJJJ-MM-TT)",
        "lbl_to": "Bis (JJJJ-MM-TT)",
        "sec_members": "ARTs in dieser Solution",
        "lbl_kind": "Art",
        "col_name": "ART-Name",
        "col_source": "Template (.json) oder IssueTimes (.xlsx)",
        "col_source_portfolio": "Solution-Template (.json)",
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
        "btn_snapshot": "Snapshot speichern …",
        "btn_delta": "Delta-Briefing …",
        "dlg_save_snapshot": "Snapshot speichern",
        "dlg_delta_prev": "Vorher-Snapshot wählen",
        "dlg_delta_now": "Nachher-Snapshot wählen",
        "msg_snapshot_saving": "Snapshot wird erzeugt …",
        "msg_snapshot_done": "Snapshot gespeichert: {path}",
        "msg_snapshot_error": "Snapshot fehlgeschlagen: {error}",
        "msg_delta_done": "Delta-Briefing im Browser geöffnet",
        "msg_delta_error": "Delta-Briefing fehlgeschlagen: {error}",
    },
    LANG_EN: {
        "window_title": "Solutions & Portfolios",
        "lbl_name": "Solution name",
        "lbl_terminology": "Terminology",
        "lbl_lang": "Language",
        "dlg_pick_date": "Pick date",
        "btn_ok": "OK",
        "lbl_from": "From (YYYY-MM-DD)",
        "lbl_to": "To (YYYY-MM-DD)",
        "sec_members": "ARTs in this solution",
        "lbl_kind": "Kind",
        "col_name": "ART name",
        "col_source": "Template (.json) or IssueTimes (.xlsx)",
        "col_source_portfolio": "Solution template (.json)",
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
        "btn_snapshot": "Save snapshot …",
        "btn_delta": "Delta briefing …",
        "dlg_save_snapshot": "Save snapshot",
        "dlg_delta_prev": "Select earlier snapshot",
        "dlg_delta_now": "Select later snapshot",
        "msg_snapshot_saving": "Building snapshot …",
        "msg_snapshot_done": "Snapshot saved: {path}",
        "msg_snapshot_error": "Snapshot failed: {error}",
        "msg_delta_done": "Delta briefing opened in the browser",
        "msg_delta_error": "Delta briefing failed: {error}",
    },
    LANG_RO: {
        "window_title": "Soluții & Portofolii",
        "lbl_name": "Numele soluției",
        "lbl_terminology": "Terminologie",
        "lbl_lang": "Limbă",
        "dlg_pick_date": "Selectați data",
        "btn_ok": "OK",
        "lbl_from": "De la (AAAA-LL-ZZ)",
        "lbl_to": "Până la (AAAA-LL-ZZ)",
        "sec_members": "ART-uri în această soluție",
        "lbl_kind": "Tip",
        "col_name": "Nume ART",
        "col_source": "Template (.json) sau IssueTimes (.xlsx)",
        "col_source_portfolio": "Template soluție (.json)",
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
        "btn_snapshot": "Salvează snapshot …",
        "btn_delta": "Delta briefing …",
        "dlg_save_snapshot": "Salvează snapshot-ul",
        "dlg_delta_prev": "Alege snapshot-ul anterior",
        "dlg_delta_now": "Alege snapshot-ul recent",
        "msg_snapshot_saving": "Se creează snapshot-ul …",
        "msg_snapshot_done": "Snapshot salvat: {path}",
        "msg_snapshot_error": "Snapshot eșuat: {error}",
        "msg_delta_done": "Delta briefing deschis în browser",
        "msg_delta_error": "Delta briefing eșuat: {error}",
    },
    LANG_PT: {
        "window_title": "Soluções & Portefólios",
        "lbl_name": "Nome da solução",
        "lbl_terminology": "Terminologia",
        "lbl_lang": "Idioma",
        "dlg_pick_date": "Selecionar data",
        "btn_ok": "OK",
        "lbl_from": "De (AAAA-MM-DD)",
        "lbl_to": "Até (AAAA-MM-DD)",
        "sec_members": "ARTs nesta solução",
        "lbl_kind": "Tipo",
        "col_name": "Nome do ART",
        "col_source": "Template (.json) ou IssueTimes (.xlsx)",
        "col_source_portfolio": "Template de solução (.json)",
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
        "btn_snapshot": "Guardar snapshot …",
        "btn_delta": "Delta briefing …",
        "dlg_save_snapshot": "Guardar snapshot",
        "dlg_delta_prev": "Escolher o snapshot anterior",
        "dlg_delta_now": "Escolher o snapshot recente",
        "msg_snapshot_saving": "A criar o snapshot …",
        "msg_snapshot_done": "Snapshot guardado: {path}",
        "msg_snapshot_error": "Snapshot falhou: {error}",
        "msg_delta_done": "Delta briefing aberto no browser",
        "msg_delta_error": "Delta briefing falhou: {error}",
    },
    LANG_FR: {
        "window_title": "Solutions & Portefeuilles",
        "lbl_name": "Nom de la solution",
        "lbl_terminology": "Terminologie",
        "lbl_lang": "Langue",
        "dlg_pick_date": "Choisir la date",
        "btn_ok": "OK",
        "lbl_from": "De (AAAA-MM-JJ)",
        "lbl_to": "À (AAAA-MM-JJ)",
        "sec_members": "ARTs dans cette solution",
        "lbl_kind": "Type",
        "col_name": "Nom de l'ART",
        "col_source": "Template (.json) ou IssueTimes (.xlsx)",
        "col_source_portfolio": "Template de solution (.json)",
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
        "btn_snapshot": "Enregistrer le snapshot …",
        "btn_delta": "Delta briefing …",
        "dlg_save_snapshot": "Enregistrer le snapshot",
        "dlg_delta_prev": "Choisir le snapshot précédent",
        "dlg_delta_now": "Choisir le snapshot récent",
        "msg_snapshot_saving": "Création du snapshot …",
        "msg_snapshot_done": "Snapshot enregistré : {path}",
        "msg_snapshot_error": "Échec du snapshot : {error}",
        "msg_delta_done": "Delta briefing ouvert dans le navigateur",
        "msg_delta_error": "Échec du delta briefing : {error}",
    },
}


# ---------------------------------------------------------------------------
# Display-independent logic (unit-tested without tkinter)
# ---------------------------------------------------------------------------

def _build_delta_html_file(prev_path: Path, now_path: Path) -> str:
    """
    Render the delta briefing for two snapshot files into a temp HTML file.

    Imports the delta machinery lazily so the manager window opens without
    pulling it until a briefing is actually requested.

    Args:
        prev_path: Earlier snapshot JSON.
        now_path:  Later snapshot JSON.

    Returns:
        Path of the written temporary .html file.

    Raises:
        ValueError: When the snapshots do not belong together or are in the
                    wrong order (surfaced to the status line by the caller).
    """
    import tempfile

    from .delta import compute_delta, render_delta_html
    from .snapshot import load_snapshot

    html = render_delta_html(
        compute_delta(load_snapshot(prev_path), load_snapshot(now_path)))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        return f.name


def _member_dict(name: str, source: str, kind: str = KIND_SOLUTION) -> dict[str, str]:
    """
    Map a (name, source path) pair to a member dict.

    For a **portfolio** the source is always a saved solution template, so it is
    stored under ``template``. For a **solution** a ``.json`` source is treated
    as an ART project template and anything else as a direct IssueTimes path.

    Args:
        name:   Member display name.
        source: Path string (template .json, IssueTimes .xlsx, or solution template).
        kind:   KIND_SOLUTION or KIND_PORTFOLIO of the parent config.

    Returns:
        Member dict with ``name`` plus either ``template`` or ``issue_times``.
    """
    source = source.strip()
    if kind == KIND_PORTFOLIO:
        key = "template"
    else:
        key = "template" if source.lower().endswith(".json") else "issue_times"
    return {"name": name.strip(), key: source}


def build_config_from_fields(
    name: str,
    framework: str,
    from_str: str,
    to_str: str,
    members: list[tuple[str, str]],
    mode: str,
    kind: str = KIND_SOLUTION,
    terminology: str = TERMINOLOGY_SAFE,
) -> SolutionConfig:
    """
    Build (and validate) a SolutionConfig from raw form field values.

    Empty member rows (no source path) are ignored. Date strings are passed
    through as-is; validation/parsing is delegated to parse_solution_config.

    Args:
        name:      Solution/portfolio name.
        framework: SAFe / LeSS / Nexus.
        from_str:  Optional from-date string (YYYY-MM-DD) or "".
        to_str:    Optional to-date string or "".
        members:   List of (member_name, source_path) pairs.
        mode:      MODE_POOLED or MODE_COMPARISON.
        kind:      KIND_SOLUTION (members are ARTs) or KIND_PORTFOLIO (members
                   are solution templates).

    Returns:
        Validated SolutionConfig.

    Raises:
        ValueError: If the resulting configuration is invalid.
    """
    member_dicts = [_member_dict(n, s, kind) for n, s in members if s.strip()]
    report: dict[str, Any] = {"modes": [mode], "terminology": terminology}
    if from_str.strip():
        report["from_date"] = from_str.strip()
    if to_str.strip():
        report["to_date"] = to_str.strip()
    return parse_solution_config({
        "schema": 1,
        "app": "situation_report",
        "kind": kind,
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


class SolutionManagerApp(tk.Tk):
    """tkinter window to build, save/load and run a solution configuration."""

    def __init__(self) -> None:
        super().__init__()
        self._lang = _load_lang_pref()
        self.title(self._tr("window_title"))
        self.configure(padx=14, pady=12)
        self.minsize(640, 480)

        self._name = tk.StringVar()
        self._terminology = tk.StringVar(value=TERMINOLOGY_SAFE)
        self._kind = tk.StringVar(value=KIND_SOLUTION)
        self._from = tk.StringVar()
        self._to = tk.StringVar()
        self._mode = tk.StringVar(value=MODE_POOLED)
        self._member_rows: list[dict] = []
        self._col_source_lbl: tk.Label | None = None
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._flag_btn: tk.Button | None = None
        self._status = tk.StringVar()

        self._create_flag_imgs()
        self._build_ui()

    def _tr(self, key: str) -> str:
        return _T.get(self._lang, _T[LANG_EN]).get(key, key)

    def _open_manual(self) -> None:
        """Open the hosted user manual PDF for the current language in the browser."""
        webbrowser.open(_MANUAL_URLS.get(self._lang, _MANUAL_URLS[LANG_EN]))

    def _create_flag_imgs(self) -> None:
        """Build language-flag PhotoImages by inline pixel drawing (same as the launcher)."""
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
        """Cycle the UI language through all supported languages and rebuild."""
        idx = _LANG_ORDER.index(self._lang) if self._lang in _LANG_ORDER else -1
        self._lang = _LANG_ORDER[(idx + 1) % len(_LANG_ORDER)]
        _save_lang_pref(self._lang)
        self._switch_lang()

    def _pick_date(self, var: tk.StringVar) -> None:
        """Open a modal calendar popup and write the selected ISO date to var."""
        from tkcalendar import Calendar
        try:
            current = date.fromisoformat(var.get().strip())
        except ValueError:
            current = date.today()
        top = tk.Toplevel(self)
        top.title(self._tr("dlg_pick_date"))
        top.resizable(False, False)
        top.grab_set()
        cal = Calendar(top, selectmode="day", year=current.year, month=current.month,
                       day=current.day, date_pattern="yyyy-mm-dd")
        cal.pack(padx=10, pady=10)

        def _confirm() -> None:
            var.set(cal.get_date())
            top.destroy()

        ttk.Button(top, text=self._tr("btn_ok"), command=_confirm).pack(pady=(0, 10))
        self.wait_window(top)

    def _col_source_text(self) -> str:
        """Member source-column header, depending on the selected kind."""
        return self._tr("col_source_portfolio" if self._kind.get() == KIND_PORTFOLIO
                        else "col_source")

    def _on_kind_change(self) -> None:
        """Refresh the member source-column header when the kind changes."""
        if self._col_source_lbl:
            self._col_source_lbl.configure(text=self._col_source_text())

    # -- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        top = tk.Frame(self)
        top.pack(fill="x")
        tk.Label(top, text=self._tr("lbl_name")).grid(row=0, column=0, sticky="w")
        tk.Entry(top, textvariable=self._name, width=34).grid(
            row=0, column=1, sticky="we", padx=(6, 16))
        tk.Label(top, text=self._tr("lbl_terminology")).grid(row=0, column=2, sticky="w")
        ttk.Combobox(top, textvariable=self._terminology, values=TERMINOLOGIES,
                     width=8, state="readonly").grid(row=0, column=3, padx=(6, 16))
        tk.Label(top, text=self._tr("lbl_kind")).grid(row=0, column=4, sticky="w")
        kind_box = ttk.Combobox(top, textvariable=self._kind, values=KINDS,
                                width=10, state="readonly")
        kind_box.grid(row=0, column=5)
        kind_box.bind("<<ComboboxSelected>>", lambda *_: self._on_kind_change())

        right = tk.Frame(top)
        right.grid(row=0, column=6, rowspan=2, sticky="ne", padx=(12, 0))
        self._flag_btn = tk.Button(
            right, image=self._flag_imgs.get(self._lang), relief="flat", bd=0,
            cursor="hand2", command=self._toggle_language)
        self._flag_btn.pack(side="right", padx=(4, 0))
        ttk.Button(right, text="?", width=2, command=self._open_manual).pack(side="right")

        tk.Label(top, text=self._tr("lbl_from")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        from_f = tk.Frame(top)
        from_f.grid(row=1, column=1, sticky="w", padx=(6, 16), pady=(6, 0))
        tk.Entry(from_f, textvariable=self._from, width=12).pack(side="left")
        ttk.Button(from_f, text="📅", width=3,
                   command=lambda: self._pick_date(self._from)).pack(side="left", padx=(2, 0))
        tk.Label(top, text=self._tr("lbl_to")).grid(row=1, column=2, sticky="w", pady=(6, 0))
        to_f = tk.Frame(top)
        to_f.grid(row=1, column=3, sticky="w", padx=(6, 16), pady=(6, 0))
        tk.Entry(to_f, textvariable=self._to, width=12).pack(side="left")
        ttk.Button(to_f, text="📅", width=3,
                   command=lambda: self._pick_date(self._to)).pack(side="left", padx=(2, 0))
        top.columnconfigure(1, weight=1)

        tk.Label(self, text=self._tr("sec_members"),
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(12, 2))
        head = tk.Frame(self)
        head.pack(fill="x")
        tk.Label(head, text=self._tr("col_name"), width=20, anchor="w").grid(row=0, column=0)
        self._col_source_lbl = tk.Label(head, text=self._col_source_text(), anchor="w")
        self._col_source_lbl.grid(row=0, column=1, sticky="w")
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
        ttk.Button(btns, text=self._tr("btn_delta"), command=self._delta).pack(
            side="right", padx=(0, 6))
        ttk.Button(btns, text=self._tr("btn_snapshot"), command=self._snapshot).pack(
            side="right", padx=(0, 6))

        tk.Label(self, textvariable=self._status, fg="#2980b9", anchor="w").pack(
            fill="x", pady=(10, 0))

        self._add_member_row()

    def _switch_lang(self) -> None:
        # self._lang is already set by the caller (_toggle_language).
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
        if self._kind.get() == KIND_PORTFOLIO:
            filetypes = [("Solution template", "*.json"), ("All files", "*.*")]
        else:
            filetypes = [("Solution member", "*.json *.xlsx"),
                         ("Project template", "*.json"),
                         ("IssueTimes", "*.xlsx"), ("All files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
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
        self._terminology.set(TERMINOLOGY_SAFE)
        self._kind.set(KIND_SOLUTION)
        self._on_kind_change()
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
        self._terminology.set(cfg.terminology)
        self._kind.set(cfg.kind)
        self._on_kind_change()
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
                self._name.get(), FRAMEWORK_SAFE,
                self._from.get(), self._to.get(),
                self._collect_members(), self._mode.get(),
                kind=self._kind.get(), terminology=self._terminology.get())
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
            filetypes=[("HTML", "*.html"), ("PDF", "*.pdf")])
        if not out:
            return
        self._status.set(self._tr("msg_generating"))
        self.update_idletasks()

        out_path = Path(out)
        is_pdf = out_path.suffix.lower() == ".pdf"
        mode = self._mode.get()
        terminology = cfg.terminology

        def worker() -> None:
            if is_pdf:
                ok = render_pdf(cfg, out_path, mode=mode, terminology=terminology,
                                log=lambda *_: None)
            else:
                render = (render_comparison_html if mode == MODE_COMPARISON
                          else render_pooled_html)
                html = render(cfg, terminology=terminology, log=lambda *_: None)
                ok = bool(html)
                if html:
                    out_path.write_text(html, encoding="utf-8")
            self.after(0, lambda: self._done(out, ok))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, out: str, ok: bool) -> None:
        if ok:
            self._status.set(self._tr("msg_report_done").format(path=out))
            webbrowser.open(Path(out).resolve().as_uri())
        else:
            self._status.set(self._tr("msg_no_figures"))

    def _snapshot(self) -> None:
        """Freeze the current configuration's report state to a JSON file (D2)."""
        cfg = self._build_config()
        if cfg is None:
            return
        path = filedialog.asksaveasfilename(
            title=self._tr("dlg_save_snapshot"), defaultextension=".json",
            initialfile=f"{cfg.name}_snapshot_{date.today().isoformat()}.json",
            filetypes=[("JSON", "*.json")])
        if not path:
            return
        self._status.set(self._tr("msg_snapshot_saving"))
        self.update_idletasks()

        def worker() -> None:
            try:
                from .snapshot import build_snapshot, save_snapshot

                snap = build_snapshot(cfg, log=lambda *_: None)
                save_snapshot(Path(path), snap)
                msg = self._tr("msg_snapshot_done").format(path=path)
            except Exception as exc:
                msg = self._tr("msg_snapshot_error").format(error=exc)
            self.after(0, lambda: self._status.set(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _delta(self) -> None:
        """Pick two snapshot files and open their delta briefing (D2)."""
        prev = filedialog.askopenfilename(
            title=self._tr("dlg_delta_prev"), filetypes=[("JSON", "*.json")])
        if not prev:
            return
        now = filedialog.askopenfilename(
            title=self._tr("dlg_delta_now"), filetypes=[("JSON", "*.json")])
        if not now:
            return

        def worker() -> None:
            try:
                tmp = _build_delta_html_file(Path(prev), Path(now))
                webbrowser.open(Path(tmp).resolve().as_uri())
                msg = self._tr("msg_delta_done")
            except Exception as exc:
                msg = self._tr("msg_delta_error").format(error=exc)
            self.after(0, lambda: self._status.set(msg))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:  # pragma: no cover - requires a display
    """Launch the Solutions & Portfolios manager window."""
    SolutionManagerApp().mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()
