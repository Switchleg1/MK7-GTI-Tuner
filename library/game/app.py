from __future__ import annotations

import math
import random
import sys
import time

from panda3d.core import AmbientLight, ClockObject, DirectionalLight, MouseButton, PerspectiveLens, TextNode, Vec3, Vec4, WindowProperties

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from library.core.constants import (
    AMBER,
    APP_NAME,
    BG,
    BLACK,
    BLUE,
    CAMERA_BY_TAB,
    DEFAULT_ASPECT,
    DEFAULT_FOV_DEG,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    DIM,
    GEAR_RATIOS,
    GREEN,
    GREEN_2,
    LINE,
    MAX_LOG_LINES,
    MODS,
    MUTED,
    PANEL,
    PANEL_DARK,
    PRESETS,
    RED,
    RIVALS,
    ROAST,
    SIMON_BUTTON,
    SIMON_PANEL,
    TABS,
    TEXT,
    TIP,
    TIRE_CIRC,
    TRACK_M,
    UI_REFRESH_SECONDS,
    VIOLET,
    WHITE,
    WINDOW_TITLE,
)
from library.game.geometry import build_car, make_box, make_grid
from library.stages.mode_select_stage import ModeSelectStage
from library.core.panda_config import enable_gltf
from library.game.simos import build_context, select_insight
from library.game.tuning import clone_tune, compute_tune, default_tune, dyno_curve, grade_for_result, pop_score, rep_title
from library.stages.unlock_stage import UnlockStage
from library.core.utils import clamp


