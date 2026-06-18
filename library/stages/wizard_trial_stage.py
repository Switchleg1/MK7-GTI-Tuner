from __future__ import annotations

import math
import random

from panda3d.core import TextNode

from library.core.constants import BLUE, DIM, GOD_PAYOUT, GREEN, GREEN_2, LINE, PANEL, PANEL_DARK, RED, TEXT, VIOLET, WHITE
from library.stages.hud import Hud

# Phase 1: power the rig by clicking these in order.
RIG_ORDER = ["POWER", "GROUND", "DATA", "CLOCK", "ENABLE"]
# Phase 2: land the probes on the live pads, avoid the decoys.
PADS_LIVE = ["V+", "DATA", "CLK", "GND"]
PADS_DECOY = ["12V", "FAN", "HORN", "A/C", "CAN"]


class WizardTrialStage(Hud):
    """The Bench Wizard's secret Trial -- a three-part arcade challenge a verified
    pro is summoned to once their cred is high enough:
      1. power the rig: click the lines in the right order,
      2. probe the board: tap the live pads, dodge the decoys,
      3. sync window: hit DROP while the marker is in the green band.
    Pass it -> ``Game.grant_god()`` (god status + a giant one-time payout), then back
    to the hub. Pure 2D over a dark backdrop; entirely made-up flavour."""

    music_key = "unlock"

    def __init__(self, app, game, on_done):
        super().__init__(app, "wizard-trial")
        self.game = game
        self.on_done = on_done
        self.scene = app.render.attachNewNode("scene-wizard")
        self.phase = 1
        self.msg = ""
        self.rig_done = 0
        self.rig_slots = list(RIG_ORDER)
        self.pad_hits: set[str] = set()
        self.pad_slots: list[str] = []
        self.marker = None
        self.t = 0.0
        self.track = (0.0, 0.0, 0.0, 0.0)  # x0, x1, win_lo, win_hi

    # -- stage protocol ----------------------------------------------------
    def enter(self):
        random.shuffle(self.rig_slots)
        self._shuffle_pads()
        self.draw()

    def exit(self):
        self.scene.removeNode()
        self.destroy()

    def render(self, dt):
        if self.phase == 3 and self.marker is not None:
            self.t += dt
            x0, x1, _, _ = self.track
            frac = 0.5 + 0.5 * math.sin(self.t * 2.3)
            self.marker.setX(x0 + frac * (x1 - x0))

    # -- helpers -----------------------------------------------------------
    def _shuffle_pads(self):
        self.pad_slots = PADS_LIVE + PADS_DECOY
        random.shuffle(self.pad_slots)

    def _header(self):
        left, right = self.bounds()
        self.frame((-2.0, 2.0, -1.0, 1.0), (0, 0, 0), PANEL_DARK, border=None)  # full-screen backdrop
        self.frame((left, right, 0.74, 0.94), (0, 0, 0.84), PANEL, border=None)
        av = self.image("avatar", (left + 0.12, 0, 0.84), 0.06)
        av.setColorScale(VIOLET)
        self.label("THE BENCH WIZARD", (left + 0.22, 0, 0.85), 0.046, VIOLET)
        self.label("Pass the Trial. Three parts. No hints. No mercy.", (left + 0.22, 0, 0.79), 0.026, DIM)
        self.button("Abort", (right - 0.12, 0, 0.84), (0.16, 0.09), self.on_done, True, PANEL, 0.034)

    def draw(self):
        self.clear()
        self.marker = None
        self._header()
        if self.phase in (1, 2, 3):
            self.label(f"PART {self.phase} / 3", (0, 0, 0.66), 0.04, BLUE, align=TextNode.ACenter)
        if self.msg:
            self.label(self.msg, (0, 0, 0.58), 0.032, RED, align=TextNode.ACenter)
        {1: self._draw_rig, 2: self._draw_pads, 3: self._draw_sync, "win": self._draw_win}[self.phase]()

    # -- part 1: power the rig --------------------------------------------
    def _draw_rig(self):
        self.label("POWER THE RIG", (0, 0, 0.46), 0.05, GREEN, align=TextNode.ACenter)
        self.label("Bring the lines up in order:  POWER -> GROUND -> DATA -> CLOCK -> ENABLE",
                   (0, 0, 0.38), 0.030, TEXT, align=TextNode.ACenter)
        done = set(RIG_ORDER[:self.rig_done])
        for i, label in enumerate(self.rig_slots):
            x = -0.84 + i * 0.42
            on = label in done
            self.button(label + (" *" if on else ""), (x, 0, 0.10), (0.38, 0.16),
                        None if on else (lambda l=label: self._rig(l)), not on,
                        GREEN_2 if on else BLUE, 0.046)
        self.label(f"lines up: {self.rig_done}/{len(RIG_ORDER)}", (0, 0, -0.18), 0.030, DIM, align=TextNode.ACenter)

    def _rig(self, label):
        if label == RIG_ORDER[self.rig_done]:
            self.rig_done += 1
            self.msg = ""
            if self.rig_done >= len(RIG_ORDER):
                self.phase = 2
        else:
            self.rig_done = 0
            random.shuffle(self.rig_slots)
            self.msg = "WRONG LINE - magic smoke! the rig resets."
        self.draw()

    # -- part 2: probe the board ------------------------------------------
    def _draw_pads(self):
        self.label("PROBE THE BOARD", (0, 0, 0.46), 0.05, GREEN, align=TextNode.ACenter)
        self.label("Land the probes on the live pads:  V+, DATA, CLK, GND.   Avoid the rest.",
                   (0, 0, 0.38), 0.030, TEXT, align=TextNode.ACenter)
        for i, label in enumerate(self.pad_slots):
            row, col = divmod(i, 3)
            x = -0.52 + col * 0.52
            z = 0.18 - row * 0.22
            on = label in self.pad_hits
            self.button(label, (x, 0, z), (0.44, 0.16), None if on else (lambda l=label: self._pad(l)),
                        not on, GREEN_2 if on else PANEL, 0.044)
        self.label(f"live pads probed: {len(self.pad_hits)}/{len(PADS_LIVE)}", (0, 0, -0.52), 0.030, DIM, align=TextNode.ACenter)

    def _pad(self, label):
        if label in PADS_LIVE:
            self.pad_hits.add(label)
            self.msg = ""
            if len(self.pad_hits) >= len(PADS_LIVE):
                self.phase = 3
                self.t = 0.0
        else:
            self.pad_hits.clear()
            self._shuffle_pads()
            self.msg = f"{label} is not live - magic smoke! probes reset."
        self.draw()

    # -- part 3: sync window ----------------------------------------------
    def _draw_sync(self):
        self.label("SYNC WINDOW", (0, 0, 0.46), 0.05, GREEN, align=TextNode.ACenter)
        self.label("Hit DROP while the marker is in the green band.", (0, 0, 0.38), 0.030, TEXT, align=TextNode.ACenter)
        x0, x1, win_lo, win_hi = -0.7, 0.7, -0.10, 0.10
        self.track = (x0, x1, win_lo, win_hi)
        self.frame((x0, x1, 0.02, 0.12), (0, 0, 0), PANEL, border=LINE)
        self.frame((win_lo, win_hi, 0.02, 0.12), (0, 0, 0), GREEN_2, border=None)
        self.marker = self.frame((-0.012, 0.012, -0.01, 0.15), (0, 0, 0), WHITE, border=None)
        self.button("DROP", (0, 0, -0.18), (0.5, 0.16), self._drop, True, BLUE, 0.05)

    def _drop(self):
        if self.marker is None:
            return
        _, _, lo, hi = self.track
        if lo <= self.marker.getX() <= hi:
            self.phase = "win"
            self.game.grant_god()
            self.draw()
        else:
            self.msg = "missed the window - timeout. try again."
            self.draw()

    # -- win ---------------------------------------------------------------
    def _draw_win(self):
        self.label("TRIAL PASSED", (0, 0, 0.44), 0.075, GREEN, align=TextNode.ACenter)
        self.label("The Wizard nods. You have achieved GOD STATUS.", (0, 0, 0.31), 0.040, VIOLET, align=TextNode.ACenter)
        self.label(f"+${GOD_PAYOUT:,} dropped into your account.", (0, 0, 0.21), 0.040, GREEN, align=TextNode.ACenter)
        self.label("Nobody can tell you anything now.", (0, 0, 0.13), 0.030, DIM, align=TextNode.ACenter)
        self.button("Continue", (0, 0, -0.10), (0.5, 0.14), self.on_done, True, GREEN_2, 0.05)
