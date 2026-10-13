# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       13.10.2026
# Geändert:       13.10.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Stage-Pfade für den Testdaten-Generator — getrennt von der Zeit. Ein
#   echter ART läuft nicht brav durch alle Stufen: Vorgänge überspringen
#   Stufen, werden abgebrochen (direkt in die Endstufe), parken in einer
#   Nebenstage (Blocker), schleifen auf sich selbst (Jira-Workflow-Loops),
#   gehen mehr als eine Stufe zurück, werden wiedereröffnet, starten nicht
#   alle in der ersten Arbeitsstufe und wandern nach dem Abschluss noch in
#   die Endstufe (Releasing → Done). Gemessen am echten ART_A (458 Vorgänge):
#   40 eindeutige Paare, 12 % rückwärts, 7,5 % Selbstschleifen, Median 4
#   Übergänge je Vorgang — der Generator vor 0.38.0 lieferte 11 Paare, 0 %
#   Schleifen, Median 7. Der Sammelregler ``realism`` (0–1) skaliert acht
#   Störungen linear; 0 ist das bisherige Verhalten (nur ``backflow_prob``),
#   ~0,7 trifft die Kennzahlen des echten ART_A (Kalibrierung per Test).
#   Die Zeitverteilung auf den Pfad bleibt Sache des Generators.
# =============================================================================

from __future__ import annotations

import random
from dataclasses import dataclass

#: Stage names (lower-case) that count as a parking stage when the config
#: names none: a side track issues enter and leave again, never a step of
#: the regular forward chain.
PARKING_NAMES = ("blocker", "blocked", "on hold", "waiting", "impediment",
                 "parked", "paused")


@dataclass(frozen=True)
class RealismKnobs:
    """
    Probabilities of the eight disturbances at ``realism = 1``.

    Per-step chances unless noted; ``knobs_at(r)`` scales them linearly.
    """
    skip: float = 0.10          # forward jump over at least one stage
    cancel: float = 0.09        # straight into the final stage (abandoned)
    park: float = 0.03          # into the parking stage and back again
    self_loop: float = 0.11     # status -> same status (workflow loops)
    long_backflow: float = 0.05  # back by two or more stages
    reopen: float = 0.05        # per issue: closed -> earlier stage, once
    entry_spread: float = 0.22  # per issue: first transition not into the first stage
    archive: float = 0.9        # per issue: after closing, move on to the final stage


#: Knobs at realism 1 — the calibration point (tests pin the ART_A numbers).
MAX_KNOBS = RealismKnobs()


def knobs_at(realism: float) -> RealismKnobs:
    """Scale the maximum knobs linearly; realism is clamped to 0..1."""
    r = max(0.0, min(1.0, float(realism)))
    return RealismKnobs(**{k: v * r for k, v in MAX_KNOBS.__dict__.items()})


def detect_parking(stages: list[str], parking_stage: str | None = None) -> int | None:
    """
    Index of the parking stage: the configured name, else the first stage
    whose name matches PARKING_NAMES, else None. Never the first or last
    stage — a parking stage is a side track, not an end.
    """
    if parking_stage:
        if parking_stage in stages:
            idx = stages.index(parking_stage)
            return idx if 0 < idx < len(stages) - 1 else None
        return None
    for i, name in enumerate(stages):
        if 0 < i < len(stages) - 1 and name.strip().lower() in PARKING_NAMES:
            return i
    return None


@dataclass
class PathSpec:
    """Everything the sampler needs to know about one workflow and issue."""
    n_stages: int
    first_idx: int
    closed_idx: int
    target_idx: int            # where the path ends (closed_idx = completes)
    parking_idx: int | None
    backflow_prob: float
    knobs: RealismKnobs
    start_idx: int = 0

    @property
    def completes(self) -> bool:
        return self.target_idx >= self.closed_idx

    @property
    def final_idx(self) -> int:
        """The last stage of the workflow (e.g. Done behind Releasing)."""
        return self.n_stages - 1

    @property
    def realism_on(self) -> bool:
        return any(v > 0 for v in self.knobs.__dict__.values())