class MK7Tuner3D(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(BG)
        if self.win and hasattr(self.win, "requestProperties"):
            self.win.requestProperties(self.window_properties())
        if self.camLens is None:
            self.camLens = PerspectiveLens()
        self.camLens.setAspectRatio(DEFAULT_ASPECT)
        enable_gltf(self)

        self.ui_nodes = []
        self.ui_dirty = True
        self.last_ui_refresh = 0.0
        self.last_aspect = None

        self.connected = False
        self.read = False
        self.patched = False
        self.flashed = False
        self.switch_patch = False
        self.dirty = False
        self.tune = default_tune()
        self.flashed_tune = None
        self.slots = [clone_tune(PRESETS["stock"]), None, None, None]
        self.active_slot = 0
        self.cash = 750
        self.cred = 0.0
        self.karen = 0.0
        self.mods = {mod[0]: False for mod in MODS}
        self.tab = "bench"
        self.unlocked_tabs = set()
        self.logs = []
        self.simon_open = False
        self.simon_current = None
        self.simon_tick = 0
        self.rpm = 850.0
        self.throttle = 0.0
        self.dyno_result = None
        self.dyno_points = dyno_curve(210)
        self.dyno_running = False
        self.dyno_started = 0.0
        self.grade = ""
        self.selected_rival = 0
        self.unlocked_rival = 0
        self.race = None
        self.garage_built = False

        self.setup_lights()
        self.accept("escape", sys.exit)
        self.start_unlock()

    # -- stage flow: unlock cinematic -> mode select -> garage -------------
    def start_unlock(self):
        self.unlock = UnlockStage(self, on_complete=self.start_mode_select)

    def start_mode_select(self):
        self.mode_select = ModeSelectStage(self, on_pick=self.enter_garage)

    def enter_garage(self, tab="maps"):
        # The cinematic already connected, read, patched and flashed the ECU.
        self.connected = self.read = self.patched = self.flashed = True
        self.dirty = False
        self.flashed_tune = clone_tune(self.tune)
        self.slots = [clone_tune(self.tune), None, None, None]
        self.slots[0]["name"] = "Your Tune"
        self.active_slot = 0
        self.unlocked_tabs = {key for key, _ in TABS}
        if not self.garage_built:
            self.build_garage()
            self.garage_built = True
        self.tab = tab if tab in self.unlocked_tabs else "maps"
        self.camera_for_tab()
        self.ui_dirty = True

    def build_garage(self):
        self.scene_root = self.render.attachNewNode("scene-root")
        self.car_root = self.scene_root.attachNewNode("player-car")
        self.rival_root = self.scene_root.attachNewNode("rival-car")
        self.flames = []
        if self.camLens:
            self.camLens.setFov(DEFAULT_FOV_DEG)
        self.setup_scene()
        self.log("SimosTools bench - Panda3D renderer online.", "violet")
        self.log("ECU unlocked in the bay. Tune in MAPS, re-flash on the BENCH.", "info")
        self.accept("space", self.space_action)
        for index, tab in enumerate(TABS, start=1):
            self.accept(str(index), self.go_tab, [tab[0]])
        self.taskMgr.add(self.update, "update")
        self.taskMgr.add(self.refresh_ui_task, "refresh-ui")

    def window_properties(self) -> WindowProperties:
        props = WindowProperties()
        props.setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        props.setTitle(WINDOW_TITLE)
        return props

    def setup_lights(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.22, 0.28, 0.32, 1))
        self.render.setLight(self.render.attachNewNode(ambient))
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(0.72, 0.90, 1.0, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-35, -48, 0)
        self.render.setLight(sun_np)

    def setup_scene(self):
        floor = make_box("floor", 32, 42, 0.05, Vec4(0.06, 0.09, 0.11, 1))
        floor.reparentTo(self.scene_root)
        floor.setPos(0, 8, -0.04)
        road = make_box("road", 9, 48, 0.03, Vec4(0.045, 0.055, 0.06, 1))
        road.reparentTo(self.scene_root)
        road.setPos(0, 9, 0.0)
        make_grid(self.scene_root)
        build_car(self.car_root, Vec4(0.90, 0.10, 0.12, 1))
        self.car_root.setPos(0, 0, 0.45)
        build_car(self.rival_root, Vec4(0.35, 0.45, 0.95, 1))
        self.rival_root.setPos(-4.0, 6, 0.45)
        self.rival_root.hide()

    def log(self, message: str, kind: str = "dim"):
        self.logs.append((message, kind))
        self.logs = self.logs[-MAX_LOG_LINES:]
        if hasattr(self, "ui_dirty"):
            self.ui_dirty = True

    def clear_ui(self):
        for node in self.ui_nodes:
            node.destroy()
        self.ui_nodes.clear()

    def ui_frame(self, frame_size, pos, color=PANEL, border=LINE):
        node = DirectFrame(parent=self.aspect2d, frameSize=frame_size, frameColor=color, pos=pos, relief=DGG.FLAT)
        self.ui_nodes.append(node)
        if border:
            outline = DirectFrame(parent=node, frameSize=frame_size, frameColor=border, frameTexture=None, relief=DGG.RIDGE, borderWidth=(0.006, 0.006))
            self.ui_nodes.append(outline)
        return node

    def ui_label(self, text, pos, scale=0.045, color=TEXT, parent=None, align=TextNode.ALeft, wordwrap=None):
        node = DirectLabel(
            parent=parent or self.aspect2d,
            text=text,
            pos=pos,
            scale=scale,
            text_fg=color,
            text_align=align,
            text_wordwrap=wordwrap,
            frameColor=(0, 0, 0, 0),
            relief=None,
        )
        self.ui_nodes.append(node)
        return node

    def ui_button(self, text, pos, size, command, enabled=True, color=None, text_scale=0.046):
        width, height = size
        fill = color or (GREEN_2 if enabled else Vec4(0.05, 0.08, 0.10, 0.92))
        fg = WHITE if enabled else Vec4(0.32, 0.39, 0.43, 1)
        node = DirectButton(
            parent=self.aspect2d,
            text=text,
            command=(lambda cmd=command: self.run_ui_command(cmd)) if enabled and command else None,
            pos=pos,
            scale=1,
            text_scale=text_scale,
            text_fg=fg,
            text_align=TextNode.ACenter,
            frameSize=(-width / 2, width / 2, -height / 2, height / 2),
            frameColor=fill,
            relief=DGG.FLAT,
            pressEffect=0,
        )
        self.ui_nodes.append(node)
        return node

    def run_ui_command(self, command):
        command()
        self.ui_dirty = True

    def refresh_ui_task(self, task):
        if self.mouseWatcherNode and self.mouseWatcherNode.isButtonDown(MouseButton.one()):
            return Task.cont
        now = time.perf_counter()
        aspect = self.getAspectRatio()
        aspect_changed = self.last_aspect is None or abs(aspect - self.last_aspect) > 0.001
        live_tab = self.tab in {"dyno", "street", "race"} or self.dyno_running or self.race_active()
        timed_refresh = live_tab and now - self.last_ui_refresh > UI_REFRESH_SECONDS
        if self.ui_dirty or aspect_changed or timed_refresh:
            self.draw_ui()
            self.ui_dirty = False
            self.last_ui_refresh = now
            self.last_aspect = aspect
        return Task.cont

    def draw_ui(self):
        self.clear_ui()
        aspect = self.getAspectRatio()
        left, right = -aspect + 0.04, aspect - 0.04
        self.ui_frame((left, right, -0.085, 0.085), (0, 0, 0.86), PANEL)
        self.ui_label("SIMOS BENCH", (left + 0.04, 0, 0.89), 0.058, GREEN)
        self.ui_label("MK7 GTI  .  EA888  .  SIMOS18.1  .  POPS & BANGS  .  CAREER", (left + 0.04, 0, 0.825), 0.028, DIM)
        self.ui_label(f"${self.cash}", (right - 1.15, 0, 0.875), 0.038, GREEN)
        self.ui_label(f"ECU: {self.ecu_status()}", (right - 0.86, 0, 0.875), 0.034, TEXT)
        self.ui_label(f"MAP: {self.active_slot + 1} . {self.active_tune().get('name', 'Stock')}", (right - 0.46, 0, 0.875), 0.034, TEXT)
        self.ui_label(f"REP: {rep_title(self.cred)}", (right - 0.03, 0, 0.875), 0.034, TEXT, align=TextNode.ARight)
        self.draw_tabs(left, right)
        self.draw_main(left, right)
        self.ui_label("Parody bench sim. Real flashing can brick ECUs; street racing can lose licenses.", (0, 0, -0.965), 0.032, DIM, align=TextNode.ACenter)
        self.draw_simon(right)

    def draw_tabs(self, left, right):
        gap = 0.025
        width = (right - left - gap * (len(TABS) - 1)) / len(TABS)
        for index, (key, name) in enumerate(TABS):
            x = left + width / 2 + index * (width + gap)
            enabled = key in self.unlocked_tabs
            active = key == self.tab
            color = Vec4(0.05, 0.16, 0.10, 0.96) if active else Vec4(0.05, 0.08, 0.10, 0.88)
            if not enabled:
                color = Vec4(0.03, 0.045, 0.055, 0.76)
            self.ui_button(name, (x, 0, 0.66), (width, 0.13), lambda k=key: self.go_tab(k), enabled, color)

    def draw_main(self, left, right):
        draw_table = {
            "bench": self.draw_bench_ui,
            "maps": self.draw_maps_ui,
            "dyno": self.draw_dyno_ui,
            "street": self.draw_street_ui,
            "race": self.draw_race_ui,
            "shop": self.draw_shop_ui,
        }
        draw_table[self.tab](left, right)

    def panel_pair(self, left, right):
        gap = 0.04
        mid = (left + right) / 2
        boxes = ((left, mid - gap / 2, -0.62, 0.48), (mid + gap / 2, right, -0.62, 0.48))
        for box in boxes:
            self.ui_frame(box, (0, 0, 0), PANEL)
        return boxes

    def draw_bench_ui(self, left, right):
        lbox, rbox = self.panel_pair(left, right)
        self.ui_label("SIMOSTOOLS - RE-FLASH", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui_label("ECU is unlocked. Build a map in TUNE, then write it to the car here.", (lbox[0] + 0.05, 0, 0.29), 0.034, TEXT, wordwrap=24)
        self.ui_label(f"Loaded tune: {self.tune.get('name', 'Your Tune')}", (lbox[0] + 0.05, 0, 0.16), 0.036, TEXT)
        self.ui_button(f"switch patch: {'ON' if self.switch_patch else 'OFF'}", (lbox[0] + 0.32, 0, 0.02), (0.48, 0.10), self.toggle_switch, True)
        self.ui_button("FLASH ECU", ((lbox[0] + lbox[1]) / 2, 0, -0.24), (lbox[1] - lbox[0] - 0.12, 0.12), self.flash_ecu, True, GREEN_2)
        if self.dirty:
            self.ui_label("Flash required for changed tune.", (lbox[0] + 0.05, 0, -0.40), 0.033, AMBER)
        self.ui_label("BENCH LOG", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for offset, (msg, kind) in enumerate(self.logs[-9:]):
            self.ui_label(msg, (rbox[0] + 0.05, 0, 0.30 - offset * 0.08), 0.031, self.kind_color(kind), wordwrap=30)

    def draw_maps_ui(self, left, right):
        lbox, rbox = self.panel_pair(left, right)
        self.ui_label("CALIBRATION", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for offset, line in enumerate([f"Boost: {self.tune['boost']:.1f} psi", f"Timing: {self.tune['timing']:.1f} deg", f"Lambda: {self.tune['lambda']:.3f}", f"Fuel: {self.tune['fuel']}"]):
            self.ui_label(line, (lbox[0] + 0.07, 0, 0.28 - offset * 0.10), 0.043, TEXT)
        for index, (key, name) in enumerate([("stock", "Stock"), ("stage1", "Stage 1"), ("stage2", "Stage 2"), ("crackle", "Crackle")]):
            self.ui_button(name, (lbox[0] + 0.19 + index * 0.29, 0, -0.25), (0.25, 0.095), lambda k=key: self.apply_preset(k), True)
        self.ui_label("POPS & SLOTS", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui_label(f"Burble index: {round(pop_score(self.tune))}", (rbox[0] + 0.07, 0, 0.28), 0.052, AMBER)
        y = 0.16
        for index, slot in enumerate(self.slots):
            if not self.switch_patch and index > 0:
                continue
            label = f"Slot {index + 1}: {slot.get('name', 'empty') if slot else 'empty'}"
            self.ui_button(label, (rbox[0] + 0.34, 0, y), (0.56, 0.085), lambda idx=index: self.select_slot(idx), bool(slot))
            y -= 0.10
        self.ui_button("Assign Current Tune", (rbox[0] + 0.36, 0, -0.34), (0.58, 0.10), self.assign_slot, self.flashed)

    def draw_dyno_ui(self, left, right):
        self.ui_frame((left, right, -0.62, 0.48), (0, 0, 0), PANEL)
        self.ui_label("DYNO CELL", (left + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui_button("Run Dyno Pull", (left + 0.30, 0, 0.24), (0.42, 0.11), self.run_dyno, self.flashed and not self.dyno_running, GREEN_2)
        state = "pulling..." if self.dyno_running else "Loaded. Send it." if self.flashed else "Flash a tune first."
        self.ui_label(state, (left + 0.56, 0, 0.25), 0.036, AMBER if self.dyno_running else DIM)
        result = self.dyno_result or compute_tune(self.flashed_tune or self.tune, self.mods)
        self.ui_label(f"WHP {round(result['whp'])}   KR {result['KR']:.1f}   EGT {round(result['egt'])} C   REL {round(result['rel'])}%   POP {round(result['pop'])}", (left + 0.05, 0, 0.06), 0.045, TEXT)
        self.ui_label(self.grade or "Dyno results will appear here.", (left + 0.05, 0, -0.10), 0.038, GREEN if self.grade.startswith("Grade") else DIM, wordwrap=56)

    def draw_street_ui(self, left, right):
        self.ui_frame((left, right, -0.62, 0.48), (0, 0, 0), PANEL)
        self.ui_label("STREET MODE", (left + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui_label(f"{round(self.rpm)} RPM   Cred {round(self.cred)}   Karen {round(self.karen)}%", (left + 0.05, 0, 0.27), 0.044, TEXT)
        self.ui_button("Throttle", (left + 0.22, 0, 0.08), (0.32, 0.11), self.throttle_blip, self.flashed, GREEN_2)
        self.ui_button("Preview Pops", (left + 0.60, 0, 0.08), (0.36, 0.11), self.preview_pops, self.flashed)
        self.ui_label("The car/road are real 3D objects viewed through the 105 deg camera.", (left + 0.05, 0, -0.14), 0.036, DIM, wordwrap=56)

    def draw_race_ui(self, left, right):
        lbox, rbox = self.panel_pair(left, right)
        self.ui_label("QUARTER MILE", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui_button("Stage & Race", (lbox[0] + 0.28, 0, 0.22), (0.40, 0.11), self.start_race, self.flashed and not self.race_active(), GREEN_2)
        self.ui_button("Launch / Shift", (lbox[0] + 0.72, 0, 0.22), (0.40, 0.11), self.race_key, self.race_active())
        self.ui_label(self.race_result_text(), (lbox[0] + 0.05, 0, 0.02), 0.036, TEXT, wordwrap=30)
        self.ui_label("STREET LADDER", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for index, rival in enumerate(RIVALS):
            self.ui_button(f"{rival['name']} ${rival['purse']}", (rbox[0] + 0.45, 0, 0.27 - index * 0.09), (0.76, 0.075), lambda idx=index: self.select_rival(idx), index <= self.unlocked_rival)

    def draw_shop_ui(self, left, right):
        self.ui_frame((left, right, -0.62, 0.48), (0, 0, 0), PANEL)
        self.ui_label(f"SHOP - CASH ${self.cash}", (left + 0.05, 0, 0.40), 0.044, BLUE)
        for index, (mod_id, name, cost, _desc) in enumerate(MODS):
            row, col = divmod(index, 2)
            x = left + 0.28 + col * 0.82
            y = 0.25 - row * 0.12
            label = f"{name} - {'owned' if self.mods[mod_id] else '$' + str(cost)}"
            self.ui_button(label, (x, 0, y), (0.72, 0.08), lambda m=mod_id: self.buy_mod(m), not self.mods[mod_id] and self.cash >= cost)

    def draw_simon(self, right):
        self.ui_button("o_O  Ask Simon", (right - 0.30, 0, -0.82), (0.54, 0.12), self.ask_simon, True, SIMON_BUTTON, 0.050)
        if not self.simon_open or not self.simon_current:
            return
        popup = (right - 1.50, right - 0.05, -0.56, 0.40)
        self.ui_frame(popup, (0, 0, 0), SIMON_PANEL, VIOLET)
        self.ui_label("o_O", (popup[0] + 0.08, 0, 0.25), 0.066, AMBER)
        self.ui_label("SIMON", (popup[0] + 0.26, 0, 0.26), 0.058, VIOLET)
        self.ui_label("master tuner  .  zero chill", (popup[0] + 0.26, 0, 0.18), 0.032, DIM)
        self.ui_label(self.simon_current["roast"], (popup[0] + 0.07, 0, 0.02), 0.043, ROAST, wordwrap=28)
        self.ui_frame((popup[0] + 0.07, popup[1] - 0.07, -0.03, -0.025), (0, 0, 0), LINE, None)
        self.ui_label("Tip: " + self.simon_current["tip"], (popup[0] + 0.07, 0, -0.20), 0.038, TIP, wordwrap=30)
        self.ui_button("X", (popup[1] - 0.08, 0, 0.29), (0.10, 0.10), self.close_simon, True, PANEL_DARK, 0.058)

    def ecu_status(self):
        return "FLASHED" if self.flashed else "UNLOCKED" if self.patched else "LOCKED"

    def kind_color(self, kind: str):
        return {"ok": GREEN, "info": BLUE, "warn": AMBER, "err": RED, "violet": VIOLET}.get(kind, DIM)

    def update(self, task):
        self.update_scene(ClockObject.getGlobalClock().getDt())
        return Task.cont

    def update_scene(self, dt):
        self.rpm += (850 + self.throttle * 6200 - self.rpm) * clamp(dt * 5, 0, 1)
        self.car_root.setH(math.sin(time.perf_counter() * 1.4) * 1.4)
        for child in self.car_root.getChildren():
            if "wheel" in child.getName():
                child.setR(time.perf_counter() * (2 + self.rpm / 450) * 45)
        if self.tab == "race" and self.race_active():
            self.update_race_scene(dt)
        else:
            self.rival_root.hide()
            positions = {"street": (math.sin(time.perf_counter() * 0.8) * 0.25, 2, 0.45), "dyno": (0, 1, 0.55)}
            self.car_root.setPos(*positions.get(self.tab, (0, 0, 0.45)))
        if self.dyno_running and time.perf_counter() - self.dyno_started > 2.2:
            self.finish_dyno()
        self.update_flames(dt)

    def update_race_scene(self, dt):
        player, rival = self.race["p"], self.race["r"]
        self.car_root.setPos(-2.2, clamp(player["d"] / 28, 0, 16) - 4, 0.45)
        self.rival_root.show()
        self.rival_root.setPos(2.2, clamp(rival["d"] / 28, 0, 16) - 4, 0.45)
        self.step_race(dt)

    def update_flames(self, dt):
        for flame in list(self.flames):
            flame["life"] -= dt
            flame["node"].setScale(max(0.02, flame["life"] * 0.45))
            flame["node"].setPos(flame["node"].getPos() + Vec3(0, -dt * 4, dt * 1.4))
            if flame["life"] <= 0:
                flame["node"].removeNode()
                self.flames.remove(flame)

    def active_tune(self):
        return self.slots[self.active_slot] or self.flashed_tune or self.tune

    def active_pop(self):
        return pop_score(self.active_tune())

    def go_tab(self, tab):
        if tab in self.unlocked_tabs:
            self.tab = tab
            self.simon_open = False
            self.camera_for_tab()
            self.ui_dirty = True

    def camera_for_tab(self):
        if not self.camera:
            return
        camera = CAMERA_BY_TAB.get(self.tab, CAMERA_BY_TAB["default"])
        self.camera.setPos(*camera["pos"])
        self.camera.lookAt(*camera["look_at"])

    def toggle_switch(self):
        self.switch_patch = not self.switch_patch
        self.log("switch patch " + ("ENABLED" if self.switch_patch else "disabled"), "ok" if self.switch_patch else "dim")

    def flash_ecu(self):
        self.flashed = True
        self.dirty = False
        self.flashed_tune = clone_tune(self.tune)
        if self.switch_patch:
            self.slots = [clone_tune(PRESETS["stock"]), clone_tune(self.tune), clone_tune(PRESETS["stage2"]), clone_tune(PRESETS["crackle"])]
            self.slots[0]["name"] = "Valet"
            self.slots[1]["name"] = "Your Tune"
            self.active_slot = 1
        else:
            self.slots = [clone_tune(self.tune), None, None, None]
            self.slots[0]["name"] = "Your Tune"
            self.active_slot = 0
        self.unlocked_tabs.update(["dyno", "street", "race", "shop"])
        self.log("FLASH OK - Dyno, Street, Race & Shop unlocked.", "ok")

    def apply_preset(self, key):
        self.tune = clone_tune(PRESETS[key])
        self.dirty = self.flashed
        self.log(f"preset loaded: {self.tune['name']}", "info")

    def assign_slot(self):
        if self.flashed:
            self.slots[self.active_slot] = clone_tune(self.tune)
            self.slots[self.active_slot]["name"] = "Your Tune"
            self.log(f"assigned tune to slot {self.active_slot + 1}", "info")

    def select_slot(self, index):
        if index < len(self.slots) and self.slots[index]:
            self.active_slot = index

    def run_dyno(self):
        self.dyno_result = compute_tune(self.flashed_tune or self.tune, self.mods)
        self.dyno_points = dyno_curve(self.dyno_result["whp"])
        self.dyno_running = True
        self.dyno_started = time.perf_counter()
        self.throttle = 1.0
        self.log("dyno pull started", "info")

    def finish_dyno(self):
        self.dyno_running = False
        self.throttle = 0.0
        self.grade = grade_for_result(self.dyno_result)
        self.log("dyno pull complete: " + self.grade, "ok")

    def throttle_blip(self):
        self.throttle = 1.0
        self.spawn_flames()
        self.doMethodLater(0.55, self.release_throttle, "release-throttle")

    def release_throttle(self, task):
        self.throttle = 0.0
        self.ui_dirty = True
        return Task.done

    def preview_pops(self):
        self.spawn_flames(max(4, round(self.active_pop() / 10)))
        self.cred += self.active_pop() / 18
        self.karen = clamp(self.karen + self.active_pop() / 18, 0, 100)

    def spawn_flames(self, count=5):
        for _ in range(count):
            node = make_box("flame", 0.12, 0.12, 0.12, Vec4(1.0, random.uniform(0.35, 0.9), 0.08, 1))
            node.reparentTo(self.scene_root)
            node.setPos(self.car_root.getX() + random.uniform(-0.25, 0.25), self.car_root.getY() - 2.35, self.car_root.getZ() + 0.28)
            self.flames.append({"node": node, "life": random.uniform(0.45, 0.8)})

    def buy_mod(self, mod_id):
        mod = next(item for item in MODS if item[0] == mod_id)
        if self.mods[mod_id] or self.cash < mod[2]:
            return
        self.cash -= mod[2]
        self.mods[mod_id] = True
        self.log(f"installed {mod[1]}", "ok")

    def car_perf(self):
        result = compute_tune(self.flashed_tune or self.tune, self.mods)
        return {"whp": result["whp"], "weight": 1400 * (0.965 if self.mods["wheels"] else 1), "grip": 0.92 + (0.18 if self.mods["clutch"] else 0), "blown": result["blown"], "rel": result["rel"]}

    def race_active(self):
        return bool(self.race and self.race["active"])

    def select_rival(self, index):
        if index <= self.unlocked_rival:
            self.selected_rival = index

    def start_race(self):
        if not self.flashed or self.race_active():
            return
        perf = self.car_perf()
        if perf["blown"]:
            self.log("Your tune is a grenade. Fix it on dyno first.", "err")
            return
        self.race = {"active": True, "green_at": time.perf_counter() + 1.9, "rival_launch": time.perf_counter() + 2.15, "p": {"d": 0.0, "v": 0.0, "gear": 1, "launched": False, "done": False, "et": 0.0, "trap": 0.0}, "r": {"d": 0.0, "v": 0.0, "done": False, "et": 0.0, "trap": 0.0}}
        self.log("staged - launch on green", "info")

    def race_key(self):
        if not self.race_active():
            return
        player = self.race["p"]
        if not player["launched"]:
            player["launched"] = True
            self.log("launched" if time.perf_counter() >= self.race["green_at"] else "red light", "ok")
            return
        if player["gear"] < 6:
            player["gear"] += 1
            self.spawn_flames(2)

    def step_race(self, dt):
        if time.perf_counter() < self.race["green_at"]:
            return
        player, rival = self.race["p"], self.race["r"]
        rival_info = RIVALS[self.selected_rival]
        if player["launched"] and not player["done"]:
            perf = self.car_perf()
            self.step_car(player, perf["whp"], perf["weight"], perf["grip"], dt)
            if player["d"] >= TRACK_M:
                player["done"] = True
                player["et"] = time.perf_counter() - self.race["green_at"]
                player["trap"] = player["v"] * 2.237
        if time.perf_counter() >= self.race["rival_launch"] and not rival["done"]:
            self.step_car(rival, rival_info["whp"], rival_info["weight"], rival_info["grip"], dt)
            if rival["d"] >= TRACK_M:
                rival["done"] = True
                rival["et"] = time.perf_counter() - self.race["green_at"]
                rival["trap"] = rival["v"] * 2.237
        if player["done"] and rival["done"]:
            self.resolve_race(player, rival, rival_info)

    def step_car(self, car, whp, weight, grip, dt):
        force = min(weight * 9.81 * grip, whp * 745.7 / max(car["v"], 2))
        drag = 0.5 * 1.2 * 0.62 * car["v"] * car["v"]
        car["v"] = max(0, car["v"] + ((force - drag) / weight) * dt)
        car["d"] += car["v"] * dt

    def resolve_race(self, player, rival, rival_info):
        won = player["et"] < rival["et"]
        if won:
            purse = rival_info["purse"]
            self.cash += purse
            self.cred += round(purse / 5)
            if self.selected_rival == self.unlocked_rival and self.unlocked_rival < len(RIVALS) - 1:
                self.unlocked_rival += 1
        self.log(("WIN" if won else "LOSS") + f" {player['et']:.2f}s @ {round(player['trap'])} mph", "ok" if won else "warn")
        self.race["active"] = False

    def race_result_text(self):
        if not self.race:
            return "Launch on green. Shift with Space."
        if self.race_active():
            return f"You {self.race['p']['d']:.0f}m / Rival {self.race['r']['d']:.0f}m"
        return "Race complete. Check bench log."

    def space_action(self):
        if self.tab == "race":
            self.race_key()
        elif self.tab == "street":
            self.throttle_blip()

    def ask_simon(self):
        self.simon_current = select_insight(build_context(self), self.simon_tick)
        self.simon_tick += 1
        self.simon_open = True

    def close_simon(self):
        self.simon_open = False
