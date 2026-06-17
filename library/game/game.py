from __future__ import annotations

import random
import time

from library.core.constants import MAX_LOG_LINES, MODS, TRACK_M
from library.core.utils import pick
from library.game.car import Car
from library.game.car_library import CarLibrary
from library.game.discord import Discord
from library.game.rival_green_name import RivalGreenName
from library.game.tuner_bro import TunerBro

# Dyno Dave's reactive one-liners, by event pool.
DAVE_LINES = {
    "flash": ["Aight, she's flashed. Try not to grenade it.", "New map's in - let's make some noise.", "Flashed clean. Go cause problems."],
    "mapswitch": ["Stalk magic. Civilized.", "Map swap on the fly, you animal.", "Cops around? Slap it to valet."],
    "bigbang": ["That one set off car alarms. Beautiful.", "Somewhere a Prius is crying.", "I felt that in my fillings.", "Cats? We don't do cats here."],
    "cops": ["The whole street knows your plate now. Worth it.", "Noise complaint AND legend status. Balanced."],
    "dyno": ["Numbers don't lie. The dyno might, but not today.", "That'll do. Send it again.", "Decent pull - chase a little more."],
    "sgrade": ["S-grade?! Tuner of the year, baby.", "Now THAT is a tune. Frame it."],
    "blown": ["...we don't talk about that one.", "That's a rebuild. GoFundMe time.", "Money shift. Classic. Painful."],
    "win": ["GET THAT MONEY. Easy work.", "He never stood a chance.", "Cash money - go buy a turbo."],
    "lose": ["Oof. Hit the shop and run it back.", "He spanked you. Tune up.", "Slower car, faster wallet... oh wait."],
    "shop": ["Bolted on - she's meaner now.", "Good buy. Now go use it.", "Money well spent, for once."],
}


class Game:
    """Root of the save-ready model tree: a TunerBro, the RivalGreenName ladder, and
    a CarLibrary, plus transient session state (logs, the active race). Cross-node
    actions (buying, pops, racing) are orchestrated here; per-node logic lives on the
    nodes. Display reads go straight to ``game.bro`` / ``game.car``."""

    def __init__(self):
        self.bro = TunerBro()
        self.rivals = RivalGreenName.ladder()
        self.cars = CarLibrary()
        self.discord = Discord()
        self.logs: list[tuple[str, str]] = []
        self.race = None
        self.simon_tick = 0  # rotates Simon through his ranked insights
        self.achievements: set[str] = set()  # unlocked ids
        self.toast_queue: list[str] = []     # achievement labels awaiting a toast
        self.dave_queue: list[str] = []       # Dyno Dave quips awaiting display
        self.total_pops = 0
        self.map_switches = 0

    @property
    def car(self) -> Car:
        return self.cars.active()

    def log(self, message: str, kind: str = "dim"):
        self.logs.append((message, kind))
        self.logs = self.logs[-MAX_LOG_LINES:]

    def _log_result(self, result):
        if result:
            self.log(*result)

    # -- achievements + Dave (drained by the Notifications overlay) ---------
    def unlock(self, key: str, label: str) -> bool:
        if key in self.achievements:
            return False
        self.achievements.add(key)
        self.toast_queue.append(label)
        return True

    def dave(self, pool: str):
        self.dave_queue.append(pick(DAVE_LINES[pool]))

    def finish_dyno(self, result: dict):
        """Record the pull, log the grade, and fire grade-based achievements/quips."""
        self._log_result(self.car.record_dyno(result))
        if result["blown"]:
            self.unlock("money_shift", "Money Shift")
            self.dave("blown")
        elif self.car.grade.startswith("Grade S"):
            self.unlock("tuner_of_year", "Tuner of the Year")
            self.dave("sgrade")
        else:
            self.dave("dyno")
        if result["pop"] > 90:
            self.unlock("cat_delete", "Cat Delete Speedrun")

    # -- car action facades (Car does the work, Game logs it) --------------
    def toggle_switch(self):
        self._log_result(self.car.toggle_switch())

    def flash_ecu(self):
        self._log_result(self.car.flash_ecu())
        self.unlock("first_flash", "Boot Patched, Baby")
        if self.car.tune["fuel"] == "E30" and self.car.tune["boost"] >= 24:
            self.unlock("e30_lifestyle", "It's Not Stage 2, It's a Lifestyle")
        self.dave("flash")

    def apply_preset(self, key: str):
        self._log_result(self.car.apply_preset(key))

    def assign_slot(self):
        self._log_result(self.car.assign_slot())

    def select_slot(self, index: int):
        self.car.select_slot(index)
        if 0 <= index < len(self.car.slots) and self.car.slots[index]:
            self.map_switches += 1
            if self.map_switches >= 10:
                self.unlock("stalk_wizard", "Stalk Wizard")
            if random.random() < 0.4:
                self.dave("mapswitch")

    def buy_mod(self, mod_id: str):
        cost = next(item[2] for item in MODS if item[0] == mod_id)
        if self.car.mods[mod_id] or not self.bro.spend(cost):
            return
        self._log_result(self.car.set_mod(mod_id))
        if all(self.car.mods.values()):
            self.unlock("fully_built", "Fully Built (Wallet Empty)")
        self.dave("shop")

    # -- street ------------------------------------------------------------
    def register_pops(self) -> int:
        """Apply cred/Karen from a pops blip; return a flame count for the scene."""
        pop = self.car.active_pop()
        self.bro.add_cred(pop / 18)
        self.bro.add_heat(pop / 18)
        self.total_pops += 1
        if self.total_pops >= 50:
            self.unlock("burble_brain", "Burble Brain")
        if pop > 90:
            self.unlock("cat_delete", "Cat Delete Speedrun")
        if self.bro.karen >= 100 and self.unlock("menace", "Neighborhood Menace"):
            self.log("the neighbors filed a noise complaint - you're a legend now", "warn")
            self.dave("cops")
        elif random.random() < 0.18:
            self.dave("bigbang")
        return max(4, round(pop / 10))

    # -- discord -----------------------------------------------------------
    def ask_discord(self, text: str) -> dict:
        """Submit a #help request: the Discord resolves it (text + who's online +
        chance), then we apply the outcome to the bro/car and log it. Returns the
        outcome so the panel can show the replies."""
        ctx = {"cred": self.bro.cred, "unlocked_maps": list(self.bro.unlocked_maps)}
        outcome = self.discord.resolve(text, ctx)
        self._apply_discord(outcome)
        return outcome

    def _apply_discord(self, outcome: dict):
        effect, amount = outcome["effect"], outcome["amount"]
        if effect == "cash":
            self.bro.earn(amount)
        elif effect == "cred":
            self.bro.add_cred(amount)
        elif effect == "map":
            self.bro.unlock_map(outcome["map_key"])
            self.unlock("community_map", "Community Map Plug")
        elif effect == "part":
            self.bro.pay_repair(amount)
        elif effect == "clients":
            self.bro.add_cred(-amount)
        self.log(outcome["summary"], "ok" if outcome["kind"] == "good" else "warn")

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
            self.unlock("first_win", "Won Some Cash")
            if self.bro.selected_rival == self.bro.unlocked_rival and self.bro.unlocked_rival < len(self.rivals) - 1:
                self.bro.unlocked_rival += 1
                self.unlock("ladder", "Climbing the Ladder")
            if self.bro.selected_rival == len(self.rivals) - 1:
                self.unlock("king", "King of the Streets")
            self.dave("win")
        else:
            self.dave("lose")
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
