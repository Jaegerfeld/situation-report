# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       30.10.2026
# Geändert:       30.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Rückfalllösung für den Demo-Datenraum in tkinter (Beta, 30.10.2026).
#   Der Tester-Lauf vom 26.10. zeigte, dass der lokale Server der Browser-
#   Oberfläche in einzelnen Umgebungen nicht erreichbar ist (Roberts
#   Rückmeldung: „Probleme mit dem html server, aber nur in wenigen
#   Szenarien"). Dieses Fenster bietet dieselben drei Schritte mit demselben
#   Funktionsumfang — Vorlage und Ereignis-Schalter, Struktur-Editor, Umfang
#   und Quellen, Erzeugen mit Fortschritt, Abbruch und Ergebniskarte samt
#   Delta-Vergleichswähler — ohne Server, ohne Browser. Es muss nicht so
#   schön sein wie die Browser-Seite; es muss überall laufen, wo tkinter ist.
#
#   Beide Oberflächen sitzen auf derselben Dienstschicht
#   (`testdata_generator.dataspace`) und teilen Texte (`web/texts.py`) und
#   Helfer (`web/server.py`): Was hier klickbar ist, ist dort klickbar.
#
#   UX read (ux-preflight): Nutzer und Ziel wie bei der Browser-Seite;
#   Gesetze Goal-Gradient (drei Reiter, Weiter/Zurück), Hick (vier Vorlagen,
#   eine empfohlen), Tesler (Vorgaben), Doherty (Vorschau sofort, Fortschritt
#   alle 200 ms), Peak-End (Ergebnis mit Aktionen), Fitts (Hauptknopf groß,
#   Zeilenhöhe durch Padding), Jakob (ttk-Standardwidgets wie im Rest der
#   Suite). Zustände: leer, Vorschau, Vorschau-Fehler, läuft, abgebrochen,
#   fehlgeschlagen, fertig, Ordner nicht leer (Rückfrage).
# =============================================================================

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from build_reports.chart_texts import DEFAULT_LANG, LANG_EN, LANGUAGES

from .dataspace import (
    STATE_DONE,
    STATE_FAILED,
    STATE_RUNNING,
    STATE_SKIPPED,
    STEPS,
    GenerationCancelled,
    GenerationRequest,
    GenerationResult,
    ProgressEvent,
    estimate_request,
    generate_dataspace,
)
from .scenario import MAX_STANDS, MIN_STANDS, _solution_tags
from .story import STORY_TEMPLATES, SUGGESTED_STANDS, Story, bind_roles, story_for
from .structure import (
    STRUCTURE_TEMPLATES,
    WORKFLOW_CLASSIC,
    WORKFLOW_STAGE_MAP,
    Estimate,
    PortfolioSpec,
    SolutionSpec,
    Structure,
    structure_template,
    suggest_art_names,
    suggest_solution_name,
    validate,
)
from .web.server import DEFAULT_REALISM, _delta_pair, _listing, _render_report, _rooms, default_open
from .web.texts import texts_for

_PREFS_PATH = Path.home() / ".situation_report" / "prefs.json"
_GREEK_FALLBACK = "S"


def _load_lang_pref() -> str:
    try:
        with open(_PREFS_PATH, encoding="utf-8") as f:
            val = json.load(f).get("lang", LANG_EN)
            return val if val in LANGUAGES else LANG_EN
    except Exception:
        return LANG_EN


# --- editable model (testable without tkinter) ----------------------------------

@dataclass
class SolutionRow:
    name: str
    workflow: str = WORKFLOW_CLASSIC
    arts: int = 3


@dataclass
class PortfolioRow:
    name: str
    solutions: list[SolutionRow] = field(default_factory=list)


@dataclass
class Settings:
    """Everything the three tabs collect — the same fields as the browser page."""
    template: str = "standard"
    switches: dict[str, bool] = field(default_factory=dict)
    structure_template: str = "standard"
    rows: list[PortfolioRow] = field(default_factory=list)
    stands: int | None = None
    user_stands: bool = False
    scale: str = "m"
    seed: str = "42"
    reference: str = field(default_factory=lambda: date.today().isoformat())
    lang: str = DEFAULT_LANG
    realism: int = DEFAULT_REALISM
    ai_drafts: bool = False
    output_dir: str = field(default_factory=lambda: str(
        Path.home() / f"SituationReport-Datenraum-{date.today().isoformat()}"))

    def effective_stands(self) -> int:
        return self.stands if self.stands else SUGGESTED_STANDS.get(self.template, 6)


def rows_from_structure(structure: Structure) -> list[PortfolioRow]:
    return [PortfolioRow(p.name, [SolutionRow(s.short, s.workflow, len(s.arts))
                                  for s in p.solutions])
            for p in structure.portfolios]


def structure_from_rows(rows: list[PortfolioRow]) -> Structure:
    """Build and validate; raises ValueError with the first problem."""
    structure = Structure([
        PortfolioSpec(p.name, [SolutionSpec(s.name, suggest_art_names(s.name, s.arts), s.workflow)
                               for s in p.solutions])
        for p in rows])
    validate(structure)
    return structure


def next_solution_name(rows: list[PortfolioRow]) -> str:
    used = {s.name for p in rows for s in p.solutions}
    for i in range(200):
        name = suggest_solution_name(i)
        if name not in used:
            return name
    return f"{_GREEK_FALLBACK}{len(used) + 1}"


