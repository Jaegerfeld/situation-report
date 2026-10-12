# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       12.10.2026
# Geändert:       12.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   tkinter-Oberfläche des Harmonisierungs-Scores: Arbeitsbereich wählen
#   oder als Beispiel anlegen, Prozesse pflegen, eine Bewertung erfassen
#   (je Frage Wert 0–4 oder „unbekannt" plus Beleggrad), die Entscheidung
#   des Boards eintragen und die Entscheider-Matrix erzeugen. Fünf Sprachen
#   über den Flaggen-Umschalter wie in den übrigen Modul-GUIs. Die
#   display-unabhängige Logik (Übersetzungen, Formular-Validierung) ist
#   getrennt gehalten und unit-getestet; der tkinter-Teil wird im Test
#   nicht instanziiert.
# =============================================================================

from __future__ import annotations

import json
import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .examples import write_example
from .model import (
    ASSESSMENTS_DIR,
    DECISION_BRAND_SPECIFIC,
    DECISION_OPEN,
    DECISION_STANDARDISE,
    DECISIONS,
    DECISIONS_FILE,
    EVIDENCE_DOCUMENTED,
    EVIDENCE_ESTIMATED,
    EVIDENCE_HEARSAY,
    EVIDENCE_LEVELS,
    PROCESSES_FILE,
    SCALE_MAX,
    SCALE_MIN,
    Answer,
    Assessment,
    Decision,
    HarmonisationError,
    Process,
    Workspace,
    assessment_filename,
    assessment_to_json,
    decisions_to_json,
    load_workspace,
    processes_to_json,
    write_json,
)
from .render import render_html

# ---------------------------------------------------------------------------
# Sprache (geteilte Präferenzdatei mit Launcher/Portfolio)
# ---------------------------------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_RO = "ro"
LANG_PT = "pt"
LANG_FR = "fr"
_LANG_ORDER = [LANG_DE, LANG_EN, LANG_RO, LANG_PT, LANG_FR]
_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"

_MANUAL_BASE = "https://jaegerfeld.github.io/situation-report/"
_MANUAL_URLS: dict[str, str] = {
    LANG_DE: _MANUAL_BASE + "harmonisation_Benutzerhandbuch.pdf",
    LANG_EN: _MANUAL_BASE + "harmonisation_UserManual.pdf",
    LANG_RO: _MANUAL_BASE + "harmonisation_ManualUtilizator.pdf",
    LANG_PT: _MANUAL_BASE + "harmonisation_ManualUtilizador.pdf",
    LANG_FR: _MANUAL_BASE + "harmonisation_ManuelUtilisateur.pdf",
}


def _load_lang_pref() -> str:
    try:
        with open(_PREFS_PATH) as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in _LANG_ORDER else LANG_EN
    except Exception:
        return LANG_EN


def _save_lang_pref(lang: str) -> None:
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
# Übersetzungen
# ---------------------------------------------------------------------------

