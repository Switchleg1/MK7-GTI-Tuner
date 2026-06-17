from __future__ import annotations

import time

from library.core.constants import MAX_LOG_LINES, MODS, PRESETS, RIVALS, TRACK_M
from library.core.utils import clamp
from library.game.tuning import clone_tune, compute_tune, default_tune, dyno_curve, grade_for_result, pop_score

DYNO_PULL_SECONDS = 2.2


class GameState:
    """All career state + pure game logic. No scene/render code lives here; tasks
    own the 3D scene and per-frame animation and read/write this model."""

    def __init__(self):
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
        self.logs = []
        self.simon_tick = 0
        self.dyno_result = None
        self.dyno_points = dyno_curve(210)
        self.dyno_running = False
        self.dyno_started = 0.0
        self.grade = ""
        self.selected_rival = 0
        self.unlocked_rival = 0
        self.race = None

    # -- bench / maps ------------------------------------------------------
    def log(self, message: str, kind: str = "dim"):
        self.logs.append((message, kind))
        self.logs = self.logs[-MAX_LOG_LINES:]

    def ecu_status(self) -> str:
        return "FLASHED" if self.flashed else "UNLOCKED" if self.patched else "LOCKED"

    def active_tune(self) -> dict:
        return self.slots[self.active_slot] or self.flashed_tune or self.tune

    def active_pop(self) -> float:
        return pop_score(self.active_tune())

    def mark_unlocked(self):
        """The cinematic unlock connected, read, patched and flashed the ECU."""
        self.connected = self.read = self.patched = self.flashed = True
        self.dirty = False
        self.flashed_tune = clone_tune(self.tune)
        self.slots = [clone_tune(self.tune), None, None, None]
        self.slots[0]["name"] = "Your Tune"
        self.active_slot = 0

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
        self.log("FLASH OK - new map written to the ECU.", "ok")

    def apply_preset(self, key: str):
        self.tune = clone_tune(PRESETS[key])
        self.dirty = self.flashed
        self.log(f"preset loaded: {self.tune['name']}", "info")

    def assign_slot(self):
        if self.flashed:
            self.slots[self.active_slot] = clone_tune(self.tune)
            self.slots[self.active_slot]["name"] = "Your Tune"
            self.log(f"assigned tune to slot {self.active_slot + 1}", "info")

    def select_slot(self, index: int):
        if index < len(self.slots) and self.slots[index]:
            self.active_slot = index

    # -- shop --------------------------------------------------------------
    def buy_mod(self, mod_id: str):
        mod = next(item for item in MODS if item[0] == mod_id)
        if self.mods[mod_id] or self.cash < mod[2]:
            return
        self.cash -= mod[2]
        self.mods[mod_id] = True
        self.log(f"installed {mod[1]}", "ok")

    def car_perf(self) -> dict:
        result = compute_tune(self.flashed_tune or self.tune, self.mods)
        return {"whp": result["whp"], "weight": 1400 * (0.965 if self.mods["wheels"] else 1), "grip": 0.92 + (0.18 if self.mods["clutch"] else 0), "blown": result["blown"], "rel": result["rel"]}

    # -- dyno --------------------------------------------------------------
    def dyno_preview(self) -> dict:
        return self.dyno_result or compute_tune(self.flashed_tune or self.tune, self.mods)

    def run_dyno(self):
        if self.dyno_running:
            return
        self.dyno_result = compute_tune(self.flashed_tune or self.tune, self.mods)
        self.dyno_points = dyno_curve(self.dyno_result["whp"])
        self.dyno_running = True
        self.dyno_started = time.perf_counter()
        self.log("dyno pull started", "info")

    def dyno_done(self) -> bool:
        return self.dyno_running and time.perf_counter() - self.dyno_started > DYNO_PULL_SECONDS

    def finish_dyno(self):
        self.dyno_running = False
        self.grade = grade_for_result(self.dyno_result)
        self.log("dyno pull complete: " + self.grade, "ok")

    # -- street ------------------------------------------------------------
    def register_pops(self) -> int:
        """Apply cred/Karen from a pops blip; returns a flame count for the scene."""
        pop = self.active_pop()
        self.cred += pop / 18
        self.karen = clamp(self.karen + pop / 18, 0, 100)
        return max(4, round(pop / 10))

    # -- race --------------------------------------------------------------
    def race_active(self) -> bool:
        return bool(self.race and self.race["active"])

    def select_rival(self, index: int):
        if index <= self.unlocked_rival:
            self.selected_rival = index

    def start_race(self) -> str | None:
        if not self.flashed or self.race_active():
            return None
        if self.car_perf()["blown"]:
            self.log("Your tune is a grenade. Fix it on dyno first.", "err")
            return "blown"
        now = time.perf_counter()
        self.race = {"active": True, "green_at": now + 1.9, "rival_launch": now + 2.15,
                     "p": {"d": 0.0, "v": 0.0, "gear": 1, "launched": False, "done": False, "et": 0.0, "trap": 0.0},
                     "r": {"d": 0.0, "v": 0.0, "done": False, "et": 0.0, "trap": 0.0}}
        self.log("staged - launch on green", "info")
        return "staged"

    def race_key(self) -> str | None:
        if not self.race_active():
            return None
        player = self.race["p"]
        if not player["launched"]:
            player["launched"] = True
            self.log("launched" if time.perf_counter() >= self.race["green_at"] else "red light", "ok")
            return "launch"
        if player["gear"] < 6:
            player["gear"] += 1
            return "shift"
        return None

    def step_race(self, dt: float):
        if time.perf_counter() < self.race["green_at"]:
            return
        player, rival = self.race["p"], self.race["r"]
        rival_info = RIVALS[self.selected_rival]
        if player["launched"] and not player["done"]:
            perf = self.car_perf()
            self._step_car(player, perf["whp"], perf["weight"], perf["grip"], dt)
            if player["d"] >= TRACK_M:
                player["done"], player["et"], player["trap"] = True, time.perf_counter() - self.race["green_at"], player["v"] * 2.237
        if time.perf_counter() >= self.race["rival_launch"] and not rival["done"]:
            self._step_car(rival, rival_info["whp"], rival_info["weight"], rival_info["grip"], dt)
            if rival["d"] >= TRACK_M:
                rival["done"], rival["et"], rival["trap"] = True, time.perf_counter() - self.race["green_at"], rival["v"] * 2.237
        if player["done"] and rival["done"]:
            self._resolve_race(player, rival, rival_info)

    def _step_car(self, car, whp, weight, grip, dt):
        force = min(weight * 9.81 * grip, whp * 745.7 / max(car["v"], 2))
        drag = 0.5 * 1.2 * 0.62 * car["v"] * car["v"]
        car["v"] = max(0, car["v"] + ((force - drag) / weight) * dt)
        car["d"] += car["v"] * dt

    def _resolve_race(self, player, rival, rival_info):
        won = player["et"] < rival["et"]
        if won:
            self.cash += rival_info["purse"]
            self.cred += round(rival_info["purse"] / 5)
            if self.selected_rival == self.unlocked_rival and self.unlocked_rival < len(RIVALS) - 1:
                self.unlocked_rival += 1
        self.log(("WIN" if won else "LOSS") + f" {player['et']:.2f}s @ {round(player['trap'])} mph", "ok" if won else "warn")
        self.race["active"] = False

    def race_result_text(self) -> str:
        if not self.race:
            return "Launch on green. Shift with Space."
        if self.race_active():
            return f"You {self.race['p']['d']:.0f}m / Rival {self.race['r']['d']:.0f}m"
        return "Race complete. Check the log."