def build_preview(settings: Settings) -> tuple[Structure, Estimate, Story]:
    """Structure, estimate and story for the current settings (ValueError on bad input)."""
    structure = structure_from_rows(settings.rows)
    stands = settings.effective_stands()
    request = GenerationRequest(output_dir=Path("."), structure=structure,
                                template=settings.template, switches=dict(settings.switches),
                                stands=stands, scale=settings.scale)
    request.validate()
    first = structure.portfolios[0]
    story = story_for(settings.template, bind_roles(first), _solution_tags(first), stands,
                      dict(settings.switches))
    return structure, estimate_request(request), story


def build_request(settings: Settings) -> GenerationRequest:
    """The GenerationRequest of the settings (ValueError on bad seed, date, folder)."""
    structure = structure_from_rows(settings.rows)
    out = settings.output_dir.strip()
    if not out:
        raise ValueError("output_dir")
    try:
        seed = int(settings.seed)
    except ValueError as exc:
        raise ValueError("seed") from exc
    try:
        reference = date.fromisoformat(settings.reference) if settings.reference.strip() else None
    except ValueError as exc:
        raise ValueError("reference") from exc
    art_profiles = None
    if settings.realism != DEFAULT_REALISM:
        art_profiles = {art: {"realism": int(settings.realism)}
                        for p in structure.portfolios for art in p.arts}
    request = GenerationRequest(
        output_dir=Path(out).expanduser(), structure=structure, template=settings.template,
        switches=dict(settings.switches), stands=settings.effective_stands(),
        scale=settings.scale, seed=seed, reference=reference, lang=settings.lang,
        art_profiles=art_profiles, ai_drafts=settings.ai_drafts)
    request.validate()
    return request


def when_text(event: Any, last: int, t: dict[str, str]) -> str:
    if event.stand_from <= 1 and (event.stand_to is None or event.stand_to >= last):
        return t["when_all"]
    if event.stand_to is None or event.stand_to >= last:
        return (t["when_from"].format(a=event.stand_from) if event.stand_from < last
                else t["when_last"])
    if event.stand_from == event.stand_to:
        return t["when_one"].format(a=event.stand_from)
    return t["when_range"].format(a=event.stand_from, b=event.stand_to)


def open_target(result: GenerationResult, what: str, room_index: int = 0,
                a: int = 1, b: int = 2, opener=None) -> Path:
    """Open README, folder, report, conference pre-read, drafts or a delta; returns the path."""
    opener = opener or default_open      # looked up at call time (tests patch it)
    rooms = _rooms(result.paths, result.structure)
    room = rooms[max(0, min(room_index, len(rooms) - 1))]
    root = Path(room["root"])
    if what == "folder":
        target = root
    elif what == "readme":
        target = root / "README.md"
    elif what == "drafts":
        target = root / "ai_drafts" / "uebung_README.md"
    elif what in ("report", "conference"):
        target = _render_report(root, kind=what)
    elif what == "delta_last":
        n = len(room["stand_dates"])
        target = _delta_pair(root, room, n - 1, n, result.request.lang)
    elif what == "delta":
        target = _delta_pair(root, room, a, b, result.request.lang)
    else:
        raise ValueError(what)
    if not target.exists():
        raise LookupError(target.name)
    opener(target)
    return target


# --- the window ----------------------------------------------------------------------