_T: dict[str, dict[str, str]] = {
    LANG_DE: {
        "window_title": "Harmonisierungs-Score",
        "menu_help": "Hilfe", "menu_manual": "Manual", "tip_language": "Sprache wechseln",
        "lbl_workspace": "Arbeitsbereich (Ordner)", "btn_browse": "Durchsuchen…",
        "btn_example": "Beispiel anlegen…", "btn_reload": "Neu laden",
        "dlg_workspace": "Arbeitsbereich wählen", "dlg_example": "Ordner für das Beispiel wählen",
        "tab_processes": "Prozesse", "tab_assessment": "Bewertung", "tab_decision": "Entscheidung",
        "lbl_process_id": "Kürzel", "lbl_process_name": "Name", "lbl_owner": "Owner",
        "lbl_brands": "Marken/Einheiten (Komma)", "btn_add_process": "Prozess hinzufügen",
        "lbl_process": "Prozess", "lbl_assessor": "Bewertet von", "lbl_date": "Datum (JJJJ-MM-TT)",
        "lbl_note": "Anmerkung", "btn_save_assessment": "Bewertung speichern",
        "lbl_scale_hint": "0 = trifft nicht zu · 4 = trifft voll zu · ? = unbekannt (zulässig)",
        "ev_documented": "belegt", "ev_estimated": "geschätzt", "ev_hearsay": "Hörensagen",
        "lbl_decision": "Entscheidung des Boards", "lbl_depth": "Tiefe (Wortlaut des Boards)",
        "lbl_body": "Gremium", "btn_save_decision": "Entscheidung speichern",
        "dec_standardise": "standardisieren", "dec_brand_specific": "markenspezifisch", "dec_open": "offen",
        "lbl_report_lang": "Sprache der Matrix", "btn_matrix": "Matrix erzeugen …",
        "msg_need_workspace": "Bitte zuerst einen Arbeitsbereich wählen oder das Beispiel anlegen.",
        "msg_loaded": "Geladen: {n} Prozesse, {a} Bewertungen", "msg_error": "Fehler: {error}",
        "msg_invalid": "Ungültige Eingabe: {error}", "msg_saved": "Gespeichert: {path}",
        "msg_matrix": "Matrix erzeugt: {path}", "msg_example": "Beispiel angelegt in {path}",
        "msg_no_process": "Bitte einen Prozess wählen.",
    },
    LANG_EN: {
        "window_title": "Harmonisation Score",
        "menu_help": "Help", "menu_manual": "Manual", "tip_language": "Change language",
        "lbl_workspace": "Workspace (folder)", "btn_browse": "Browse…",
        "btn_example": "Create example…", "btn_reload": "Reload",
        "dlg_workspace": "Choose workspace", "dlg_example": "Choose a folder for the example",
        "tab_processes": "Processes", "tab_assessment": "Assessment", "tab_decision": "Decision",
        "lbl_process_id": "Id", "lbl_process_name": "Name", "lbl_owner": "Owner",
        "lbl_brands": "Brands/units (comma)", "btn_add_process": "Add process",
        "lbl_process": "Process", "lbl_assessor": "Assessed by", "lbl_date": "Date (YYYY-MM-DD)",
        "lbl_note": "Note", "btn_save_assessment": "Save assessment",
        "lbl_scale_hint": "0 = does not apply · 4 = fully applies · ? = unknown (allowed)",
        "ev_documented": "documented", "ev_estimated": "estimated", "ev_hearsay": "hearsay",
        "lbl_decision": "Board decision", "lbl_depth": "Depth (board's wording)",
        "lbl_body": "Body", "btn_save_decision": "Save decision",
        "dec_standardise": "standardise", "dec_brand_specific": "brand-specific", "dec_open": "open",
        "lbl_report_lang": "Matrix language", "btn_matrix": "Generate matrix …",
        "msg_need_workspace": "Please choose a workspace or create the example first.",
        "msg_loaded": "Loaded: {n} processes, {a} assessments", "msg_error": "Error: {error}",
        "msg_invalid": "Invalid input: {error}", "msg_saved": "Saved: {path}",
        "msg_matrix": "Matrix generated: {path}", "msg_example": "Example created in {path}",
        "msg_no_process": "Please choose a process.",
    },
    LANG_RO: {
        "window_title": "Scor de armonizare",
        "menu_help": "Ajutor", "menu_manual": "Manual", "tip_language": "Schimbă limba",
        "lbl_workspace": "Spațiu de lucru (dosar)", "btn_browse": "Răsfoire…",
        "btn_example": "Creează exemplul…", "btn_reload": "Reîncarcă",
        "dlg_workspace": "Alegeți spațiul de lucru", "dlg_example": "Alegeți un dosar pentru exemplu",
        "tab_processes": "Procese", "tab_assessment": "Evaluare", "tab_decision": "Decizie",
        "lbl_process_id": "Id", "lbl_process_name": "Nume", "lbl_owner": "Responsabil",
        "lbl_brands": "Mărci/unități (virgulă)", "btn_add_process": "Adaugă proces",
        "lbl_process": "Proces", "lbl_assessor": "Evaluat de", "lbl_date": "Data (AAAA-LL-ZZ)",
        "lbl_note": "Notă", "btn_save_assessment": "Salvează evaluarea",
        "lbl_scale_hint": "0 = nu se aplică · 4 = se aplică pe deplin · ? = necunoscut (permis)",
        "ev_documented": "documentat", "ev_estimated": "estimat", "ev_hearsay": "din auzite",
        "lbl_decision": "Decizia board-ului", "lbl_depth": "Profunzime (formularea board-ului)",
        "lbl_body": "Organ", "btn_save_decision": "Salvează decizia",
        "dec_standardise": "standardizare", "dec_brand_specific": "specific mărcii", "dec_open": "deschis",
        "lbl_report_lang": "Limba matricei", "btn_matrix": "Generează matricea …",
        "msg_need_workspace": "Alegeți mai întâi un spațiu de lucru sau creați exemplul.",
        "msg_loaded": "Încărcat: {n} procese, {a} evaluări", "msg_error": "Eroare: {error}",
        "msg_invalid": "Intrare nevalidă: {error}", "msg_saved": "Salvat: {path}",
        "msg_matrix": "Matrice generată: {path}", "msg_example": "Exemplu creat în {path}",
        "msg_no_process": "Alegeți un proces.",
    },
    LANG_PT: {
        "window_title": "Score de harmonização",
        "menu_help": "Ajuda", "menu_manual": "Manual", "tip_language": "Mudar idioma",
        "lbl_workspace": "Área de trabalho (pasta)", "btn_browse": "Procurar…",
        "btn_example": "Criar exemplo…", "btn_reload": "Recarregar",
        "dlg_workspace": "Escolher área de trabalho", "dlg_example": "Escolher uma pasta para o exemplo",
        "tab_processes": "Processos", "tab_assessment": "Avaliação", "tab_decision": "Decisão",
        "lbl_process_id": "Id", "lbl_process_name": "Nome", "lbl_owner": "Responsável",
        "lbl_brands": "Marcas/unidades (vírgula)", "btn_add_process": "Adicionar processo",
        "lbl_process": "Processo", "lbl_assessor": "Avaliado por", "lbl_date": "Data (AAAA-MM-DD)",
        "lbl_note": "Nota", "btn_save_assessment": "Guardar avaliação",
        "lbl_scale_hint": "0 = não se aplica · 4 = aplica-se totalmente · ? = desconhecido (permitido)",
        "ev_documented": "documentado", "ev_estimated": "estimado", "ev_hearsay": "por ouvir dizer",
        "lbl_decision": "Decisão do board", "lbl_depth": "Profundidade (palavras do board)",
        "lbl_body": "Órgão", "btn_save_decision": "Guardar decisão",
        "dec_standardise": "padronizar", "dec_brand_specific": "específico da marca", "dec_open": "em aberto",
        "lbl_report_lang": "Idioma da matriz", "btn_matrix": "Gerar matriz …",
        "msg_need_workspace": "Escolha primeiro uma área de trabalho ou crie o exemplo.",
        "msg_loaded": "Carregado: {n} processos, {a} avaliações", "msg_error": "Erro: {error}",
        "msg_invalid": "Entrada inválida: {error}", "msg_saved": "Guardado: {path}",
        "msg_matrix": "Matriz gerada: {path}", "msg_example": "Exemplo criado em {path}",
        "msg_no_process": "Escolha um processo.",
    },
    LANG_FR: {
        "window_title": "Score d'harmonisation",
        "menu_help": "Aide", "menu_manual": "Manuel", "tip_language": "Changer de langue",
        "lbl_workspace": "Espace de travail (dossier)", "btn_browse": "Parcourir…",
        "btn_example": "Créer l'exemple…", "btn_reload": "Recharger",
        "dlg_workspace": "Choisir l'espace de travail", "dlg_example": "Choisir un dossier pour l'exemple",
        "tab_processes": "Processus", "tab_assessment": "Évaluation", "tab_decision": "Décision",
        "lbl_process_id": "Id", "lbl_process_name": "Nom", "lbl_owner": "Responsable",
        "lbl_brands": "Marques/unités (virgule)", "btn_add_process": "Ajouter un processus",
        "lbl_process": "Processus", "lbl_assessor": "Évalué par", "lbl_date": "Date (AAAA-MM-JJ)",
        "lbl_note": "Remarque", "btn_save_assessment": "Enregistrer l'évaluation",
        "lbl_scale_hint": "0 = ne s'applique pas · 4 = s'applique pleinement · ? = inconnu (autorisé)",
        "ev_documented": "documenté", "ev_estimated": "estimé", "ev_hearsay": "par ouï-dire",
        "lbl_decision": "Décision du board", "lbl_depth": "Profondeur (termes du board)",
        "lbl_body": "Instance", "btn_save_decision": "Enregistrer la décision",
        "dec_standardise": "standardiser", "dec_brand_specific": "propre à la marque", "dec_open": "ouvert",
        "lbl_report_lang": "Langue de la matrice", "btn_matrix": "Générer la matrice …",
        "msg_need_workspace": "Veuillez d'abord choisir un espace de travail ou créer l'exemple.",
        "msg_loaded": "Chargé : {n} processus, {a} évaluations", "msg_error": "Erreur : {error}",
        "msg_invalid": "Entrée invalide : {error}", "msg_saved": "Enregistré : {path}",
        "msg_matrix": "Matrice générée : {path}", "msg_example": "Exemple créé dans {path}",
        "msg_no_process": "Veuillez choisir un processus.",
    },
}


