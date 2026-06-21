from __future__ import annotations

import random
import time

from panda3d.core import CardMaker, MovieTexture, TextNode, Vec4

import library.core.assets as assets
from library.core.constants import (
    AMBER, AUDIO, BLUE, BOX_LINE, CHASE_CAM_LOOK, CHASE_CAM_POS, CHASE_FOV, DIM, ED_HEAL_ON_WIN,
    ED_LOSS, ED_RACE_GRIP_PENALTY, ED_RACE_WHP_PENALTY, ED_TAUNT_THRESHOLD,
    GREEN, GREEN_2, OVERLAY_BIN, OVERLAY_SORT, PANEL_DARK, RED, TEXT, TRACK_M, WHITE,
)
from library.core.utils import clamp
from library.game.geometry import make_box
from library.game.tuning import whp_at
from library.stages.task_base import TaskBase

SHIFT_RPM = 6500                # tach goes amber from 5500, red from here (chase cam lives in constants)

RIVAL_X = 2.2                   # lateral lane offset (your car stays at -2.2)
RIVAL_GAP_SCALE = 0.18          # scene units per meter of (rival.d - player.d)

# Track markers (centre dashes + side cones) scroll at the player's velocity so
# motion is visible even though the car geometry doesn't move.
MARKER_RECYCLE_Y = 28.0
MARKER_PAST_Y = -4.0
DASH_SPACING_M = 7.0            # one centerline dash every ~7 metres
SCROLL_SCALE = 0.22             # scene units per metre of player travel
RESULT_VIDEO_FALLBACK_SECONDS = 5.0
RESULT_VIDEO_AUDIO_DELAY_SECONDS = 0.50


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
    live = False
    flash_interval = 0.5

    def build_scene(self):
        self.next_flash         = 0
        self.show_warning       = False
        assets.load_model(assets.ModelType.GEOMETRY, "ground").reparentTo(self.scene)
        self.player_car         = assets.load_model(assets.ModelType.CAR, "mk7_gti")
        self.player_car.reparentTo(self.scene)
        self.player_car.setPos(-2.2, 0, 0.0)
        self.player_wheels      = self.prepare_wheels(self.player_car)
        self.rival_car          = None       # set by _load_rival_car (which replaces any current one)
        self.rival_wheels       = None
        self._rival_model       = None
        self._load_rival_car()
        # Wheel pivots for both cars -- spun in tick so the cars look like they're
        # moving even though they hold their scene Y position.
        self.spin               = 0.0
        self._build_track()
        # Chase camera (overrides TASK_CAMERAS["race"] for the duration of the stage).
        if self.app.camLens:
            self.app.camLens.setFov(CHASE_FOV)
        self.app.camera.setPos(*CHASE_CAM_POS)
        self.app.camera.lookAt(*CHASE_CAM_LOOK)
        # Cached dash widgets, built once in build_ui and updated per-frame.
        self.dash               = {}
        self.race               = None
        self.result_video       = None
        self.music_paused_for_video = False

    def exit(self):
        self._clear_result_video(restore_controls=False)
        super().exit()

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
        #update blown engine warning
        if self.game.car.car_perf()["blown"]:
            self.next_flash -= dt
            while self.next_flash <= 0.0:
                self.show_warning = not self.show_warning
                self.next_flash += self.flash_interval
            self.ui.get("blown").is_visible(self.show_warning)
        else:
            self.ui.get("blown").is_visible(False)
            
        self._update_result_video(dt)
        if self.result_video is not None:
            self.app.audio.silence()
            return
        if self.race and self.race["active"]:
            self._step_race(dt)
            player = self.race["p"]
            rival = self.race["r"]
            # Rival lane position = the literal gap, in scaled scene units.
            self.rival_car.setY((rival["d"] - player["d"]) * RIVAL_GAP_SCALE)
            # World scroll: lane dashes/cones travel backward at the player's speed.
            self._scroll_world(-player["v"] * SCROLL_SCALE * dt)
            # Spin each car's wheels at its own velocity (rival's may differ).
            foe = self.game.rivals[self.game.bro.selected_rival]
            self._spin_wheels(self.player_wheels, player["v"], dt, self.game.car.tire_circ)
            self._spin_wheels(self.rival_wheels, rival["v"], dt, foe.car.tire_circ)
            gear = int(clamp(player["gear"], 1, len(self.game.car.gears)))
            rpm = self._engine_rpm(player, self.game.car)
            mph = player["v"] * 2.237
            load = AUDIO["pull_load"] if player["launched"] and not player["done"] else 0.2
            self.app.audio.set_engine(rpm, load)
            self._update_dash(rpm, gear, mph)
            self._update_status()
        else:
            self.app.audio.idle(900)
            self._update_dash(self.game.car.idle, 1, 0)
            self._update_status()

    def _spin_wheels(self, wheels, velocity_mps, dt, tire_circ):
        # Roughly: angular velocity (deg/s) = v / circumference * 360.
        if not wheels:
            return
        delta = velocity_mps / tire_circ * 360.0 * dt
        for w in wheels:
            w.setP(w.getP() - delta)

    def _engine_rpm(self, state, car) -> float:
        """Engine rpm from road speed, the car's current gear, final drive and tire
        circumference -- clamped to the car's idle..redline."""
        gear = int(clamp(state.get("gear", 1), 1, len(car.gears)))
        rpm = state["v"] / car.tire_circ * car.gears[gear - 1] * car.final_drive * 60
        return clamp(rpm, car.idle, car.redline)

    def _update_status(self):
        # Status / hint / gap labels stay smooth without periodic redraws.
        status = self.ui.get("status")
        if status is not None:
            text, color, hint = self._race_status()
            status.text(text)
            status.color(color)
            self.ui.get("hint").text(hint)
            gap_lbl = self.ui.get("gap")
            if self.race and self.race["active"]:
                gap = self.race["p"]["d"] - self.race["r"]["d"]
                if abs(gap) > 0.5:
                    gap_lbl.text(f"YOU +{gap:.0f}m" if gap > 0 else f"RIVAL +{-gap:.0f}m")
                    gap_lbl.color(GREEN if gap > 0 else RED)
                else:
                    gap_lbl.text("DEAD EVEN")
                    gap_lbl.color(AMBER)
            else:
                gap_lbl.text("")

    def _update_dash(self, rpm, gear, mph):
        d = self.dash
        if not d.get("needle"):
            return
        # Tach needle position (a frame); the digits are managed text.
        frac = clamp((rpm - 850) / (7300 - 850), 0, 1)
        d["needle"].node.setX(d["tach_x0"] + frac * (d["tach_x1"] - d["tach_x0"]))
        self.ui.get("rpm").text(f"{int(rpm)}")
        self.ui.get("gear").text("N" if rpm <= 900 and gear == 1 else str(gear))
        self.ui.get("mph").text(f"{int(mph)}")
        # Shift light: brightens (and the bezel goes red) past the redline.
        if rpm >= SHIFT_RPM:
            d["shift_bg"].color((1.0, 0.20, 0.20, 0.90))
            self.ui.get("shift").color(WHITE)
        else:
            d["shift_bg"].color(PANEL_DARK)
            self.ui.get("shift").color(DIM)

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
    def build_ui(self):
        game = self.game
        left, right = self.bounds()
        C, R = TextNode.ACenter, TextNode.ARight
        # Skreets ladder (top-right): one button per rival, fixed positions.
        for index, rival in enumerate(game.rivals):
            self.ui.add_button(f"rival-{index}", f"{rival.name}  ${rival.purse}",
                               (right - 0.42, 0, 0.58 - index * 0.075), (0.78, 0.062),
                               self.bind(self._select_rival, index),
                               index <= game.bro.unlocked_rival, GREEN_2, 0.026)
        self.ui.add_button("stage", "Stage & Race", (left + 0.22, 0, 0.66), (0.40, 0.085),
                           self.bind(self._start_race), game.car.flashed, GREEN_2, 0.032)
        self.ui.add_button("launch", "Launch (SPACE)", (left + 0.22, 0, 0.56), (0.40, 0.085),
                           self.do_key, False, None, 0.032)
        # Status / ladder title / emotional-damage readout.
        self.ui.add_text("blown", "*Engine is blown - Go Fix it*", (0, 0.0, 0.25), 0.10, RED, C, is_visible=True)
        self.ui.add_text("status", "", (0, 0, 0.92), 0.046, TEXT, C, wordwrap=44)
        self.ui.add_text("hint", "", (0, 0, 0.85), 0.028, DIM, C, wordwrap=64)
        self.ui.add_text("gap", "", (0, 0, 0.77), 0.044, AMBER, C)
        self.ui.add_text("ladder-title", "SKREETS LADDER", (right - 0.05, 0, 0.66), 0.030, BLUE, R, is_visible=False)
        self.ui.add_text("ed", "", (left + 0.22, 0, 0.47), 0.026, DIM, C)
        self.ui.add_text("ed-hint", "shaky hands - launches suffer", (left + 0.22, 0, 0.435), 0.020, DIM, C, is_visible=False)
        # Tach dash geometry and labels. Everything here is built once; tick/build_ui
        # only move the needle and update text/color/visibility.
        self._build_dash_objects()
        tx0, tx1, z1 = -0.72, 0.72, -0.76
        span = tx1 - tx0
        for r in (1000, 2000, 3000, 4000, 5000, 6000, 7000):
            tx = tx0 + (r - 850) / (7300 - 850) * span
            self.ui.add_text(f"tach-{r}", f"{r // 1000}", (tx, 0, z1 + 0.035), 0.022, DIM, C)
        self.ui.add_text("rpm", "0", (0, 0, -0.69), 0.075, TEXT, C)
        self.ui.add_text("t-rpm", "RPM", (0, 0, -0.62), 0.024, DIM, C)
        self.ui.add_text("gear", "N", (tx0 - 0.13, 0, -0.84), 0.085, GREEN, C)
        self.ui.add_text("t-gear", "GEAR", (tx0 - 0.13, 0, -0.69), 0.022, DIM, C)
        self.ui.add_text("mph", "0", (tx1 + 0.13, 0, -0.83), 0.075, TEXT, C)
        self.ui.add_text("t-mph", "MPH", (tx1 + 0.13, 0, -0.69), 0.022, DIM, C)
        self.ui.add_text("shift", "SHIFT", (0, 0, -0.555), 0.034, DIM, C)

    def update_ui(self, left, right):
        game = self.game
        staged = self._race_active()
        self.ui.get("ladder-title").is_visible(not staged)
        for index in range(len(game.rivals)):
            button = self.ui.get(f"rival-{index}")
            button.is_visible(not staged)
            button.enabled(index <= game.bro.unlocked_rival)
            button.color(RED if index == game.bro.selected_rival else GREEN_2)
        launching = (not staged) or not self.race["p"]["launched"]
        self.ui.get("stage").enabled(game.car.flashed and not staged and self.result_video is None)
        launch = self.ui.get("launch")
        launch.text(("Launch" if launching else "Shift") + " (SPACE)")
        launch.enabled(staged)
        # Status / hint (also updated smoothly in tick via _spin_wheels).
        text, color, hint = self._race_status()
        status = self.ui.get("status")
        status.text(text)
        status.color(color)
        self.ui.get("hint").text(hint)
        # Emotional damage readout (it saps power + launch grip on the strip).
        ed = game.bro.emotional_damage
        ed_lbl = self.ui.get("ed")
        ed_lbl.text(f"EMOTIONAL DAMAGE  {round(ed)}%")
        ed_lbl.color(RED if ed >= 60 else AMBER if ed >= 30 else DIM)
        self.ui.get("ed-hint").is_visible(ed >= ED_TAUNT_THRESHOLD)
                
    def _build_dash_objects(self):
        d = self.dash
        d["tach_x0"], d["tach_x1"] = -0.72, 0.72
        z0, z1 = -0.82, -0.76
        span = d["tach_x1"] - d["tach_x0"]
        amber_x = d["tach_x0"] + (5500 - 850) / (7300 - 850) * span
        red_x = d["tach_x0"] + (SHIFT_RPM - 850) / (7300 - 850) * span

        self.ui.add_frame(
            "dash-tach-bg",
            frame_size=(d["tach_x0"] - 0.01, d["tach_x1"] + 0.01, z0 - 0.012, z1 + 0.012),
            color=PANEL_DARK, border=BOX_LINE)
        self.ui.add_frame("dash-zone-green", frame_size=(d["tach_x0"], amber_x, z0, z1),
                          color=GREEN_2, border=None)
        self.ui.add_frame("dash-zone-amber", frame_size=(amber_x, red_x, z0, z1),
                          color=AMBER, border=None)
        self.ui.add_frame("dash-zone-red", frame_size=(red_x, d["tach_x1"], z0, z1),
                          color=RED, border=None)
        for r in (1000, 2000, 3000, 4000, 5000, 6000, 7000):
            tx = d["tach_x0"] + (r - 850) / (7300 - 850) * span
            self.ui.add_frame(f"dash-tick-{r}", frame_size=(tx - 0.003, tx + 0.003, z1, z1 + 0.025),
                              color=WHITE, border=None)
        d["needle"] = self.ui.add_frame("dash-needle", frame_size=(-0.006, 0.006, -0.058, 0.058),
                                        color=WHITE, border=None)
        d["needle"].pos((d["tach_x0"], 0, (z0 + z1) / 2))

        gx = d["tach_x0"] - 0.13
        self.ui.add_frame("dash-gear-box", frame_size=(gx - 0.10, gx + 0.10, -0.90, -0.66),
                          color=PANEL_DARK, border=BOX_LINE)
        mx = d["tach_x1"] + 0.13
        self.ui.add_frame("dash-mph-box", frame_size=(mx - 0.10, mx + 0.10, -0.90, -0.66),
                          color=PANEL_DARK, border=BOX_LINE)
        d["shift_bg"] = self.ui.add_frame("dash-shift-bg", frame_size=(-0.11, 0.11, -0.58, -0.50),
                                          color=PANEL_DARK, border=BOX_LINE)
        
    def _select_rival(self, index: int):
        if index <= self.game.bro.unlocked_rival:
            self.game.bro.selected_rival = index
            self._load_rival_car()
            
    def _load_rival_car(self):
        """(Re)load the selected rival's car, REPLACING any current one. The previous
        version never removed the old model, so selecting a rival left the old car
        orphaned in the scene -- two rivals showing, one moving (the live one) and one
        static. We remove the old node first, and skip the reload entirely when the
        model is unchanged (just re-stage it) so tapping the ladder isn't a stutter."""
        rival = self.game.rivals[self.game.bro.selected_rival]
        model = rival.model if rival else None
        if model and model == self._rival_model and self.rival_car:
            self.rival_car.setPos(RIVAL_X, 0, 0.0)  # same model already loaded; just re-stage
            return
        if self.rival_car:
            self.rival_car.removeNode()  # also frees its wheel pivots (children)
        self._rival_model = model
        if model:
            self.rival_car = assets.load_model(assets.ModelType.CAR, model)
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
        if self.result_video is not None or not self.game.car.flashed or self._race_active():
            return None
        if self.game.car.car_perf()["blown"]:
            self.game.log("Your tune is a grenade. Fix it on dyno first.", "err")
            return "blown"
        now = time.perf_counter()
        self.allow_back = False
        self.game.set_advisors_visible(False)  # clear the Ask pills while the race is live
        # Build each car's power curve + mass/grip ONCE for the run (avoids rebuilding the
        # curve every physics frame); the race steps both off these.
        foe = self.game.rivals[self.game.bro.selected_rival]
        p_perf = self.game.car.car_perf()
        r_perf = foe.car.car_perf()
        self.race = {"active": True, "green_at": now + 1.9, "rival_launch": now + 2.15,
                     "p": {"d": 0.0, "v": 0.0, "gear": 1, "launched": False, "done": False, "et": 0.0, "trap": 0.0},
                     "r": {"d": 0.0, "v": 0.0, "gear": 1, "done": False, "et": 0.0, "trap": 0.0},
                     "p_curve": p_perf["curve"], "p_weight": p_perf["weight"], "p_grip": p_perf["grip"],
                     "r_curve": r_perf["curve"], "r_weight": r_perf["weight"], "r_grip": r_perf["grip"]}
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
        race = self.race
        player, rival = race["p"], race["r"]
        foe = self.game.rivals[self.game.bro.selected_rival]
        if player["launched"] and not player["done"]:
            # Emotional damage = shaky hands: less power and launch grip. The player
            # shifts manually (SPACE); off-curve gears now cost you real time.
            ed = self.game.bro.emotional_damage / 100.0
            self._step_car(player, self.game.car, race["p_curve"], race["p_weight"], race["p_grip"], dt,
                           whp_scale=1 - ed * ED_RACE_WHP_PENALTY, grip_scale=1 - ed * ED_RACE_GRIP_PENALTY)
            if player["d"] >= TRACK_M:
                player["done"], player["et"], player["trap"] = True, time.perf_counter() - race["green_at"], player["v"] * 2.237
        if time.perf_counter() >= race["rival_launch"] and not rival["done"]:
            self._auto_shift(rival, foe.car)  # the rival bangs gears near its redline
            self._step_car(rival, foe.car, race["r_curve"], race["r_weight"], race["r_grip"], dt)
            if rival["d"] >= TRACK_M:
                rival["done"], rival["et"], rival["trap"] = True, time.perf_counter() - race["green_at"], rival["v"] * 2.237
        if player["done"] and rival["done"]:
            self._resolve_race(player, rival, foe)

    def _step_car(self, state, car, curve, weight, grip, dt, whp_scale=1.0, grip_scale=1.0):
        """Power-limited launch: tractive force is grip-capped at low speed, then the
        wheel power at the *current rpm* / velocity, minus drag. The current gear sets the
        rpm, so being in the wrong gear costs power -- and bouncing off the rev limiter
        (rpm >= redline) makes NO power until you upshift, so gearing genuinely matters."""
        gear = int(clamp(state.get("gear", 1), 1, len(car.gears)))
        rpm = state["v"] / car.tire_circ * car.gears[gear - 1] * car.final_drive * 60
        whp_now = 0.0 if rpm >= car.redline else whp_at(curve, max(rpm, car.idle)) * whp_scale
        force = min(weight * 9.81 * grip * grip_scale, whp_now * 745.7 / max(state["v"], 2))
        drag = 0.5 * 1.2 * 0.62 * state["v"] * state["v"]
        state["v"] = max(0, state["v"] + ((force - drag) / weight) * dt)
        state["d"] += state["v"] * dt

    def _auto_shift(self, state, car):
        gear = int(clamp(state.get("gear", 1), 1, len(car.gears)))
        if gear >= len(car.gears):
            return
        rpm = state["v"] / car.tire_circ * car.gears[gear - 1] * car.final_drive * 60
        if rpm >= car.redline * 0.97:
            state["gear"] = gear + 1

    def _resolve_race(self, player, rival, foe):
        game = self.game
        won = player["et"] < rival["et"]
        video_playing = False
        if won:
            game.bro.earn(foe.purse)
            game.bro.add_cred(round(foe.purse / 5))
            # first_win / ladder trophies are polled off bro.unlocked_rival; king needs a
            # flag (unlocked_rival caps below the count, so beating the LAST rival is its own
            # signal). We still own the ladder-progression bookkeeping here.
            if game.bro.selected_rival == game.bro.unlocked_rival and game.bro.unlocked_rival < len(game.rivals) - 1:
                game.bro.unlocked_rival += 1
            if game.bro.selected_rival == len(game.rivals) - 1:
                game.bro.beat_king = True
            game.dave("win")
            game.soothe_bro(ED_HEAL_ON_WIN)  # a win settles the nerves
            video_playing = self._play_result_video(foe.video_win)
        else:
            game.dave("lose")
            game.hurt_bro(ED_LOSS)
            video_playing = self._play_result_video(foe.video_loss)
        game.log(("WIN" if won else "LOSS") + f" {player['et']:.2f}s @ {round(player['trap'])} mph", "ok" if won else "warn")
        game.maybe_green()
        self.race["active"] = False
        self.allow_back = not video_playing
        game.set_advisors_visible(not video_playing)  # race over -- bring the advisor pills back unless a clip owns the screen
        self.dirty = True

    def _play_result_video(self, clips: list[str]) -> bool:
        if not clips:
            return False
        clip = random.choice(clips)
        path = assets.video_path(clip)
        texture_name = "race-result-" + clip.replace("/", "-").replace("\\", "-")
        tex = MovieTexture(texture_name)
        try:
            loaded = tex.read(path)
        except Exception as exc:  # noqa: BLE001
            self.game.log(f"could not play race video {clip}: {exc}", "warn")
            return False
        if not loaded:
            self.game.log(f"could not play race video {clip}", "warn")
            return False
        audio = self._load_result_video_audio(path, clip)

        self._clear_result_video(restore_controls=False)
        card = CardMaker("race-result-video")
        card.setFrameFullscreenQuad()
        card.setUvRange(tex)
        node = self.app.render2d.attachNewNode(card.generate())
        node.setTexture(tex)
        node.setBin(OVERLAY_BIN, OVERLAY_SORT["toast"] - 1)
        tex.play()
        audio_delay = RESULT_VIDEO_AUDIO_DELAY_SECONDS if audio is not None else 0.0
        self.result_video = {
            "node": node,
            "texture": tex,
            "audio": audio,
            "audio_delay": audio_delay,
            "audio_started": audio is None,
            "life": self._result_video_duration(tex, audio) + audio_delay,
        }
        self._pause_music_for_video()
        self.allow_back = False
        self._sync_back()
        self.game.set_advisors_visible(False)
        return True

    def _update_result_video(self, dt):
        if self.result_video is None:
            return
        if not self.result_video["audio_started"]:
            self.result_video["audio_delay"] -= dt
            if self.result_video["audio_delay"] <= 0:
                self._start_result_video_audio()
        self.result_video["life"] -= dt
        if self.result_video["life"] <= 0:
            self._clear_result_video(restore_controls=True)
            self.dirty = True

    def _start_result_video_audio(self):
        if self.result_video is None:
            return
        audio = self.result_video["audio"]
        if audio is not None:
            audio.play()
        self.result_video["audio_started"] = True

    def _clear_result_video(self, restore_controls: bool):
        if self.result_video is None:
            return
        texture = self.result_video["texture"]
        if texture is not None and hasattr(texture, "stop"):
            texture.stop()
        audio = self.result_video.get("audio")
        if audio is not None:
            audio.stop()
        self.result_video["node"].removeNode()
        self.result_video = None
        self._resume_music_after_video()
        if restore_controls:
            self.allow_back = True
            self._sync_back()
            self.game.set_advisors_visible(True)

    def _load_result_video_audio(self, path: str, clip: str):
        try:
            audio = self.app.loader.loadSfx(path)
        except Exception as exc:  # noqa: BLE001
            self.game.log(f"could not load race video audio {clip}: {exc}", "warn")
            return None
        if audio is None:
            self.game.log(f"could not load race video audio {clip}", "warn")
            return None
        try:
            length = float(audio.length())
        except Exception:  # noqa: BLE001
            length = 0.0
        if length <= 0:
            self.game.log(f"race video audio has no playable length {clip}", "warn")
            return None
        audio.setLoop(False)
        audio.setVolume(1.0)
        return audio

    def _pause_music_for_video(self):
        music = getattr(self.app, "music", None)
        if music is None:
            return
        music.pause()
        self.music_paused_for_video = True

    def _resume_music_after_video(self):
        if not self.music_paused_for_video:
            return
        music = getattr(self.app, "music", None)
        if music is not None:
            music.resume()
        self.music_paused_for_video = False

    @staticmethod
    def _result_video_duration(texture, audio) -> float:
        if audio is not None:
            try:
                value = float(audio.length())
            except Exception:  # noqa: BLE001
                value = 0.0
            if value > 0:
                return value
        for name in ("getVideoLength", "getDuration", "length"):
            method = getattr(texture, name, None)
            if callable(method):
                try:
                    value = float(method())
                except Exception:  # noqa: BLE001
                    continue
                if value > 0:
                    return value
        return RESULT_VIDEO_FALLBACK_SECONDS