class DataspaceWindow(tk.Tk):
    """Three tabs on the data-room service layer — the tkinter fallback of the browser UI."""

    POLL_MS = 200

    def __init__(self, lang: str | None = None) -> None:
        super().__init__()
        lang = lang or _load_lang_pref()
        self.ui_lang = "de" if lang == "de" else "en"
        self.t = texts_for(self.ui_lang)
        self.s = Settings(lang=lang if lang in LANGUAGES else DEFAULT_LANG)
        self.s.rows = rows_from_structure(structure_template("standard"))
        self.preview: tuple[Structure, Estimate, Story] | None = None
        self.preview_error: str | None = None
        self.result: GenerationResult | None = None
        self.job_state = "idle"
        self.job_error = ""
        self._cancel = False
        self._queue: queue.Queue[ProgressEvent | tuple[str, Any]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._preview_after: str | None = None
        self._event_vars: dict[str, tk.BooleanVar] = {}
        self._quiet = False

        self.title(f"{self.t['app']} · {self.t['nav_room']}")
        self.minsize(960, 640)
        self.geometry("1200x900")        # all ten events visible on a 1080p screen
        self._build()
        self._refresh_preview()

    # -- layout --
    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        # Footer first and at the bottom: Back/Next stay visible however tall the tabs grow.
        foot = ttk.Frame(self)
        foot.pack(side="bottom", fill="x", **pad)
        self.nb = ttk.Notebook(self)
        self.nb.pack(side="top", fill="both", expand=True, **pad)
        self.tab1 = ttk.Frame(self.nb)
        self.tab2 = ttk.Frame(self.nb)
        self.tab3 = ttk.Frame(self.nb)
        self.nb.add(self.tab1, text=f"1 · {self.t['step1']}")
        self.nb.add(self.tab2, text=f"2 · {self.t['step2']}")
        self.nb.add(self.tab3, text=f"3 · {self.t['step3']}")
        self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._update_footer())
        self._build_tab1()
        self._build_tab2()
        self._build_tab3()
        self.btn_back = ttk.Button(foot, text=self.t["back"], command=lambda: self._go(-1))
        self.btn_back.pack(side="left")
        self.lbl_footer = ttk.Label(foot, text="", foreground="#5b6b7c")
        self.lbl_footer.pack(side="left", padx=12)
        self.btn_next = ttk.Button(foot, text=self.t["next_step2"], command=lambda: self._go(1))
        self.btn_next.pack(side="right")

    def _go(self, delta: int) -> None:
        index = self.nb.index(self.nb.select()) + delta
        if 0 <= index <= 2:
            self.nb.select(index)

    def _update_footer(self) -> None:
        index = self.nb.index(self.nb.select())
        tpl = self.t.get(f"tpl_{self.s.template}", self.s.template)
        if index == 0:
            on = (sum(1 for e in self.preview[2].events
                      if self.s.switches.get(e.event_id, e.enabled)) if self.preview else 0)
            self.lbl_footer.configure(text=self.t["footer_step1"].format(tpl=tpl, on=on))
            self.btn_next.configure(text=self.t["next_step2"], state="normal")
            self.btn_back.configure(state="disabled")
        else:
            self.lbl_footer.configure(text=self.t["footer_step2"].format(
                tpl=tpl, scale=self.s.scale.upper(), stands=self.s.effective_stands(),
                realism=self.s.realism, seed=self.s.seed))
            self.btn_back.configure(state="normal")
            if index == 1:
                self.btn_next.configure(text=self.t["next_step3"], state="normal")
            else:
                self.btn_next.configure(text=self.t["next_step3"], state="disabled")

    # -- tab 1: scenario --
    def _build_tab1(self) -> None:
        left = ttk.Frame(self.tab1)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        right = ttk.Frame(self.tab1, width=380)
        right.pack(side="right", fill="y", padx=8, pady=6)

        ttk.Label(left, text=self.t["h1_step1"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text=self.t["p_step1"], wraplength=560, foreground="#5b6b7c").pack(anchor="w")
        box = ttk.LabelFrame(left, text=self.t["step1"])
        box.pack(fill="x", pady=(8, 4))
        self.var_template = tk.StringVar(value=self.s.template)
        for i, tpl in enumerate(STORY_TEMPLATES):
            cell = ttk.Frame(box)
            cell.grid(row=i // 2, column=i % 2, sticky="nw", padx=6, pady=4)
            title = self.t.get(f"tpl_{tpl}", tpl) + (f"  ★ {self.t['recommended']}" if tpl == "standard" else "")
            ttk.Radiobutton(cell, text=title, value=tpl, variable=self.var_template,
                            command=self._on_template).pack(anchor="w")
            ttk.Label(cell, text=self.t.get(f"tpl_{tpl}_desc", ""), wraplength=260,
                      foreground="#5b6b7c").pack(anchor="w", padx=22)
        ev = ttk.LabelFrame(left, text=self.t["events_title"])
        ev.pack(fill="both", expand=True, pady=4)
        self.lbl_events_hint = ttk.Label(ev, text="", foreground="#5b6b7c")
        self.lbl_events_hint.pack(anchor="w", padx=6)
        self.events_box = ttk.Frame(ev)
        self.events_box.pack(fill="both", expand=True, padx=4)
        self.lbl_notices = ttk.Label(ev, text="", wraplength=560, foreground="#8a5a00")
        self.lbl_notices.pack(anchor="w", padx=6, pady=(2, 4))

        st = ttk.LabelFrame(right, text=self.t["structure_title"])
        st.pack(fill="both", expand=True)
        row = ttk.Frame(st)
        row.pack(fill="x", padx=6, pady=4)
        ttk.Label(row, text=self.t["structure_template"]).pack(side="left")
        self.var_struct_tpl = tk.StringVar(value="standard")
        self.cmb_struct = ttk.Combobox(row, textvariable=self.var_struct_tpl, state="readonly",
                                       values=[self.t[f"st_{k}"] for k in STRUCTURE_TEMPLATES]
                                       + [self.t["st_custom"]], width=34)
        self.cmb_struct.pack(side="left", padx=6)
        self.cmb_struct.bind("<<ComboboxSelected>>", self._on_struct_template)
        self._set_struct_combo("standard")
        ttk.Label(st, text=self.t["structure_hint"], wraplength=350, foreground="#5b6b7c").pack(
            anchor="w", padx=6)
        self.tree_box = ttk.Frame(st)
        self.tree_box.pack(fill="both", expand=True, padx=4, pady=4)
        self.lbl_sum = ttk.Label(st, text="", foreground="#5b6b7c")
        self.lbl_sum.pack(anchor="w", padx=6)
        yields = ttk.LabelFrame(right, text=f"{self.t['yields_title']} {self.t['yields_follow']}")
        yields.pack(fill="x", pady=(6, 0))
        self.lbl_yields = ttk.Label(yields, text="", wraplength=350, justify="left")
        self.lbl_yields.pack(anchor="w", padx=6, pady=4)
        self.lbl_warn = ttk.Label(yields, text="", wraplength=350, foreground="#8a5a00")
        self.lbl_warn.pack(anchor="w", padx=6)
        self._render_tree()

    def _set_struct_combo(self, key: str) -> None:
        label = self.t[f"st_{key}"] if key in STRUCTURE_TEMPLATES else self.t["st_custom"]
        self.var_struct_tpl.set(label)

    def _on_struct_template(self, _e=None) -> None:
        label = self.var_struct_tpl.get()
        for key in STRUCTURE_TEMPLATES:
            if label == self.t[f"st_{key}"]:
                self.s.structure_template = key
                self.s.rows = rows_from_structure(structure_template(key))
                break
        else:
            self.s.structure_template = "custom"
        self._render_tree()
        self._schedule_preview()

    def _mark_custom(self) -> None:
        self.s.structure_template = "custom"
        self._set_struct_combo("custom")
        self._render_tree()
        self._schedule_preview()

    def _render_tree(self) -> None:
        for child in self.tree_box.winfo_children():
            child.destroy()
        for pi, p in enumerate(self.s.rows):
            prow = ttk.Frame(self.tree_box)
            prow.pack(fill="x", pady=(4, 0))
            ttk.Label(prow, text=self.t["portfolio"], font=("Segoe UI", 9, "bold")).pack(side="left")
            name_var = tk.StringVar(value=p.name)
            ent = ttk.Entry(prow, textvariable=name_var, width=18)
            ent.pack(side="left", padx=4)
            ent.bind("<FocusOut>", lambda _e, p=p, v=name_var: self._rename(p, v))
            ent.bind("<Return>", lambda _e, p=p, v=name_var: self._rename(p, v))
            ttk.Button(prow, text="–", width=3, command=lambda pi=pi: self._remove_portfolio(pi),
                       state="normal" if len(self.s.rows) > 1 else "disabled").pack(side="left")
            for si, s in enumerate(p.solutions):
                srow = ttk.Frame(self.tree_box)
                srow.pack(fill="x", padx=(18, 0), pady=1)
                ttk.Label(srow, text=self.t["solution"]).pack(side="left")
                sv = tk.StringVar(value=s.name)
                sent = ttk.Entry(srow, textvariable=sv, width=10)
                sent.pack(side="left", padx=3)
                sent.bind("<FocusOut>", lambda _e, s=s, v=sv: self._rename(s, v))
                sent.bind("<Return>", lambda _e, s=s, v=sv: self._rename(s, v))
                ttk.Label(srow, text=self.t["arts"]).pack(side="left")
                av = tk.IntVar(value=s.arts)
                spin = ttk.Spinbox(srow, from_=1, to=30, width=3, textvariable=av,
                                   command=lambda s=s, v=av: self._set_arts(s, v))
                spin.pack(side="left", padx=3)
                spin.bind("<FocusOut>", lambda _e, s=s, v=av: self._set_arts(s, v))
                wv = tk.StringVar(value=self.t["wf_stage_map"] if s.workflow == WORKFLOW_STAGE_MAP
                                  else self.t["wf_classic"])
                cmb = ttk.Combobox(srow, textvariable=wv, state="readonly", width=16,
                                   values=[self.t["wf_classic"], self.t["wf_stage_map"]])
                cmb.pack(side="left", padx=3)
                cmb.bind("<<ComboboxSelected>>", lambda _e, s=s, v=wv: self._set_workflow(s, v))
                ttk.Button(srow, text="×", width=3,
                           command=lambda p=p, si=si: self._remove_solution(p, si),
                           state="normal" if len(p.solutions) > 1 else "disabled").pack(side="left")
            ttk.Button(self.tree_box, text=self.t["add_solution"],
                       command=lambda p=p: self._add_solution(p)).pack(anchor="w", padx=18, pady=(2, 0))
        ttk.Button(self.tree_box, text=self.t["add_portfolio"], command=self._add_portfolio).pack(
            anchor="w", pady=(6, 0))
        np_ = len(self.s.rows)
        ns = sum(len(p.solutions) for p in self.s.rows)
        na = sum(s.arts for p in self.s.rows for s in p.solutions)
        self.lbl_sum.configure(text=self.t["sum"].format(
            p=f"{np_} {self.t['portfolio']}", s=f"{ns} {self.t['solution']}", a=f"{na} {self.t['arts']}"))

    def _rename(self, item: Any, var: tk.StringVar) -> None:
        if var.get().strip() and var.get().strip() != item.name:
            item.name = var.get().strip()
            self._mark_custom()

    def _set_arts(self, s: SolutionRow, var: tk.IntVar) -> None:
        try:
            value = max(1, int(var.get()))
        except (tk.TclError, ValueError):
            return
        if value != s.arts:
            s.arts = value
            self._mark_custom()

    def _set_workflow(self, s: SolutionRow, var: tk.StringVar) -> None:
        s.workflow = WORKFLOW_STAGE_MAP if var.get() == self.t["wf_stage_map"] else WORKFLOW_CLASSIC
        self._mark_custom()

    def _add_solution(self, p: PortfolioRow) -> None:
        p.solutions.append(SolutionRow(next_solution_name(self.s.rows), WORKFLOW_CLASSIC, 2))
        self._mark_custom()

    def _remove_solution(self, p: PortfolioRow, si: int) -> None:
        if len(p.solutions) > 1:
            del p.solutions[si]
            self._mark_custom()

    def _add_portfolio(self) -> None:
        name = f"{self.t['portfolio']} {len(self.s.rows) + 1}"
        self.s.rows.append(PortfolioRow(name, [SolutionRow(next_solution_name(self.s.rows),
                                                            WORKFLOW_CLASSIC, 2)]))
        self._mark_custom()

    def _remove_portfolio(self, pi: int) -> None:
        if len(self.s.rows) > 1:
            del self.s.rows[pi]
            self._mark_custom()

    def _on_template(self) -> None:
        self.s.template = self.var_template.get()
        self.s.switches = {}
        if not self.s.user_stands:
            self.s.stands = None
            if hasattr(self, "scl_stands"):
                self._set_scale_quietly(self.scl_stands, self.s.effective_stands())
                self._on_stands(str(self.s.effective_stands()), from_user=False)
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        if self._preview_after:
            self.after_cancel(self._preview_after)
        self._preview_after = self.after(150, self._refresh_preview)

    def _refresh_preview(self) -> None:
        self._preview_after = None
        try:
            self.preview = build_preview(self.s)
            self.preview_error = None
        except ValueError as exc:
            self.preview_error = str(exc)
        self._render_events()
        self._render_yields()
        self._update_footer()

    def _render_events(self) -> None:
        for child in self.events_box.winfo_children():
            child.destroy()
        self._event_vars = {}
        if self.preview_error:
            ttk.Label(self.events_box, text=self.preview_error, foreground="#b23a48",
                      wraplength=540).pack(anchor="w")
            return
        if not self.preview:
            return
        _, _, story = self.preview
        last = story.stands
        self.lbl_events_hint.configure(text=self.t["events_hint"].format(n=last))
        head = ttk.Frame(self.events_box)
        head.pack(fill="x")
        for col, key, width in ((0, "col_on", 4), (1, "col_when", 14), (2, "col_what", 40),
                                (3, "col_effect", 40)):
            ttk.Label(head, text=self.t[key], foreground="#5b6b7c", width=width).grid(
                row=0, column=col, sticky="w", padx=3)
        for e in story.events:
            on = self.s.switches.get(e.event_id, e.enabled)
            var = tk.BooleanVar(value=on)
            self._event_vars[e.event_id] = var
            row = ttk.Frame(self.events_box)
            row.pack(fill="x", pady=1)
            ttk.Checkbutton(row, variable=var, command=lambda eid=e.event_id, v=var: self._toggle(eid, v)
                            ).grid(row=0, column=0, sticky="nw", padx=3)
            ttk.Label(row, text=when_text(e, last, self.t) if on else "—", width=14,
                      foreground="#23303e" if on else "#5b6b7c").grid(row=0, column=1, sticky="nw", padx=3)
            ttk.Label(row, text=e.title, wraplength=280, foreground="#23303e" if on else "#5b6b7c").grid(
                row=0, column=2, sticky="nw", padx=3)
            ttk.Label(row, text=e.effect, wraplength=280, foreground="#5b6b7c").grid(
                row=0, column=3, sticky="nw", padx=3)
        self.lbl_notices.configure(text=(self.t["notices_title"] + ": " + " ".join(story.notices))
                                   if story.notices else "")

    def _toggle(self, eid: str, var: tk.BooleanVar) -> None:
        self.s.switches[eid] = bool(var.get())
        self._schedule_preview()

    def _render_yields(self) -> None:
        if not self.preview:
            self.lbl_yields.configure(text="")
            return
        _, e, _ = self.preview
        self.lbl_yields.configure(text="\n".join([
            self.t["yields_line1"].format(exports=e.jira_exports, workbooks=e.workbooks,
                                          registers=e.registers),
            self.t["yields_line2"],
            self.t["yields_line3"].format(stands=e.stands, deltas=e.deltas),
            self.t["yields_note"]]))
        self.lbl_warn.configure(text=self.t["warn_large"].format(reason=e.warn_reason) if e.warn else "")
        if hasattr(self, "lbl_estimate"):
            self.lbl_estimate.configure(text=self.t["estimate_line"].format(
                exports=e.jira_exports, registers=e.registers, stands=e.stands, deltas=e.deltas))

    # -- tab 2: scope --
    def _build_tab2(self) -> None:
        left = ttk.Frame(self.tab2)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        right = ttk.Frame(self.tab2, width=360)
        right.pack(side="right", fill="y", padx=8, pady=6)
        ttk.Label(left, text=self.t["h1_step2"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text=self.t["p_step2"], foreground="#5b6b7c").pack(anchor="w")
        grid = ttk.Frame(left)
        grid.pack(fill="x", pady=8)
        # stands
        ttk.Label(grid, text=f"{self.t['stands']} {self.t['stands_sub']}", font=("Segoe UI", 9, "bold")
                  ).grid(row=0, column=0, sticky="w")
        self.scl_stands = ttk.Scale(grid, from_=MIN_STANDS, to=MAX_STANDS, orient="horizontal")
        self.scl_stands.grid(row=1, column=0, sticky="ew", padx=(0, 20))
        self.lbl_stands = ttk.Label(grid, text="")
        self.lbl_stands.grid(row=2, column=0, sticky="w")
        self._set_scale_quietly(self.scl_stands, self.s.effective_stands())
        self.scl_stands.configure(command=self._on_stands)
        ttk.Label(grid, text=self.t["stands_hint"], wraplength=360, foreground="#5b6b7c").grid(
            row=3, column=0, sticky="w", pady=(0, 8))
        # scale
        ttk.Label(grid, text=self.t["scale"], font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w")
        self.var_scale = tk.StringVar(value=self.t[f"scale_{self.s.scale}"])
        cmb = ttk.Combobox(grid, textvariable=self.var_scale, state="readonly", width=32,
                           values=[self.t[f"scale_{k}"] for k in ("s", "m", "l")])
        cmb.grid(row=1, column=1, sticky="w")
        cmb.bind("<<ComboboxSelected>>", self._on_scale)
        # realism
        ttk.Label(grid, text=f"{self.t['realism']} {self.t['realism_sub']}", font=("Segoe UI", 9, "bold")
                  ).grid(row=4, column=0, sticky="w")
        self.scl_realism = ttk.Scale(grid, from_=0, to=100, orient="horizontal")
        self.scl_realism.grid(row=5, column=0, sticky="ew", padx=(0, 20))
        self.lbl_realism = ttk.Label(grid, text=f"{self.t['realism_low']} · {self.s.realism} · {self.t['realism_high']}")
        self.lbl_realism.grid(row=6, column=0, sticky="w", pady=(0, 8))
        self.scl_realism.set(self.s.realism)
        self.scl_realism.configure(command=self._on_realism)
        # seed / reference / lang
        ttk.Label(grid, text=f"{self.t['seed']} {self.t['seed_sub']}", font=("Segoe UI", 9, "bold")
                  ).grid(row=4, column=1, sticky="w")
        self.var_seed = tk.StringVar(value=self.s.seed)
        ttk.Entry(grid, textvariable=self.var_seed, width=12).grid(row=5, column=1, sticky="w")
        ttk.Label(grid, text=self.t["reference"], font=("Segoe UI", 9, "bold")).grid(row=7, column=0, sticky="w")
        self.var_ref = tk.StringVar(value=self.s.reference)
        ttk.Entry(grid, textvariable=self.var_ref, width=14).grid(row=8, column=0, sticky="w")
        ttk.Label(grid, text=self.t["lang"], font=("Segoe UI", 9, "bold")).grid(row=7, column=1, sticky="w")
        self.var_lang = tk.StringVar(value=self.s.lang)
        ttk.Combobox(grid, textvariable=self.var_lang, state="readonly", values=list(LANGUAGES),
                     width=6).grid(row=8, column=1, sticky="w")
        grid.columnconfigure(0, weight=1)
        ttk.Label(left, text=self.t["details"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        ttk.Label(left, text=self.t["details_text"], wraplength=560, foreground="#5b6b7c").pack(anchor="w")
        self._on_stands(str(self.s.effective_stands()), from_user=False)

        src = ttk.LabelFrame(right, text=self.t["sources_title"])
        src.pack(fill="x")
        ttk.Label(src, text=self.t["sources_hint"], wraplength=330, foreground="#5b6b7c").pack(
            anchor="w", padx=6, pady=(2, 4))
        for key in ("jira", "prometheus", "github", "gitlab", "sonarqube", "csv"):
            ttk.Label(src, text=f"✓ {self.t['src_' + key]}  ({self.t['src_always']})").pack(anchor="w", padx=8)
        self.var_ai = tk.BooleanVar(value=False)
        ttk.Checkbutton(src, text=self.t["src_ai"], variable=self.var_ai,
                        command=lambda: setattr(self.s, "ai_drafts", bool(self.var_ai.get()))
                        ).pack(anchor="w", padx=6, pady=(6, 0))
        ttk.Label(src, text=self.t["src_ai_hint"], wraplength=330, foreground="#5b6b7c").pack(
            anchor="w", padx=28, pady=(0, 6))
        est = ttk.LabelFrame(right, text=self.t["estimate_title"])
        est.pack(fill="x", pady=(8, 0))
        self.lbl_estimate = ttk.Label(est, text="", wraplength=330)
        self.lbl_estimate.pack(anchor="w", padx=6, pady=4)

    def _on_stands(self, value: str, from_user: bool = True) -> None:
        n = int(round(float(value)))
        if from_user and not self._quiet and self.s.stands != n:
            self.s.stands = n
            self.s.user_stands = True
            self._schedule_preview()
        if abs(self.scl_stands.get() - n) > 0.01:
            self._set_scale_quietly(self.scl_stands, n)
        self.lbl_stands.configure(text=self.t["stands_line"].format(n=n, weeks=(n - 1) * 2))

    def _set_scale_quietly(self, scale: ttk.Scale, value: float) -> None:
        """Move a scale without treating the callback as a user change."""
        self._quiet = True
        try:
            scale.set(value)
        finally:
            self._quiet = False

    def _on_scale(self, _e=None) -> None:
        for key in ("s", "m", "l"):
            if self.var_scale.get() == self.t[f"scale_{key}"]:
                self.s.scale = key
        self._schedule_preview()

    def _on_realism(self, value: str) -> None:
        self.s.realism = int(round(float(value)))
        self.lbl_realism.configure(text=f"{self.t['realism_low']} · {self.s.realism} · {self.t['realism_high']}")
        self._update_footer()

    def _sync_scalars(self) -> None:
        self.s.seed = self.var_seed.get().strip()
        self.s.reference = self.var_ref.get().strip()
        self.s.lang = self.var_lang.get() or DEFAULT_LANG
        self.s.ai_drafts = bool(self.var_ai.get())
        self.s.output_dir = self.var_out.get()

    # -- tab 3: generate --
    def _build_tab3(self) -> None:
        frame = ttk.Frame(self.tab3)
        frame.pack(fill="both", expand=True, padx=8, pady=6)
        ttk.Label(frame, text=self.t["h1_step3"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(8, 2))
        ttk.Label(row, text=f"{self.t['target']} {self.t['target_sub']}").pack(anchor="w")
        row2 = ttk.Frame(frame)
        row2.pack(fill="x")
        self.var_out = tk.StringVar(value=self.s.output_dir)
        ttk.Entry(row2, textvariable=self.var_out).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text=self.t["browse"], command=self._browse).pack(side="left", padx=6)
        row3 = ttk.Frame(frame)
        row3.pack(fill="x", pady=8)
        self.btn_generate = ttk.Button(row3, text=self.t["generate"], command=self._generate)
        self.btn_generate.pack(side="left", ipadx=14, ipady=6)
        ttk.Label(row3, text=self.t["generate_hint"], foreground="#5b6b7c").pack(side="left", padx=10)
        self.lbl_error = ttk.Label(frame, text="", foreground="#b23a48", wraplength=800)
        self.lbl_error.pack(anchor="w")

        prog = ttk.LabelFrame(frame, text=self.t["step3"])
        prog.pack(fill="x", pady=6)
        top = ttk.Frame(prog)
        top.pack(fill="x", padx=6, pady=2)
        self.lbl_prog = ttk.Label(top, text="")
        self.lbl_prog.pack(side="left")
        self.btn_cancel = ttk.Button(top, text=self.t["cancel"], command=self._cancel_job, state="disabled")
        self.btn_cancel.pack(side="right")
        self.pbar = ttk.Progressbar(prog, maximum=len(STEPS), value=0)
        self.pbar.pack(fill="x", padx=6, pady=2)
        self.step_rows: dict[str, tuple[ttk.Label, ttk.Label, ttk.Label]] = {}
        grid = ttk.Frame(prog)
        grid.pack(fill="x", padx=6, pady=(2, 6))
        for i, (step, label) in enumerate(STEPS):
            mark = ttk.Label(grid, text="○", width=2, foreground="#5b6b7c")
            mark.grid(row=i % 5, column=(i // 5) * 3, sticky="w")
            name = ttk.Label(grid, text=label, foreground="#5b6b7c")
            name.grid(row=i % 5, column=(i // 5) * 3 + 1, sticky="w", padx=(2, 10))
            detail = ttk.Label(grid, text="", foreground="#5b6b7c", wraplength=330)
            detail.grid(row=i % 5, column=(i // 5) * 3 + 2, sticky="w", padx=(0, 20))
            self.step_rows[step] = (mark, name, detail)

        self.result_box = ttk.LabelFrame(frame, text="")
        self.lbl_result_meta = ttk.Label(self.result_box, text="", foreground="#5b6b7c")
        self.lbl_result_meta.pack(anchor="w", padx=6)
        self.nums = ttk.Frame(self.result_box)
        self.nums.pack(fill="x", padx=6, pady=4)
        self.lbl_story = ttk.Label(self.result_box, text="", wraplength=800, justify="left")
        self.lbl_story.pack(anchor="w", padx=6)
        self.actions = ttk.Frame(self.result_box)
        self.actions.pack(fill="x", padx=6, pady=4)
        self.compare = ttk.Frame(self.result_box)
        self.compare.pack(fill="x", padx=6, pady=(0, 4))
        self.lbl_opened = ttk.Label(self.result_box, text="", foreground="#5b6b7c")
        self.lbl_opened.pack(anchor="w", padx=6)
        self.txt_listing = tk.Text(self.result_box, height=6, width=60, relief="flat",
                                   font=("Consolas", 9), state="disabled")
        self.txt_listing.pack(fill="x", padx=6, pady=(0, 6))

    def _browse(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.var_out.get() or None, mustexist=False)
        if chosen:
            self.var_out.set(chosen)

    def _generate(self, confirmed: bool = False) -> None:
        self._sync_scalars()
        self.lbl_error.configure(text="")
        try:
            request = build_request(self.s)
        except ValueError as exc:
            self.lbl_error.configure(text=f"{self.t['error_title']}: {exc}")
            return
        out = Path(request.output_dir)
        if out.exists() and not out.is_dir():
            self.lbl_error.configure(text=f"{self.t['error_title']}: {out}")
            return
        if out.is_dir() and any(out.iterdir()) and not confirmed:
            entries = sum(1 for _ in out.iterdir())
            if not messagebox.askyesno(self.t["confirm_title"],
                                       self.t["confirm_text"].format(path=out, n=entries),
                                       parent=self):
                return
        self._start(request)

    def _start(self, request: GenerationRequest) -> None:
        self.result = None
        self.result_box.pack_forget()
        self.job_state = STATE_RUNNING
        self.job_error = ""
        self._cancel = False
        self._done_steps = 0
        for mark, name, detail in self.step_rows.values():
            mark.configure(text="○", foreground="#5b6b7c")
            name.configure(foreground="#5b6b7c")
            detail.configure(text="")
        self.pbar.configure(value=0)
        self.lbl_prog.configure(text=self.t["running"])
        self.btn_generate.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self._started = __import__("time").monotonic()

        def work() -> None:
            try:
                result = generate_dataspace(request, progress=self._queue.put, log=lambda m: None,
                                            cancel=lambda: self._cancel)
                self._queue.put(("done", result))
            except GenerationCancelled:
                self._queue.put(("cancelled", None))
            except Exception as exc:  # shown next to the steps
                self._queue.put(("failed", f"{type(exc).__name__}: {exc}"))

        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()
        self.after(self.POLL_MS, self._poll)

    def _cancel_job(self) -> None:
        self._cancel = True
        self.btn_cancel.configure(state="disabled")

    def _poll(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, ProgressEvent):
                self._apply_event(item)
            else:
                kind, payload = item
                self._finish(kind, payload)
                return
        elapsed = __import__("time").monotonic() - self._started
        self.lbl_prog.configure(text=self.t["step_counter"].format(
            done=self._done_steps, total=len(STEPS), s=f"{elapsed:.0f}"))
        if self.job_state == STATE_RUNNING:
            self.after(self.POLL_MS, self._poll)

    def _apply_event(self, e: ProgressEvent) -> None:
        rows = self.step_rows.get(e.step)
        if not rows:
            return
        mark, name, detail = rows
        if e.state == STATE_RUNNING:
            mark.configure(text="⟳", foreground="#1f6fa8")
            name.configure(foreground="#23303e")
        elif e.state == STATE_DONE:
            mark.configure(text="✓", foreground="#2e8b57")
            name.configure(foreground="#23303e")
            detail.configure(text=f"{e.detail}  {e.elapsed_s} s" if e.detail else f"{e.elapsed_s} s")
            self._done_steps += 1
        elif e.state == STATE_SKIPPED:
            mark.configure(text="–", foreground="#5b6b7c")
            detail.configure(text=f"{self.t['skipped']}: {e.detail}")
            self._done_steps += 1
        elif e.state == STATE_FAILED:
            mark.configure(text="✗", foreground="#b23a48")
            detail.configure(text=e.detail)
        self.pbar.configure(value=self._done_steps)

    def _finish(self, kind: str, payload: Any) -> None:
        self.btn_generate.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.job_state = kind
        if kind == "cancelled":
            self.lbl_prog.configure(text=self.t["cancelled"])
        elif kind == "failed":
            self.job_error = str(payload)
            self.lbl_prog.configure(text=self.t["failed"].format(error=payload))
        else:
            self.result = payload
            self._done_steps = len(STEPS)
            self.pbar.configure(value=len(STEPS))
            self.lbl_prog.configure(text=self.t["step_counter"].format(
                done=len(STEPS), total=len(STEPS), s=payload.elapsed_s))
            self._render_result(payload)

    def _render_result(self, r: GenerationResult) -> None:
        self.result_box.configure(text=self.t["done_title"].format(name=r.root.name))
        self.lbl_result_meta.configure(text=self.t["done_meta"].format(s=r.elapsed_s, seed=r.request.seed))
        for child in list(self.nums.winfo_children()) + list(self.actions.winfo_children()) \
                + list(self.compare.winfo_children()):
            child.destroy()
        cells = [(r.issues, self.t["n_issues"].format(arts=r.structure.n_arts)),
                 (r.registers, self.t["n_registers"].format(solutions=r.structure.n_solutions)),
                 (r.stands, self.t["n_stands"]), (r.providers, self.t["n_providers"])]
        for i, (n, label) in enumerate(cells):
            cell = ttk.Frame(self.nums)
            cell.grid(row=0, column=i, padx=(0, 18), sticky="w")
            ttk.Label(cell, text=str(n), font=("Segoe UI", 16, "bold")).pack(anchor="w")
            ttk.Label(cell, text=label, foreground="#5b6b7c").pack(anchor="w")
        self.lbl_story.configure(text=(self.t["story_three"] + " " + " ".join(r.story.summary))
                                 if r.story else "")
        rooms = _rooms(r.paths, r.structure)
        self.var_room = tk.IntVar(value=0)
        if len(rooms) > 1:
            cmb = ttk.Combobox(self.actions, state="readonly", width=28,
                               values=[self.t["portfolio_tab"].format(name=x["name"]) for x in rooms])
            cmb.current(0)
            cmb.bind("<<ComboboxSelected>>", lambda _e, c=cmb: self.var_room.set(c.current()))
            cmb.pack(side="left", padx=(0, 8))
        for what, key in (("report", "open_report"), ("conference", "open_conference"),
                          ("delta_last", "open_delta_last"), ("readme", "open_readme"),
                          ("folder", "open_folder")):
            ttk.Button(self.actions, text=self.t[key], command=lambda w=what: self._open(w)).pack(
                side="left", padx=(0, 4))
        if r.ai_drafts:
            ttk.Button(self.actions, text=self.t["open_drafts"], command=lambda: self._open("drafts")).pack(
                side="left")
        dates = rooms[0]["stand_dates"] if rooms else []
        if len(dates) >= 2:
            ttk.Label(self.compare, text=self.t["compare"], font=("Segoe UI", 9, "bold")).pack(side="left")
            self.cmb_a = ttk.Combobox(self.compare, state="readonly", width=16,
                                      values=[f"{i + 1} · {d}" for i, d in enumerate(dates[:-1])])
            self.cmb_a.current(len(dates) - 2)
            self.cmb_a.pack(side="left", padx=4)
            ttk.Label(self.compare, text="→").pack(side="left")
            self.cmb_b = ttk.Combobox(self.compare, state="readonly", width=16,
                                      values=[f"{i + 1} · {d}" for i, d in enumerate(dates) if i > 0])
            self.cmb_b.current(len(dates) - 2)
            self.cmb_b.pack(side="left", padx=4)
            ttk.Button(self.compare, text=self.t["open_delta"], command=self._open_pair).pack(side="left")
            ttk.Label(self.compare, text=self.t["compare_hint"], foreground="#5b6b7c").pack(side="left", padx=6)
        self.txt_listing.configure(state="normal")
        self.txt_listing.delete("1.0", "end")
        self.txt_listing.insert("1.0", "\n".join(_listing(Path(rooms[0]["root"]))) if rooms else "")
        self.txt_listing.configure(state="disabled")
        self.lbl_opened.configure(text="")
        self.result_box.pack(fill="x", pady=6)

    def _open(self, what: str, a: int = 1, b: int = 2) -> None:
        if not self.result:
            return
        try:
            target = open_target(self.result, what, self.var_room.get(), a, b)
            self.lbl_opened.configure(text=f"{self.t['opened']}: {target}")
        except (LookupError, ValueError) as exc:
            self.lbl_opened.configure(text=f"{self.t['error_title']}: {exc}")

    def _open_pair(self) -> None:
        a = self.cmb_a.current() + 1
        b = self.cmb_b.current() + 2
        if a >= b:
            self.lbl_opened.configure(text=f"{self.t['error_title']}: {a} → {b}")
            return
        self._open("delta", a, b)


def main(lang: str | None = None) -> int:
    """Open the tkinter data-room window (the fallback of the browser UI)."""
    DataspaceWindow(lang).mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    main()
