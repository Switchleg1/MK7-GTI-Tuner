from __future__ import annotations

import math
import random

from panda3d.core import NodePath, TextNode

from library.core.constants import (
    BLUE, DIM, GOD_PAYOUT, GREEN, GREEN_2, LINE, PAD_GOLD, PAD_GREEN, PAD_RED, PAD_TOP_Z,
    PADS_DECOY, PADS_LIVE, PANEL, PANEL_DARK, PIN_TOP_Z, RED, RIG_ORDER, TEXT, VIOLET, WHITE,
)
from library.core.utils import rgba
from library.game.geometry import make_box
from library.stages.hud import Hud
from library.stages.picker import Picker


class WizardTrialStage(Hud):
    """The Bench Wizard's secret Trial -- a three-part challenge a verified pro is
    summoned to once their cred is high enough:
      1. power the rig: click the lines in the right order (2D),
      2. probe the board: a 3D PCB -- drop the pogo pin on the live pads, dodge
         the decoys (real geometry + click-picking),
      3. sync window: hit DROP while the marker is in the green band (2D).
    Pass it -> ``Game.grant_god()`` (god status + a giant one-time payout), then back
    to the hub. Made-up flavour; no real procedure."""

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
        # 3D board (phase 2)
        self.board_root = None
        self.picker = None
        self.pads = []          # [{"label", "node"}]
        self.pin = None
        self.pin_anim = None     # {"x", "y", "t", "dur"}
        self.flash = None        # {"node", "t"}
        self._advance = False    # advance to phase 3 after the final tap

    # -- stage protocol ----------------------------------------------------
    def enter(self):
        random.shuffle(self.rig_slots)
        self.pad_slots = PADS_LIVE + PADS_DECOY
        random.shuffle(self.pad_slots)
        self.draw()

    def exit(self):
        self._clear_board()
        self.scene.removeNode()
        self.destroy()

    def render(self, dt):
        {
            2: self._render_probe_phase,
            3: self._render_sync_phase,
        }.get(self.phase, lambda _dt: None)(dt)
        self.ui.render(dt)  # 2D objects: visibility + the Abort/DROP/Continue click flash

    def _render_probe_phase(self, dt):
        if self.board_root is not None:
            self._animate_pin(dt)
            self._decay_flash(dt)

    def _render_sync_phase(self, dt):
        if self.marker is None:
            return
        self.t += dt
        x0, x1, _, _ = self.track
        frac = 0.5 + 0.5 * math.sin(self.t * 2.3)
        self.marker.node.setX(x0 + frac * (x1 - x0))

    # -- header / draw router ---------------------------------------------
    def _header(self, backdrop=True):
        left, right = self.bounds()
        if backdrop:
            self.ui.add_frame("backdrop", frame_size=(-2.0, 2.0, -1.0, 1.0), color=PANEL_DARK, border=None)  # 2D modal backdrop
        self.ui.add_frame("hdr-bg", frame_size=(left, right, 0.74, 0.94), pos=(0, 0, 0.84), color=PANEL, border=None)
        self.ui.add_image("hdr-av", "avatar", (left + 0.12, 0, 0.84), 0.06, color_scale=VIOLET)
        self.ui.add_text("hdr-title", "THE BENCH WIZARD", (left + 0.22, 0, 0.85), 0.046, VIOLET)
        self.ui.add_text("hdr-sub", "Pass the Trial. Three parts. No hints. No mercy.", (left + 0.22, 0, 0.79), 0.026, DIM)
        self.ui.add_button("abort", "Abort", (right - 0.12, 0, 0.84), (0.16, 0.09), self.on_done, True, PANEL, 0.034)

    def draw(self):
        self.ui.clear()
        self.marker = None
        if self.phase == 2:
            if self.board_root is None:
                self._build_board()
            self._header(backdrop=False)  # keep the 3D board visible
            self.ui.add_text("part", "PART 2 / 3", (0, 0, 0.66), 0.04, BLUE, align=TextNode.ACenter)
            self.ui.add_text("p2-instr", "PROBE THE BOARD - drop the pogo pin on the live pads: V+, DATA, CLK, GND.  Avoid the rest.",
                             (0, 0, 0.585), 0.027, TEXT, align=TextNode.ACenter, wordwrap=46)
            self.ui.add_text("p2-progress", f"live pads probed: {len(self.pad_hits)}/{len(PADS_LIVE)}", (0, 0, -0.86), 0.030, DIM, align=TextNode.ACenter)
            if self.msg:
                self.ui.add_text("p2-msg", self.msg, (0, 0, -0.92), 0.028, RED, align=TextNode.ACenter)
            return
        if self.board_root is not None:
            self._clear_board()
        self._header(backdrop=True)
        self.ui.add_text("part", f"PART {self.phase} / 3" if self.phase in (1, 3) else "", (0, 0, 0.66), 0.04, BLUE, align=TextNode.ACenter)
        if self.msg:
            self.ui.add_text("msg", self.msg, (0, 0, 0.58), 0.032, RED, align=TextNode.ACenter)
        {1: self._draw_rig, 3: self._draw_sync, "win": self._draw_win}[self.phase]()

    # -- part 1: power the rig (2D) ---------------------------------------
    def _draw_rig(self):
        self.ui.add_text("rig-title", "POWER THE RIG", (0, 0, 0.46), 0.05, GREEN, align=TextNode.ACenter)
        self.ui.add_text("rig-instr", "Bring the lines up in order:  POWER -> GROUND -> DATA -> CLOCK -> ENABLE",
                         (0, 0, 0.38), 0.030, TEXT, align=TextNode.ACenter)
        done = set(RIG_ORDER[:self.rig_done])
        for i, label in enumerate(self.rig_slots):
            x = -0.84 + i * 0.42
            on = label in done
            self.ui.add_button(f"rig-{i}", label + (" *" if on else ""), (x, 0, 0.10), (0.38, 0.16),
                               None if on else (lambda l=label: self._rig(l)), not on,
                               GREEN_2 if on else BLUE, 0.046)
        self.ui.add_text("rig-count", f"lines up: {self.rig_done}/{len(RIG_ORDER)}", (0, 0, -0.18), 0.030, DIM, align=TextNode.ACenter)

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

    # -- part 2: probe the board (3D) -------------------------------------
    def _build_board(self):
        self.picker = Picker(self.app)
        self.board_root = self.scene.attachNewNode("pogo-board")
        self.board_root.setLightOff()  # show flat vertex colors (make_box has no normals)
        make_box("pcb", 5.6, 3.7, 0.25, rgba("#0c3a20")).reparentTo(self.board_root)
        chip = make_box("chip", 1.1, 1.0, 0.22, rgba("#15171a")); chip.reparentTo(self.board_root); chip.setPos(-2.0, 1.05, 0.2)
        conn = make_box("conn", 5.0, 0.34, 0.2, rgba("#1b1f24")); conn.reparentTo(self.board_root); conn.setPos(0, -1.55, 0.2)
        self.pads = []
        cols, rows = (-1.6, 0.0, 1.6), (1.0, 0.0, -1.0)
        for i, label in enumerate(self.pad_slots):
            cx, cy = cols[i % 3], rows[i // 3]
            pad = make_box(f"pad{i}", 0.74, 0.74, 0.16, PAD_GOLD)
            pad.reparentTo(self.board_root)
            pad.setPos(cx, cy, 0.2)
            tn = TextNode(f"lbl{i}")
            tn.setText(label)
            tn.setAlign(TextNode.ACenter)
            tn.setTextColor(1, 1, 1, 1)
            if self.font:
                tn.setFont(self.font)
            lbl = self.board_root.attachNewNode(tn)
            lbl.setScale(0.34)
            lbl.setPos(cx, cy, 0.64)
            lbl.setBillboardPointEye()
            lbl.setLightOff()
            self.picker.register(pad, f"pad{i}", lambda l=label, n=pad: self._probe(l, n))
            self.pads.append({"label": label, "node": pad})
        self.pin = self._make_pin()
        self.pin.reparentTo(self.board_root)
        self.pin.hide()
        self.app.camera.setPos(0, -6.6, 4.4)
        self.app.camera.lookAt(0, 0.0, 0.25)
        if self.app.camLens:
            self.app.camLens.setFov(46)
        self._refresh_pads()

    def _make_pin(self):
        pin = NodePath("pogo-pin")
        barrel = make_box("pp_barrel", 0.16, 0.16, 0.8, rgba("#aeb6bd")); barrel.reparentTo(pin); barrel.setPos(0, 0, 0.72)
        make_box("pp_tip", 0.08, 0.08, 0.34, rgba("#ffd24a")).reparentTo(pin)  # tip bottom at z=0
        pin.getChild(1).setPos(0, 0, 0.17)
        wire = make_box("pp_wire", 0.05, 0.05, 0.7, rgba("#ff4d52")); wire.reparentTo(pin); wire.setPos(0, 0, 1.45)
        pin.setLightOff()
        return pin

    def _clear_board(self):
        if self.picker is not None:
            self.picker.destroy()
            self.picker = None
        if self.board_root is not None:
            self.board_root.removeNode()
            self.board_root = None
        self.pads = []
        self.pin = None
        self.pin_anim = None
        self.flash = None
        self._advance = False

    def _refresh_pads(self):
        for pad in self.pads:
            pad["node"].setColorScale(*(PAD_GREEN if pad["label"] in self.pad_hits else (1, 1, 1, 1)))

    def _probe(self, label, node):
        if self.pin_anim is not None:  # ignore clicks mid-tap
            return
        pos = node.getPos(self.board_root)
        self.pin.setPos(pos.getX(), pos.getY(), PIN_TOP_Z)
        self.pin.show()
        self.pin_anim = {"x": pos.getX(), "y": pos.getY(), "t": 0.0, "dur": 0.42}
        if label in PADS_LIVE:
            self.pad_hits.add(label)
            self.msg = ""
            self._refresh_pads()
            if len(self.pad_hits) >= len(PADS_LIVE):
                self._advance = True
        else:
            self.pad_hits.clear()
            self._refresh_pads()
            self.flash = {"node": node, "t": 0.5}
            self.msg = f"{label} is not live - magic smoke! probes reset."
        self.draw()  # refresh the 2D progress/msg overlay (the 3D board persists)

    def _animate_pin(self, dt):
        if self.pin_anim is None:
            return
        a = self.pin_anim
        a["t"] += dt
        prog = min(1.0, a["t"] / a["dur"])
        z = PIN_TOP_Z - (PIN_TOP_Z - PAD_TOP_Z) * math.sin(math.pi * prog)  # drop then retract
        self.pin.setPos(a["x"], a["y"], z)
        if prog >= 1.0:
            self.pin.hide()
            self.pin_anim = None
            if self._advance:
                self._advance = False
                self._clear_board()
                self.phase = 3
                self.t = 0.0
                self.draw()

    def _decay_flash(self, dt):
        if self.flash is None:
            return
        self.flash["t"] -= dt
        if self.flash["t"] <= 0:
            self.flash = None
            self._refresh_pads()
        else:
            self.flash["node"].setColorScale(*PAD_RED)

    # -- part 3: sync window (2D) -----------------------------------------
    def _draw_sync(self):
        self.ui.add_text("sync-title", "SYNC WINDOW", (0, 0, 0.46), 0.05, GREEN, align=TextNode.ACenter)
        self.ui.add_text("sync-instr", "Hit DROP while the marker is in the green band.", (0, 0, 0.38), 0.030, TEXT, align=TextNode.ACenter)
        x0, x1, win_lo, win_hi = -0.7, 0.7, -0.10, 0.10
        self.track = (x0, x1, win_lo, win_hi)
        self.ui.add_frame("sync-track", frame_size=(x0, x1, 0.02, 0.12), color=PANEL, border=LINE)
        self.ui.add_frame("sync-band", frame_size=(win_lo, win_hi, 0.02, 0.12), color=GREEN_2, border=None)
        self.marker = self.ui.add_frame("sync-marker", frame_size=(-0.012, 0.012, -0.01, 0.15), color=WHITE, border=None)
        self.ui.add_button("drop", "DROP", (0, 0, -0.18), (0.5, 0.16), self._drop, True, BLUE, 0.05)

    def _drop(self):
        if self.marker is None:
            return
        _, _, lo, hi = self.track
        if lo <= self.marker.node.getX() <= hi:
            self.phase = "win"
            self.game.grant_god()
            self.draw()
        else:
            self.msg = "missed the window - timeout. try again."
            self.draw()

    # -- win ---------------------------------------------------------------
    def _draw_win(self):
        self.ui.add_text("win-title", "TRIAL PASSED", (0, 0, 0.44), 0.075, GREEN, align=TextNode.ACenter)
        self.ui.add_text("win-1", "The Wizard nods. You have achieved GOD STATUS.", (0, 0, 0.31), 0.040, VIOLET, align=TextNode.ACenter)
        self.ui.add_text("win-2", f"+${GOD_PAYOUT:,} dropped into your account.", (0, 0, 0.21), 0.040, GREEN, align=TextNode.ACenter)
        self.ui.add_text("win-3", "Nobody can tell you anything now.", (0, 0, 0.13), 0.030, DIM, align=TextNode.ACenter)
        self.ui.add_button("continue", "Continue", (0, 0, -0.10), (0.5, 0.14), self.on_done, True, GREEN_2, 0.05)
