from __future__ import annotations

import time

from panda3d.core import TextNode, Vec4

import library.core.assets as assets
from library.core.constants import (
    AMBER, AUDIO, BLUE, BOX_LINE, DIM, FINAL_DRIVE, GEAR_RATIOS, GREEN, GREEN_2, LINE, PANEL, PANEL_DARK, RED, TEXT, TIRE_CIRC, TRACK_M, WHITE,
)
from library.core.utils import clamp
from library.game.geometry import make_box
from library.stages.task_base import TaskBase

# Chase camera framed BETWEEN the two lanes so BOTH cars are visible. A
# cockpit-only POV can't see the rival when they're side-by-side at start (they
# sit ~4m straight off to the side, which is outside any sane FOV). The cars
# still stay fixed and the world scrolls past, so it keeps the "world moves
# around you" feel from a broadcast/follow camera vantage.
SHIFT_RPM = 6500                # tach goes amber from 5500, red from here
CHASE_CAM_POS = (0.0, -8.0, 2.6)
CHASE_CAM_LOOK = (0.0, 14.0, 0.5)
CHASE_FOV = 55

RIVAL_X = 2.2                   # lateral lane offset (your car stays at -2.2)
RIVAL_GAP_SCALE = 0.18          # scene units per meter of (rival.d - player.d)

# Track markers (centre dashes + side cones) scroll at the player's velocity so
# motion is visible even though the car geometry doesn't move.
MARKER_RECYCLE_Y = 28.0
MARKER_PAST_Y = -4.0
DASH_SPACING_M = 7.0            # one centerline dash every ~7 metres
SCROLL_SCALE = 0.22             # scene units per metre of player travel


