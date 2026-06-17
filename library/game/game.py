from __future__ import annotations

import time

from library.core.constants import MAX_LOG_LINES, MODS, TRACK_M
from library.game.car import Car
from library.game.car_library import CarLibrary
from library.game.rival_green_name import RivalGreenName
from library.game.tuner_bro import TunerBro


class Game:
    """Root of the save-ready model tree: a TunerBro, the RivalGreenName ladder, and
    a CarLibrary, plus transient session state (logs, the active race). Cross-node
    actions (buying, pops, racing) are orchestrated here; per-node logic lives on the
    nodes. Display reads go straight to ``game.bro`` / ``game.car``."""

    def __init__(self):
        self.bro = TunerBro()
        self.rivals = RivalGreenName.ladder()
        self.cars = CarLibrary()
        self.logs: list[tuple[str, str]] = []
        self.race = None
        self.simon_tick = 0  # rotates Simon through his ranked insights

    @property
    def car(self) -> Car:
        return self.cars.active()

    def log(self, message: str, kind: str = "dim"):
        self.logs.append((message, kind))
        self.logs = self.logs[-MAX_LOG_LINES:]

    def _log_result(self, result):
        if result:
            self.log(*result)

    # -- car action facades (Car does the work, Game logs it) --------------
    def toggle_switch(self):
        self._log_result(self.car.toggle_switch())

    def flash_ecu(self):
        self._log_result(self.car.flash_ecu())

    def apply_preset(self, key: str):
        self._log_result(self.car.apply_preset(key))

    def assign_slot(self):
        self._log_result(self.car.assign_slot())

    def select_slot(self, index: int):
        self.car.select_slot(index)

    def buy_mod(self, mod_id: str):
        cost = next(item[2] for item in MODS if item[0] == mod_id)
        if self.car.mods[mod_id] or not self.bro.spend(cost):
            return
        self._log_result(self.car.set_mod(mod_id))

    # -- street ------------------------------------------------------------
    def register_pops(self) -> int:
        """Apply cred/Karen from a pops blip; return a flame count for the scene."""
        pop = self.car.active_pop()
        self.bro.add_cred(pop / 18)
        self.bro.add_heat(pop / 18)
        return max(4, round(pop / 10))

    # -- race --------------------------------------------------------------
    def race_active(self) -> bool:
        return bool(self.race and self.race["active"])

    def select_rival(self, index: int):
        if index <= self.bro.unlocked_rival:
            self.bro.selected_rival = index

    def start_race(self) -> str | None:
        if not self.car.flashed or self.race_active():
            return None
        if self.car.car_perf()["blown"]:
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
        foe = self.rivals[self.bro.selected_rival]
        if player["launched"] and not player["done"]:
            perf = self.car.car_perf()
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
        won = player["et"] < rival["et"]
        if won:
            self.bro.earn(foe.purse)
            self.bro.add_cred(round(foe.purse / 5))
            if self.bro.selected_rival == self.bro.unlocked_rival and self.bro.unlocked_rival < len(self.rivals) - 1:
                self.bro.unlocked_rival += 1
        self.log(("WIN" if won else "LOSS") + f" {player['et']:.2f}s @ {round(player['trap'])} mph", "ok" if won else "warn")
        self.race["active"] = False

    def race_result_text(self) -> str:
        if not self.race:
            return "Launch on green. Shift with Space."
        if self.race_active():
            return f"You {self.race['p']['d']:.0f}m / Rival {self.race['r']['d']:.0f}m"
        return "Race complete. Check the log."

    # -- save --------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"bro": self.bro.to_dict(), "cars": self.cars.to_dict()}

    def from_dict(self, data: dict):
        self.bro.from_dict(data.get("bro", {}))
        self.cars.from_dict(data.get("cars", {}))