def _tr(lang: str, key: str) -> str:
    """Übersetze `key`; EN-Fallback, wenn die Sprache/der Key fehlt."""
    return _T.get(lang, _T[LANG_EN]).get(key) or _T[LANG_EN][key]


# ---------------------------------------------------------------------------
# Display-unabhängige Formular-Logik (unit-getestet)
# ---------------------------------------------------------------------------

UNKNOWN = "?"   # Darstellung von „unbekannt" in den Formularen
_EVIDENCE_KEYS = {EVIDENCE_DOCUMENTED: "ev_documented", EVIDENCE_ESTIMATED: "ev_estimated",
                  EVIDENCE_HEARSAY: "ev_hearsay"}
_DECISION_KEYS = {DECISION_STANDARDISE: "dec_standardise",
                  DECISION_BRAND_SPECIFIC: "dec_brand_specific", DECISION_OPEN: "dec_open"}


def _parse_day(value: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("date must be YYYY-MM-DD") from None


def parse_process_form(process_id: str, name: str, owner: str = "",
                       brands: str = "") -> Process:
    """Validate the 'add process' fields; brands are comma-separated."""
    pid = process_id.strip()
    if not pid or not all(ch.isalnum() or ch in "-_" for ch in pid):
        raise ValueError("process id must be letters, digits, '-' or '_'")
    if not name.strip():
        raise ValueError("process name is required")
    return Process(pid, name.strip(), owner.strip(),
                   tuple(b.strip() for b in brands.split(",") if b.strip()))


def parse_assessment_form(process: str, assessor: str, day: str,
                          answers: dict[str, tuple[str, str]],
                          note: str = "") -> Assessment:
    """
    Validate an assessment form.

    Args:
        answers: {question_id: (value, evidence)} with value '0'..'4' or '?'
                 and evidence one of the EVIDENCE_LEVELS.
    """
    if not process.strip():
        raise ValueError("process is required")
    parsed: dict[str, Answer] = {}
    for qid, (value, evidence) in answers.items():
        value = value.strip()
        if evidence not in EVIDENCE_LEVELS:
            raise ValueError(f"evidence for {qid} is invalid")
        if value in ("", UNKNOWN):
            parsed[qid] = Answer(None, evidence)
            continue
        try:
            n = int(value)
        except ValueError:
            raise ValueError(f"value for {qid} must be {SCALE_MIN}..{SCALE_MAX} or {UNKNOWN}") from None
        if not SCALE_MIN <= n <= SCALE_MAX:
            raise ValueError(f"value for {qid} must be {SCALE_MIN}..{SCALE_MAX} or {UNKNOWN}")
        parsed[qid] = Answer(n, evidence)
    return Assessment(process.strip(), assessor.strip(), _parse_day(day), parsed, note.strip())


def parse_decision_form(process: str, decision: str, depth: str = "",
                        day: str = "", body: str = "") -> Decision:
    if not process.strip():
        raise ValueError("process is required")
    if decision not in DECISIONS:
        raise ValueError("decision is invalid")
    when = _parse_day(day) if day.strip() else None
    return Decision(process.strip(), decision, depth.strip(), when, body.strip())


# ---------------------------------------------------------------------------
# tkinter-GUI (nicht im Test instanziiert)
# ---------------------------------------------------------------------------

class HarmonisationApp:
    """Workspace folder on top, three tabs below, the matrix button at the bottom."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = _load_lang_pref()
        self.workspace = tk.StringVar(value="")
        self.report_lang = tk.StringVar(value=self.lang)
        self.status = tk.StringVar(value="")
        self.ws: Workspace | None = None
        self._answer_vars: dict[str, tuple[tk.StringVar, tk.StringVar]] = {}
        self._flag_imgs: dict[str, tk.PhotoImage] = {}
        self._create_flag_imgs()
        self._build()

    def _t(self, key: str) -> str:
        return _tr(self.lang, key)

    # -- Sprache ------------------------------------------------------------

    def _create_flag_imgs(self) -> None:
        """Build PhotoImage flags for all supported languages via inline pixels."""
        W, H = 32, 20

        def stripes_h(colours: list[str]) -> tk.PhotoImage:
            img = tk.PhotoImage(width=W, height=H)
            for y in range(H):
                c = colours[y * len(colours) // H]
                img.put("{" + " ".join([c] * W) + "}", to=(0, y))
            return img

        def stripes_v(colours: list[str], split: list[int] | None = None) -> tk.PhotoImage:
            img = tk.PhotoImage(width=W, height=H)
            bounds = split or [W * (i + 1) // len(colours) for i in range(len(colours))]
            for y in range(H):
                row = [next(c for c, b in zip(colours, bounds) if x < b) for x in range(W)]
                img.put("{" + " ".join(row) + "}", to=(0, y))
            return img

        gb = tk.PhotoImage(width=W, height=H)
        for y in range(H):
            row: list[str] = []
            for x in range(W):
                cx, cy = abs(x - (W - 1) / 2), abs(y - (H - 1) / 2)
                nx, ny = x / (W - 1), y / (H - 1)
                if cx < W * 0.13 or cy < H * 0.13:
                    row.append("#C8102E")
                elif cx < W * 0.24 or cy < H * 0.24 or abs(nx - ny) < 0.16 or abs(nx - (1 - ny)) < 0.16:
                    row.append("#FFFFFF")
                else:
                    row.append("#012169")
            gb.put("{" + " ".join(row) + "}", to=(0, y))

        self._flag_imgs = {
            LANG_DE: stripes_h(["#000000", "#DD0000", "#FFCC00"]),
            LANG_EN: gb,
            LANG_RO: stripes_v(["#002B7F", "#FCD116", "#CE1126"]),
            LANG_PT: stripes_v(["#006600", "#FF0000"], [W * 2 // 5, W]),
            LANG_FR: stripes_v(["#002395", "#FFFFFF", "#ED2939"]),
        }

    def _toggle_language(self) -> None:
        idx = _LANG_ORDER.index(self.lang) if self.lang in _LANG_ORDER else -1
        self.lang = _LANG_ORDER[(idx + 1) % len(_LANG_ORDER)]
        _save_lang_pref(self.lang)
        for child in self.root.winfo_children():
            child.destroy()
        self._build()

    def _open_manual(self) -> None:
        webbrowser.open(_MANUAL_URLS.get(self.lang, _MANUAL_URLS[LANG_EN]))

    # -- Aufbau -------------------------------------------------------------

    def _build(self) -> None:
        self.root.title(self._t("window_title"))
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=self._t("menu_help"), menu=help_menu)
        help_menu.add_command(label=self._t("menu_manual"), command=self._open_manual)
        self.root.config(menu=menubar)

        frm = ttk.Frame(self.root, padding=12)
        frm.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text=self._t("lbl_workspace")).grid(column=0, row=0, sticky="w")
        ttk.Entry(frm, textvariable=self.workspace, width=56).grid(column=1, row=0, sticky="ew", padx=4)
        bar = ttk.Frame(frm)
        bar.grid(column=2, row=0, sticky="e")
        ttk.Button(bar, text=self._t("btn_browse"), command=self._browse).pack(side="left")
        ttk.Button(bar, text=self._t("btn_example"), command=self._create_example).pack(side="left", padx=(4, 0))
        ttk.Button(bar, text=self._t("btn_reload"), command=self._reload).pack(side="left", padx=(4, 0))
        tk.Button(bar, image=self._flag_imgs[self.lang], command=self._toggle_language,
                  relief="flat", cursor="hand2", bd=0, padx=4).pack(side="left", padx=(8, 0))

        self.tabs = ttk.Notebook(frm)
        self.tabs.grid(column=0, columnspan=3, row=1, sticky="nsew", pady=(10, 6))
        frm.rowconfigure(1, weight=1)
        self.tab_processes = ttk.Frame(self.tabs, padding=8)
        self.tab_assessment = ttk.Frame(self.tabs, padding=8)
        self.tab_decision = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(self.tab_processes, text=self._t("tab_processes"))
        self.tabs.add(self.tab_assessment, text=self._t("tab_assessment"))
        self.tabs.add(self.tab_decision, text=self._t("tab_decision"))
        self._build_processes_tab()
        self._build_assessment_tab()
        self._build_decision_tab()

        bottom = ttk.Frame(frm)
        bottom.grid(column=0, columnspan=3, row=2, sticky="ew")
        ttk.Label(bottom, text=self._t("lbl_report_lang")).pack(side="left")
        ttk.Combobox(bottom, textvariable=self.report_lang, values=_LANG_ORDER, width=4,
                     state="readonly").pack(side="left", padx=(4, 12))
        ttk.Button(bottom, text=self._t("btn_matrix"), command=self._generate).pack(side="left")
        ttk.Label(frm, textvariable=self.status, foreground="#14304a").grid(
            column=0, columnspan=3, row=3, sticky="w", pady=(6, 0))
        if self.workspace.get():
            self._reload()

    def _build_processes_tab(self) -> None:
        tab = self.tab_processes
        self.process_list = tk.Listbox(tab, height=8, width=70)
        self.process_list.grid(column=0, columnspan=4, row=0, sticky="ew", pady=(0, 8))
        self.p_vars = {k: tk.StringVar() for k in ("id", "name", "owner", "brands")}
        for col, (key, label) in enumerate((("id", "lbl_process_id"), ("name", "lbl_process_name"),
                                            ("owner", "lbl_owner"), ("brands", "lbl_brands"))):
            ttk.Label(tab, text=self._t(label)).grid(column=col, row=1, sticky="w")
            ttk.Entry(tab, textvariable=self.p_vars[key], width=18 if key != "name" else 26).grid(
                column=col, row=2, sticky="w", padx=(0, 6))
        ttk.Button(tab, text=self._t("btn_add_process"), command=self._add_process).grid(
            column=0, row=3, sticky="w", pady=(8, 0))

    def _build_assessment_tab(self) -> None:
        tab = self.tab_assessment
        self.a_process = tk.StringVar()
        self.a_assessor = tk.StringVar()
        self.a_date = tk.StringVar(value=date.today().isoformat())
        self.a_note = tk.StringVar()
        head = ttk.Frame(tab)
        head.grid(column=0, row=0, sticky="ew")
        ttk.Label(head, text=self._t("lbl_process")).pack(side="left")
        self.a_process_box = ttk.Combobox(head, textvariable=self.a_process, width=22, state="readonly")
        self.a_process_box.pack(side="left", padx=(4, 10))
        ttk.Label(head, text=self._t("lbl_assessor")).pack(side="left")
        ttk.Entry(head, textvariable=self.a_assessor, width=18).pack(side="left", padx=(4, 10))
        ttk.Label(head, text=self._t("lbl_date")).pack(side="left")
        ttk.Entry(head, textvariable=self.a_date, width=12).pack(side="left", padx=(4, 0))
        ttk.Label(tab, text=self._t("lbl_scale_hint"), foreground="#5b6b7c").grid(
            column=0, row=1, sticky="w", pady=(4, 4))

        # Scrollbare Fragenliste
        canvas = tk.Canvas(tab, height=320, highlightthickness=0)
        scroll = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        self.q_frame = ttk.Frame(canvas)
        self.q_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.q_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(column=0, row=2, sticky="nsew")
        scroll.grid(column=1, row=2, sticky="ns")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        foot = ttk.Frame(tab)
        foot.grid(column=0, row=3, sticky="ew", pady=(6, 0))
        ttk.Label(foot, text=self._t("lbl_note")).pack(side="left")
        ttk.Entry(foot, textvariable=self.a_note, width=50).pack(side="left", padx=(4, 10))
        ttk.Button(foot, text=self._t("btn_save_assessment"), command=self._save_assessment).pack(side="left")

    def _build_decision_tab(self) -> None:
        tab = self.tab_decision
        self.d_process = tk.StringVar()
        self.d_decision = tk.StringVar(value=DECISION_OPEN)
        self.d_depth = tk.StringVar()
        self.d_date = tk.StringVar(value=date.today().isoformat())
        self.d_body = tk.StringVar(value="Board")
        rows = (("lbl_process", None), ("lbl_decision", None), ("lbl_depth", self.d_depth),
                ("lbl_date", self.d_date), ("lbl_body", self.d_body))
        for row, (label, var) in enumerate(rows):
            ttk.Label(tab, text=self._t(label)).grid(column=0, row=row, sticky="w", pady=2)
            if label == "lbl_process":
                self.d_process_box = ttk.Combobox(tab, textvariable=self.d_process, width=30, state="readonly")
                self.d_process_box.grid(column=1, row=row, sticky="w", padx=4)
                self.d_process_box.bind("<<ComboboxSelected>>", lambda e: self._load_decision())
            elif label == "lbl_decision":
                self.d_decision_box = ttk.Combobox(
                    tab, width=30, state="readonly",
                    values=[self._t(k) for k in _DECISION_KEYS.values()])
                self.d_decision_box.grid(column=1, row=row, sticky="w", padx=4)
                self.d_decision_box.current(list(_DECISION_KEYS).index(DECISION_OPEN))
            else:
                ttk.Entry(tab, textvariable=var, width=60).grid(column=1, row=row, sticky="w", padx=4)
        ttk.Button(tab, text=self._t("btn_save_decision"), command=self._save_decision).grid(
            column=0, row=len(rows), sticky="w", pady=(10, 0))

    # -- Arbeitsbereich -----------------------------------------------------

    def _root(self) -> Path | None:
        text = self.workspace.get().strip()
        if not text:
            self.status.set(self._t("msg_need_workspace"))
            return None
        return Path(text)

    def _browse(self) -> None:
        folder = filedialog.askdirectory(title=self._t("dlg_workspace"))
        if folder:
            self.workspace.set(folder)
            self._reload()

    def _create_example(self) -> None:
        folder = filedialog.askdirectory(title=self._t("dlg_example"))
        if not folder:
            return
        write_example(Path(folder))
        self.workspace.set(folder)
        self.status.set(self._t("msg_example").format(path=folder))
        self._reload()

    def _reload(self) -> None:
        root = self._root()
        if root is None:
            return
        try:
            self.ws = load_workspace(root)
        except HarmonisationError as exc:
            self.ws = None
            self.status.set(self._t("msg_error").format(error=exc))
            return
        self._refresh_processes()
        self._refresh_questions()
        self.status.set(self._t("msg_loaded").format(n=len(self.ws.processes),
                                                     a=len(self.ws.assessments)))

    def _refresh_processes(self) -> None:
        self.process_list.delete(0, "end")
        ids: list[str] = []
        if self.ws is not None:
            for p in self.ws.processes:
                self.process_list.insert("end", f"{p.id}  —  {p.name}" + (f"  ({p.owner})" if p.owner else ""))
                ids.append(p.id)
        self.a_process_box["values"] = ids
        self.d_process_box["values"] = ids
        if ids and self.a_process.get() not in ids:
            self.a_process.set(ids[0])
        if ids and self.d_process.get() not in ids:
            self.d_process.set(ids[0])
            self._load_decision()

    def _refresh_questions(self) -> None:
        for child in self.q_frame.winfo_children():
            child.destroy()
        self._answer_vars = {}
        if self.ws is None:
            return
        evidence_labels = [self._t(k) for k in _EVIDENCE_KEYS.values()]
        row = 0
        for dim in self.ws.catalogue.dimensions:
            ttk.Label(self.q_frame, text=dim.label(self.lang), font=("Segoe UI", 10, "bold")).grid(
                column=0, columnspan=8, row=row, sticky="w", pady=(8, 2))
            row += 1
            for q in dim.questions:
                value = tk.StringVar(value=UNKNOWN)
                evidence = tk.StringVar(value=evidence_labels[1])
                self._answer_vars[q.id] = (value, evidence)
                ttk.Label(self.q_frame, text=q.label(self.lang), wraplength=520).grid(
                    column=0, row=row, sticky="w")
                for col, opt in enumerate([str(n) for n in range(SCALE_MIN, SCALE_MAX + 1)] + [UNKNOWN]):
                    ttk.Radiobutton(self.q_frame, text=opt, value=opt, variable=value).grid(
                        column=1 + col, row=row, padx=1)
                ttk.Combobox(self.q_frame, textvariable=evidence, values=evidence_labels, width=11,
                             state="readonly").grid(column=7, row=row, padx=(6, 0))
                row += 1

    # -- Aktionen -----------------------------------------------------------

    def _add_process(self) -> None:
        root = self._root()
        if root is None or self.ws is None:
            return
        try:
            new = parse_process_form(*(self.p_vars[k].get() for k in ("id", "name", "owner", "brands")))
            if any(p.id == new.id for p in self.ws.processes):
                raise ValueError(f"process id '{new.id}' already exists")
        except ValueError as exc:
            self.status.set(self._t("msg_invalid").format(error=exc))
            return
        write_json(root / PROCESSES_FILE, processes_to_json(self.ws.processes + (new,)))
        for var in self.p_vars.values():
            var.set("")
        self._reload()
        self.status.set(self._t("msg_saved").format(path=PROCESSES_FILE))

    def _evidence_from_label(self, label: str) -> str:
        for level, key in _EVIDENCE_KEYS.items():
            if self._t(key) == label:
                return level
        return EVIDENCE_ESTIMATED

    def _save_assessment(self) -> None:
        root = self._root()
        if root is None or self.ws is None:
            return
        if not self.a_process.get():
            self.status.set(self._t("msg_no_process"))
            return
        answers = {qid: (value.get(), self._evidence_from_label(evidence.get()))
                   for qid, (value, evidence) in self._answer_vars.items()}
        try:
            a = parse_assessment_form(self.a_process.get(), self.a_assessor.get(),
                                      self.a_date.get(), answers, self.a_note.get())
        except ValueError as exc:
            self.status.set(self._t("msg_invalid").format(error=exc))
            return
        path = root / ASSESSMENTS_DIR / assessment_filename(a)
        if path.exists() and not messagebox.askyesno(self._t("window_title"), f"{path.name}\n→ overwrite?"):
            return
        write_json(path, assessment_to_json(a))
        self._reload()
        self.status.set(self._t("msg_saved").format(path=path.name))

    def _load_decision(self) -> None:
        if self.ws is None:
            return
        d = self.ws.decisions.get(self.d_process.get())
        decision = d.decision if d else DECISION_OPEN
        self.d_decision_box.current(list(_DECISION_KEYS).index(decision))
        self.d_depth.set(d.depth if d else "")
        self.d_date.set(d.day.isoformat() if d and d.day else date.today().isoformat())
        self.d_body.set(d.body if d and d.body else "Board")

    def _save_decision(self) -> None:
        root = self._root()
        if root is None or self.ws is None:
            return
        if not self.d_process.get():
            self.status.set(self._t("msg_no_process"))
            return
        decision = list(_DECISION_KEYS)[self.d_decision_box.current()]
        try:
            d = parse_decision_form(self.d_process.get(), decision, self.d_depth.get(),
                                    self.d_date.get(), self.d_body.get())
        except ValueError as exc:
            self.status.set(self._t("msg_invalid").format(error=exc))
            return
        decisions = dict(self.ws.decisions)
        decisions[d.process] = d
        write_json(root / DECISIONS_FILE, decisions_to_json(decisions))
        self._reload()
        self.status.set(self._t("msg_saved").format(path=DECISIONS_FILE))

    def _generate(self) -> None:
        root = self._root()
        if root is None:
            return
        try:
            ws = load_workspace(root)
        except HarmonisationError as exc:
            self.status.set(self._t("msg_error").format(error=exc))
            return
        lang = self.report_lang.get() or self.lang
        path = root / f"matrix.{lang}.html"
        path.write_text(render_html(ws, lang), encoding="utf-8")
        self.status.set(self._t("msg_matrix").format(path=path))
        webbrowser.open(path.resolve().as_uri())


def main() -> None:
    root = tk.Tk()
    HarmonisationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