class RaceTask(TaskBase):
    """Quarter-mile vs the skreets ladder, broadcast-cam style.

    The two cars hold fixed scene Ys; the world scrolls past via recycling lane
    dashes and side cones, and both sets of wheels spin (TaskBase.prepare_wheels)
    so motion sells from a chase camera. The rival car's scene-Y is the live
    race gap in metres (so when they're ahead you actually see them ahead). The
    bottom HUD is a cockpit dash: a horizontal tach with green/amber/red zones
    and a swept needle, big digital RPM and gear, an MPH readout, and a shift
    light that lights at SHIFT_RPM."""

    title = "RACE"
    key = "race"
    live = True

    def build_scene(self):
        assets.load_model(assets.ModelType.GEOMETRY, "ground").reparentTo(self.scene)
        self.player_car = assets.load_model(assets.ModelType.CAR, "mk7_gti")
        self.player_car.reparentTo(self.scene)
        self.player_car.setPos(-2.2, 0, 0.0)
        self.player_wheels = self.prepare_wheels(self.player_car)
        self._load_rival_car()
        # Wheel pivots for both cars -- spun in tick so the cars look like they're
        # moving even though they hold their scene Y position.
        self.spin = 0.0
        self._build_track()
        # Chase camera (overrides TASK_CAMERAS["race"] for the duration of the stage).
        if self.app.camLens:
            self.app.camLens.setFov(CHASE_FOV)
        self.app.camera.setPos(*CHASE_CAM_POS)
        self.app.camera.lookAt(*CHASE_CAM_LOOK)
        # Cached dash widgets (rebuilt each redraw; tick checks for them).
        self.dash = {}
        self.race = None

    def _build_track(self):
        """Two rows of lane dashes + side cones laid out along +Y. Each is a
        plain procedural box parented to the scene, recycled in ``_scroll_world``."""
        self.markers = []
        y = 0.0
        while y < MARKER_RECYCLE_Y:
            for x in (-2.2, 2.2):  # one dash per lane
                dash = make_box("lane", 0.18, 1.2, 0.02, Vec4(0.92, 0.92, 0.92, 1))
                dash.setLightOff()
                dash.reparentTo(self.scene)
                dash.setPos(x, y, 0.02)
                self.markers.append(dash)
            for x in (-4.6, 4.6):  # side cones
                cone = make_box("cone", 0.30, 0.30, 0.55, Vec4(1.0, 0.45, 0.10, 1))
                cone.setLightOff()
                cone.reparentTo(self.scene)
                cone.setPos(x, y + DASH_SPACING_M * 0.5, 0.28)
                self.markers.append(cone)
            y += DASH_SPACING_M

    def _scroll_world(self, dy):
        """Move every recycled marker by ``dy`` (negative when the player is moving
        forward) and wrap any that have passed behind the camera."""
        for m in self.markers:
            m.setY(m.getY() + dy)
            if m.getY() < MARKER_PAST_Y:
                m.setY(m.getY() + MARKER_RECYCLE_Y)

    # -- per-frame ---------------------------------------------------------
    def tick(self, dt):
        if self.race and self.race["active"]:
            self._step_race(dt)
            player = self.race["p"]
            rival = self.race["r"]
            # Rival lane position = the literal gap, in scaled scene units.
            self.rival_car.setY((rival["d"] - player["d"]) * RIVAL_GAP_SCALE)
            # World scroll: lane dashes/cones travel backward at the player's speed.
            self._scroll_world(-player["v"] * SCROLL_SCALE * dt)
            # Spin each car's wheels at its own velocity (rival's may differ).
            self._spin_wheels(self.player_wheels, player["v"], dt)
            self._spin_wheels(self.rival_wheels, rival["v"], dt)
            gear = clamp(player["gear"], 1, len(GEAR_RATIOS))
            rpm = clamp(player["v"] / TIRE_CIRC * GEAR_RATIOS[gear - 1] * FINAL_DRIVE * 60, 850, 7300)
            mph = player["v"] * 2.237
            load = AUDIO["pull_load"] if player["launched"] and not player["done"] else 0.2
            self.app.audio.set_engine(rpm, load)
            self._update_dash(rpm, gear, mph)
        else:
            self.app.audio.idle(900)
            self._update_dash(850, 1, 0)

    def _spin_wheels(self, wheels, velocity_mps, dt):
        # Roughly: angular velocity (deg/s) = v / circumference * 360.
        if not wheels:
            return
        delta = velocity_mps / TIRE_CIRC * 360.0 * dt
        for w in wheels:
            w.setP(w.getP() - delta)
        # Status / hint / gap labels stay smooth between periodic redraws.
        if self.dash.get("status") is not None:
            text, _, hint = self._race_status()
            self.dash["status"]["text"] = text
            self.dash["hint"]["text"] = hint
            if self.race and self.race["active"]:
                gap = self.race["p"]["d"] - self.race["r"]["d"]
                if abs(gap) > 0.5:
                    self.dash["gap"]["text"] = (f"YOU +{gap:.0f}m" if gap > 0 else f"RIVAL +{-gap:.0f}m")
                    self.dash["gap"]["text_fg"] = GREEN if gap > 0 else RED
                else:
                    self.dash["gap"]["text"] = "DEAD EVEN"
                    self.dash["gap"]["text_fg"] = AMBER
            else:
                self.dash["gap"]["text"] = ""

    def _update_dash(self, rpm, gear, mph):
        d = self.dash
        if not d:
            return
        # Tach needle position.
        frac = clamp((rpm - 850) / (7300 - 850), 0, 1)
        d["needle"].setX(d["tach_x0"] + frac * (d["tach_x1"] - d["tach_x0"]))
        d["rpm"]["text"] = f"{int(rpm)}"
        d["gear"]["text"] = "N" if rpm <= 900 and gear == 1 else str(gear)
        d["mph"]["text"] = f"{int(mph)}"
        # Shift light: brightens (and the bezel goes red) past the redline.
        if rpm >= SHIFT_RPM:
            d["shift_bg"]["frameColor"] = (1.0, 0.20, 0.20, 0.90)
            d["shift_lbl"]["text_fg"] = WHITE
        else:
            d["shift_bg"]["frameColor"] = PANEL_DARK
            d["shift_lbl"]["text_fg"] = DIM

    def bind_keys(self):
        self.accept("space", self.do_key)

    def do_key(self):
        event = self._race_key()
        if event in ("launch", "shift"):
            self.spawn_flames(self.player_car, 2)
        if event == "shift":
            self.app.audio.bang()
            self.app.audio.overrun(28, 0.3)
        self.dirty = True

    def _race_status(self):
        race = self.race
        if not race:
            return "Pick a rival, then Stage & Race.", DIM, "SPACE launches on GREEN, then shifts gears."
        player, rival = race["p"], race["r"]
        now = time.perf_counter()
        if race["active"]:
            if now < race["green_at"]:
                if not player["launched"]:
                    return f"STAGED   {race['green_at'] - now:0.1f}s", AMBER, "Hands on the wheel. Wait for GREEN."
                return "WAIT FOR GREEN!", RED, "Pre-loaded - you'll roll the moment it goes green."
            if not player["launched"]:
                return "GREEN - GO!", GREEN, "Press SPACE to LAUNCH now!"
            return "GO!", GREEN, f"SPACE to shift  (gear {player['gear']})"
        won = player["et"] < rival["et"] if rival["et"] else True
        foe = self.game.rivals[self.game.bro.selected_rival]
        if won:
            return (f"WIN!  {player['et']:.2f}s @ {player['trap']:.0f} mph", GREEN,
                    f"+${foe.purse} banked. Rival ran {rival['et']:.2f}s. Stage to run it again.")
        return (f"LOSS  {player['et']:.2f}s @ {player['trap']:.0f} mph", RED,
                f"Rival ran {rival['et']:.2f}s. Tune up or buy parts, then run it back.")

    # -- UI ----------------------------------------------------------------
    def build_ui(self, left, right):
        game = self.game
        text, color, hint = self._race_status()
        self.dash["status"] = self.label(text, (0, 0, 0.92), 0.046, color, align=TextNode.ACenter, wordwrap=44)
        self.dash["hint"] = self.label(hint, (0, 0, 0.85), 0.028, DIM, align=TextNode.ACenter, wordwrap=64)
        self.dash["gap"] = self.label("", (0, 0, 0.77), 0.044, AMBER, align=TextNode.ACenter)
        # Skreets ladder (smaller, top-right).
        self.label("SKREETS LADDER", (right - 0.05, 0, 0.66), 0.030, BLUE, align=TextNode.ARight)
        for index, rival in enumerate(game.rivals):
            sel = index == game.bro.selected_rival
            self.button(f"{rival.name}  ${rival.purse}",
                        (right - 0.42, 0, 0.58 - index * 0.075), (0.78, 0.062),
                        self.bind(self._select_rival, index),
                        index <= game.bro.unlocked_rival,
                        GREEN_2 if sel else None, 0.026)
        # Stage / Launch (top-left).
        staged = self._race_active()
        launching = (not staged) or not self.race["p"]["launched"]
        self.button("Stage & Race", (left + 0.22, 0, 0.66), (0.40, 0.085),
                    self.bind(self._start_race), game.car.flashed and not staged, GREEN_2, 0.032)
        self.button(("Launch" if launching else "Shift") + " (SPACE)",
                    (left + 0.22, 0, 0.56), (0.40, 0.085), self.do_key, staged, None, 0.032)
        self._build_dash(left, right)

    def _build_dash(self, left, right):
        d = self.dash
        # Tach bar geometry (bottom centre).
        d["tach_x0"], d["tach_x1"] = -0.72, 0.72
        z0, z1 = -0.82, -0.76
        span = d["tach_x1"] - d["tach_x0"]
        # Backdrop + zone fills.
        self.frame((d["tach_x0"] - 0.01, d["tach_x1"] + 0.01, z0 - 0.012, z1 + 0.012),
                   color=PANEL_DARK, border=BOX_LINE)
        amber_x = d["tach_x0"] + (5500 - 850) / (7300 - 850) * span
        red_x = d["tach_x0"] + (SHIFT_RPM - 850) / (7300 - 850) * span
        self.frame((d["tach_x0"], amber_x, z0, z1), color=GREEN_2, border=None)
        self.frame((amber_x, red_x, z0, z1), color=AMBER, border=None)
        self.frame((red_x, d["tach_x1"], z0, z1), color=RED, border=None)
        # Tick marks every 1000 rpm.
        for r in (1000, 2000, 3000, 4000, 5000, 6000, 7000):
            tx = d["tach_x0"] + (r - 850) / (7300 - 850) * span
            self.frame((tx - 0.003, tx + 0.003, z1, z1 + 0.025), color=WHITE, border=None)
            self.label(f"{r // 1000}", (tx, 0, z1 + 0.035), 0.022, DIM, align=TextNode.ACenter)
        # Needle (positioned in _update_dash).
        d["needle"] = self.frame((-0.006, 0.006, -0.058, 0.058), color=WHITE, border=None)
        d["needle"].setPos(d["tach_x0"], 0, (z0 + z1) / 2)
        # Big digital RPM (above the tach).
        d["rpm"] = self.label("0", (0, 0, -0.69), 0.075, TEXT, align=TextNode.ACenter)
        self.label("RPM", (0, 0, -0.62), 0.024, DIM, align=TextNode.ACenter)
        # Gear letter (left of the tach).
        gx = d["tach_x0"] - 0.13
        self.frame((gx - 0.10, gx + 0.10, -0.90, -0.66), color=PANEL_DARK, border=BOX_LINE)
        d["gear"] = self.label("N", (gx, 0, -0.84), 0.085, GREEN, align=TextNode.ACenter)
        self.label("GEAR", (gx, 0, -0.69), 0.022, DIM, align=TextNode.ACenter)
        # MPH (right of the tach).
        mx = d["tach_x1"] + 0.13
        self.frame((mx - 0.10, mx + 0.10, -0.90, -0.66), color=PANEL_DARK, border=BOX_LINE)
        d["mph"] = self.label("0", (mx, 0, -0.83), 0.075, TEXT, align=TextNode.ACenter)
        self.label("MPH", (mx, 0, -0.69), 0.022, DIM, align=TextNode.ACenter)
        # Shift light (centre, above the RPM digits).
        d["shift_bg"] = self.frame((-0.11, 0.11, -0.58, -0.50), color=PANEL_DARK, border=BOX_LINE)
        d["shift_lbl"] = self.label("SHIFT", (0, 0, -0.555), 0.034, DIM, align=TextNode.ACenter)
        
    def _select_rival(self, index: int):
        if index <= self.game.bro.unlocked_rival:
            self.game.bro.selected_rival = index
            self._load_rival_car()
            
    def _load_rival_car(self):
        rival = self.game.rivals[self.game.bro.selected_rival]
        if rival:
            self.rival_car = assets.load_model(assets.ModelType.CAR, rival.model)
            self.rival_car.reparentTo(self.scene)
            self.rival_car.setColorScale(0.5, 0.6, 1.25, 1)
            self.rival_car.setPos(RIVAL_X, 0, 0.0)
            self.rival_wheels = self.prepare_wheels(self.rival_car)
        else:
            self.rival_car = None
            self.rival_wheels = None

    def _race_active(self) -> bool:
        return bool(self.race and self.race["active"])

    def _start_race(self) -> str | None:
        if not self.game.car.flashed or self._race_active():
            return None
        if self.game.car.car_perf()["blown"]:
            self.game.log("Your tune is a grenade. Fix it on dyno first.", "err")
            return "blown"
        now = time.perf_counter()
        self.race = {"active": True, "green_at": now + 1.9, "rival_launch": now + 2.15,
                     "p": {"d": 0.0, "v": 0.0, "gear": 1, "launched": False, "done": False, "et": 0.0, "trap": 0.0},
                     "r": {"d": 0.0, "v": 0.0, "done": False, "et": 0.0, "trap": 0.0}}
        self.game.log("staged - launch on green", "info")
        return "staged"
    
    def _race_key(self) -> str | None:
        if not self._race_active():
            return None
        player = self.race["p"]
        if not player["launched"]:
            player["launched"] = True
            self.game.log("launched" if time.perf_counter() >= self.race["green_at"] else "red light", "ok")
            return "launch"
        if player["gear"] < 6:
            player["gear"] += 1
            return "shift"
        return None

    def _step_race(self, dt: float):
        if time.perf_counter() < self.race["green_at"]:
            return
        player, rival = self.race["p"], self.race["r"]
        foe = self.game.rivals[self.game.bro.selected_rival]
        if player["launched"] and not player["done"]:
            perf = self.game.car.car_perf()
            self._step_car(player, perf["whp"], perf["weight"], perf["grip"], dt)
            if player["d"] >= TRACK_M:
                player["done"], player["et"], player["trap"] = True, time.perf_counter() - self.race["green_at"], player["v"] * 2.237
        if time.perf_counter() >= self.race["rival_launch"] and not rival["done"]:
            self._step_car(rival, foe.whp, foe.weight, foe.grip, dt)
            if rival["d"] >= TRACK_M:
                rival["done"], rival["et"], rival["trap"] = True, time.perf_counter() - self.race["green_at"], rival["v"] * 2.237
        if player["done"] and rival["done"]:
            self._resolve_race(player, rival, foe)

    def _step_car(self, car, whp, weight, grip, dt):
        force = min(weight * 9.81 * grip, whp * 745.7 / max(car["v"], 2))
        drag = 0.5 * 1.2 * 0.62 * car["v"] * car["v"]
        car["v"] = max(0, car["v"] + ((force - drag) / weight) * dt)
        car["d"] += car["v"] * dt

    def _resolve_race(self, player, rival, foe):
        game = self.game
        won = player["et"] < rival["et"]
        if won:
            game.bro.earn(foe.purse)
            game.bro.add_cred(round(foe.purse / 5))
            game.unlock("first_win", "Won Some Cash")
            if game.bro.selected_rival == game.bro.unlocked_rival and game.bro.unlocked_rival < len(game.rivals) - 1:
                game.bro.unlocked_rival += 1
                game.unlock("ladder", "Climbing the Ladder")
            if game.bro.selected_rival == len(game.rivals) - 1:
                game.unlock("king", "King of the Streets")
            game.dave("win")
        else:
            game.dave("lose")
        game.log(("WIN" if won else "LOSS") + f" {player['et']:.2f}s @ {round(player['trap'])} mph", "ok" if won else "warn")
        game.maybe_green()
        self.race["active"] = False

    def _race_result_text(self) -> str:
        if not self.race:
            return "Launch on green. Shift with Space."
        if self._race_active():
            return f"You {self.race['p']['d']:.0f}m / Rival {self.race['r']['d']:.0f}m"
        return "Race complete. Check the log."