class _Walk:
    """Mutable state of one path walk (kept out of the sampler's signature)."""

    def __init__(self, spec: PathSpec, rng: random.Random) -> None:
        self.spec = spec
        self.rng = rng
        self.k = spec.knobs
        self.parking = spec.parking_idx if spec.knobs.park > 0 else None
        self.cur = spec.start_idx
        self.path: list[int] = []
        self.parked_from: int | None = None
        self.reopened = False
        self.finished = False      # cancelled or archived: nothing follows

    def go(self, idx: int) -> None:
        self.cur = idx
        self.path.append(idx)

    def forward_candidates(self) -> list[int]:
        """Regular working stages after cur up to the target (parking excluded)."""
        s = self.spec
        return [j for j in range(self.cur + 1, min(s.target_idx, s.closed_idx) + 1)
                if j != self.parking]

    # --- the eight disturbances, each returns True when it moved ------------

    def entry_spread(self) -> bool:
        s, k = self.spec, self.k
        if self.cur >= s.first_idx or self.rng.random() >= k.entry_spread:
            return False
        later = [j for j in range(s.first_idx + 1, s.target_idx + 1) if j != self.parking]
        if later:
            self.go(self.rng.choice(later))
        return bool(later)

    def self_loop(self, roll: float) -> bool:
        if roll < self.k.self_loop and self.cur >= self.spec.first_idx:
            self.go(self.cur)
            return True
        return False

    def park(self, roll: float) -> bool:
        s = self.spec
        if (self.parking is not None and self.cur != self.parking
                and s.first_idx <= self.cur < s.closed_idx and roll < self.k.park):
            self.parked_from = self.cur
            self.go(self.parking)
            return True
        return False

    def cancel(self, roll: float) -> bool:
        s = self.spec
        if s.completes and s.first_idx <= self.cur < s.closed_idx and roll < self.k.cancel:
            self.go(s.final_idx)
            self.finished = True
            return True
        return False

    def long_backflow(self, roll: float) -> bool:
        s = self.spec
        if self.cur > s.first_idx + 1 and self.cur < s.closed_idx and roll < self.k.long_backflow:
            back = [j for j in range(s.first_idx, self.cur - 1) if j != self.parking]
            if back:
                self.go(self.rng.choice(back))
                return True
        return False

    def skip(self, roll: float) -> bool:
        if self.cur < self.spec.first_idx or roll >= self.k.skip:
            return False
        far = [j for j in self.forward_candidates() if j > self.cur + 1]
        if far:
            self.go(self.rng.choice(far))
        return bool(far)

    def disturb(self, roll: float) -> bool:
        """Try the per-step disturbances in a fixed order (one roll serves all)."""
        k = self.k
        for prob, move in ((k.self_loop, self.self_loop), (k.park, self.park),
                           (k.cancel, self.cancel), (k.long_backflow, self.long_backflow),
                           (k.skip, self.skip)):
            if move(roll):
                return True
            roll -= prob
        return False

    def classic_step(self, roll: float) -> None:
        """The pre-0.38.0 chain: one back (backflow) or one forward."""
        s = self.spec
        if s.first_idx < self.cur < s.closed_idx and roll < s.backflow_prob:
            back = self.cur - 1
            if back == self.parking:          # the side track is no step back
                back -= 1
            self.go(max(s.first_idx, back))
            return
        nxt = self.cur + 1
        if self.parking is not None and nxt == self.parking and nxt < s.target_idx:
            nxt += 1
        self.go(min(nxt, s.target_idx))

    def after_close(self) -> None:
        """Reopen once (then close again) or archive into the final stage."""
        s, k = self.spec, self.k
        if not self.reopened and self.rng.random() < k.reopen:
            self.reopened = True
            back = self.rng.randint(s.first_idx, max(s.first_idx, s.closed_idx - 1))
            if back != self.parking:
                self.go(back)
                return
        if s.final_idx > s.closed_idx and self.rng.random() < k.archive:
            self.go(s.final_idx)
        self.finished = True


def sample_path(spec: PathSpec, rng: random.Random,
                max_steps: int | None = None) -> list[int]:
    """
    Sample the sequence of stage indices an issue visits after ``start_idx``.

    The result lists the TARGET stage of every transition, in order; an
    empty list means the issue never left its start stage. Rules:

    - A completing issue reaches ``closed_idx``; with realism it may reopen
      once (then closes again) and usually moves on to the final stage
      (``archive``). An open issue ends at ``target_idx`` and never touches
      the closed stage — forward jumps are clamped to it.
    - A cancelled issue (``cancel``, completing issues only) jumps straight
      into the final stage and ends there — it never carries a closed-stage
      transition, exactly like "Done/Canceled" in a real export. Open issues
      stay open: completion_rate keeps its meaning as "share that attempts
      completion".
    - Backflow never goes below ``first_idx`` (the To-Do zone is left once).
    - The parking stage is not a step of the forward chain when realism is
      on; it is entered from a working stage and left back to that stage.
      With realism off the chain walks through it as before 0.38.0.
    - Self-loops are emitted as a transition to the same index.
    """
    w = _Walk(spec, rng)
    limit = max_steps if max_steps is not None else spec.n_stages * 6 + 6
    if spec.realism_on:
        w.entry_spread()
    steps = 0
    while not w.finished and steps < limit:
        steps += 1
        if w.parked_from is not None:
            back, w.parked_from = w.parked_from, None
            w.go(back)
            continue
        if w.cur == spec.closed_idx and spec.completes:
            if spec.realism_on:
                w.after_close()
            else:
                w.finished = True
            continue
        if w.cur == spec.target_idx:
            break
        roll = rng.random()
        if spec.realism_on and w.disturb(roll):
            continue
        if spec.realism_on:
            roll -= (w.k.self_loop + w.k.park + w.k.cancel + w.k.long_backflow + w.k.skip)
        w.classic_step(max(0.0, roll))
    return w.path
