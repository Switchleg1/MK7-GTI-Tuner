from __future__ import annotations

import random
import time

from library.core.constants import (
    BUST_FINE, DISCORD_GREEN_BRUSHOFF, ED_BAD_REVIEW, ED_BLOWN, ED_BUST, ED_DISCORD_BAD,
    ED_DISCORD_GOOD_HEAL, ED_TAUNT_THRESHOLD, GOD_PAYOUT, GREEN_NAME_CRED, KAREN_AFTER_BUST,
    KAREN_COOLDOWN_PER_SEC, MAX_LOG_LINES, MODS, PRO_MAPS, SALE_BAD, SAVE_VERSION, TRACK_M,
    TUNE_SALE, WIZARD_CRED,
)
from library.core.utils import pick
from library.game.car import Car
from library.game.car_library import CarLibrary
from library.game.discord import Discord
from library.game.pro_tuner import ProTuner
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
    "green": ["You went GREEN, baby. Verified and everything.", "Green name. Now the noobs DM you.", "You're official. Don't let it go to your head."],
    "sell": ["Sold a tune to some poor soul. Cha-ching.", "Another satisfied (?) customer.", "You're a tune mill now."],
    "pro": ["Talking to the pros now, huh.", "Networking. Gross. Profitable.", "Big leagues."],
    "wizard": ["The Wizard wants a word. Don't keep him waiting.", "A secret tuner trial just dropped. Go.", "Some hooded guy DM'd you. Spooky. Click it."],
    "god": ["GOD STATUS. Nobody can tell you anything now.", "You passed the Trial. Unreal.", "Infinite-ish money. Go nuts."],
}

# When emotional damage is high, the crew piles on (logged as a chat-style ping).
ED_TAUNTS = [
    "tacos: ratio. + post a log. + cope.",
    "cp4334: bent another one? rods are merely suggestions.",
    "Simon: this is why we tell you to post a log.",
    "tacos: skill issue (affectionate)",
    "Mike: more boost would've fixed that. (it would not have)",
    "JC: that's a 2x4 problem. it's always a 2x4 problem.",
    "the FB group screenshotted your build. brutal.",
]


class Game:
    """Root of the save-ready model tree: a TunerBro, the RivalGreenName ladder, and
    a CarLibrary, plus transient session state (logs, the active race). Cross-node
    actions (buying, pops, racing) are orchestrated here; per-node logic lives on the
    nodes. Display reads go straight to ``game.bro`` / ``game.car``."""

    def __init__(self):
        self.pros = ProTuner.roster()  # static reference data (never reset)
        # The advisor UI panels live here (built once by the app on first hub entry,
        # kept for the session -- NOT reset by new_game). The Discord *model* is
        # ``self.discord``; the on-screen panels are ``*_panel``. ``advisors_visible``
        # lets a task hide the pills (e.g. the race hides them while it's live).
        self.simon_panel = None
        self.discord_panel = None
        self.advisors_visible = True
        self.new_game()

    def new_game(self):
        """(Re)initialise a fresh career in place. Mutating the existing Game (rather
        than building a new one) keeps the shared panels' ``game`` references valid."""
        self.bro = TunerBro()
        self.rivals = RivalGreenName.ladder()
        self.cars = CarLibrary()
        self.discord = Discord()
        self.logs: list[tuple[str, str]] = []
        self.simon_tick = 0  # rotates Simon through his ranked insights
        self.achievements: set[str] = set()  # unlocked ids
        self.toast_queue: list[str] = []     # achievement labels awaiting a toast
        self.dave_queue: list[str] = []       # Dyno Dave quips awaiting display
        self.total_pops = 0
        self.map_switches = 0

    @property
    def car(self) -> Car:
        return self.cars.active()

    # -- advisor panels (Ask Simon / Ask Discord) --------------------------
    def set_advisors_visible(self, visible: bool):
        """Show or hide the Ask-Simon + Ask-Discord pills (closing any open window when
        hiding). A task calls this to clear them off-screen -- e.g. the race hides them
        while it's live and restores them when it concludes. No-op before the panels are
        built (first hub entry)."""
        self.advisors_visible = visible
        for panel in (self.simon_panel, self.discord_panel):
            if panel is None:
                continue
            if not visible:
                panel.close()
            panel.set_visible(visible)

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

    # -- emotional damage (getting clowned hurts your race launches) --------
    def hurt_bro(self, amount: float, taunt: bool = True):
        """Pile on emotional damage. Once it's high, the crew starts piling on too."""
        self.bro.add_damage(amount)
        if taunt and self.bro.emotional_damage >= ED_TAUNT_THRESHOLD and random.random() < 0.6:
            self.log(pick(ED_TAUNTS), "err")

    def soothe_bro(self, amount: float):
        """Heal emotional damage (a win, a good outcome)."""
        self.bro.add_damage(-amount)

    def finish_dyno(self, result: dict):
        """Record the pull, log the grade, and fire grade-based achievements/quips."""
        self._log_result(self.car.record_dyno(result))
        if result["blown"]:
            self.unlock("money_shift", "Money Shift")
            self.hurt_bro(ED_BLOWN)
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
        if self.bro.karen >= 100:
            self.bust_if_maxed()  # real cop penalty (repeatable)
        elif random.random() < 0.18:
            self.dave("bigbang")
        self.maybe_green()
        return max(4, round(pop / 10))

    def cool_heat(self, dt: float):
        """Continuous Karen-meter cooldown -- called every frame from quieter tasks
        (street_task) when the throttle is down. No-op if the meter is already at 0."""
        if self.bro.karen > 0:
            self.bro.add_heat(-dt * KAREN_COOLDOWN_PER_SEC)

    def bust_if_maxed(self):
        """If the Karen meter capped, the cops roll up: fine the bro and partially
        reset the meter. Repeatable -- every cap-out is a new citation. The first
        bust also fires the Neighborhood Menace achievement."""
        if self.bro.karen < 100:
            return
        fine = int(BUST_FINE * (1 + self.bro.cred / 300.0))
        self.bro.pay_repair(fine)
        self.bro.karen = KAREN_AFTER_BUST
        self.log(f"COPS rolled up - noise complaint citation: -${fine}", "err")
        self.hurt_bro(ED_BUST)
        self.dave("cops")
        self.unlock("menace", "Neighborhood Menace")

    # -- discord -----------------------------------------------------------
    def ask_discord(self, text: str) -> dict:
        """Submit a #help request: the Discord resolves it (text + who's online +
        chance), then we apply the outcome to the bro/car and log it. Returns the
        outcome so the panel can show the replies."""
        if self.bro.green_name and random.random() < 0.7:
            return self._green_brushoff()
        ctx = {"cred": self.bro.cred, "unlocked_maps": list(self.bro.unlocked_maps)}
        outcome = self.discord.resolve(text, ctx)
        self._apply_discord(outcome)
        self.maybe_green()
        return outcome

    def _green_brushoff(self) -> dict:
        roster = self.discord.online() or self.discord.members
        who = pick(roster)
        line = pick(DISCORD_GREEN_BRUSHOFF)
        self.log("green name asked in #help: " + line, "warn")
        self.hurt_bro(ED_DISCORD_BAD * 0.5)
        return {"kind": "bad", "effect": "none", "amount": 0, "map_key": None,
                "summary": "you're green now - they expect you to know this one",
                "replies": [{"name": who.name, "color": who.color, "text": line}]}

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
        if outcome["kind"] == "good":
            self.soothe_bro(ED_DISCORD_GOOD_HEAL)
        else:
            self.hurt_bro(ED_DISCORD_BAD)
        self.log(outcome["summary"], "ok" if outcome["kind"] == "good" else "warn")

    # -- green name (verified pro path) ------------------------------------
    def maybe_green(self):
        """Promote to verified green name once cred crosses the bar (once)."""
        if not self.bro.green_name and self.bro.cred >= GREEN_NAME_CRED:
            self.bro.green_name = True
            self.unlock("green_name", "Green Name")
            self.dave("green")
            self.log("VERIFIED: you got the green name. the noobs DM you now.", "ok")
        self.maybe_wizard()

    def wizard_available(self) -> bool:
        """The Bench Wizard only DMs an established green name (until you pass)."""
        return self.bro.green_name and self.bro.cred >= WIZARD_CRED and not self.bro.god

    def maybe_wizard(self):
        if self.wizard_available() and self.unlock("wizard_summon", "A Mysterious DM"):
            self.log("a hooded tuner DMs you a three-part Trial. prove yourself.", "violet")
            self.dave("wizard")

    def grant_god(self):
        """Trial passed: god status + a giant one-time payout."""
        if self.bro.god:
            return
        self.bro.god = True
        self.bro.earn(GOD_PAYOUT)
        self.unlock("god_status", "Passed the Trial")
        self.dave("god")
        self.log(f"TRIAL PASSED. god status granted. +${GOD_PAYOUT:,}.", "ok")

    def sell_tune(self):
        """Green-name income: flog a tune to a random user. Usually pays; sometimes
        they brick it and leave a bad review (a cred hit)."""
        if not self.bro.green_name:
            return
        if random.random() < TUNE_SALE["bad_chance"]:
            self.bro.add_cred(-4)
            self.hurt_bro(ED_BAD_REVIEW)
            self.log(pick(SALE_BAD), "warn")
            return
        whp = self.car.compute()["whp"]
        pay = int(TUNE_SALE["base"] + max(0.0, whp - 210) * TUNE_SALE["per_whp"])
        self.bro.earn(pay)
        self.bro.add_cred(TUNE_SALE["cred"])
        self.bro.tunes_sold += 1
        self.unlock("first_sale", "Side Hustle")
        if self.bro.tunes_sold >= 10:
            self.unlock("tune_mill", "Tune Mill")
        self.log(f"sold a tune for ${pay}  ({self.bro.tunes_sold} sold)", "ok")
        self.dave("sell")
        self.maybe_green()

    def ask_pro(self, handle: str):
        """DM a pro for a pro-only map stage. They hand it over once you've sold
        enough tunes to be taken seriously; otherwise they tell you to earn it."""
        if not self.bro.green_name:
            return
        pro = next((p for p in self.pros if p.handle == handle), None)
        if pro is None:
            return
        if pro.grant_map in self.bro.unlocked_maps:
            self.log(f"{pro.name}: you already have {PRO_MAPS[pro.grant_map]['name']}.", "info")
        elif self.bro.tunes_sold >= pro.min_tunes:
            self.bro.unlock_map(pro.grant_map)
            self.unlock("pro_network", "Pro Network")
            self.log(f"{pro.name} hooked you up: {PRO_MAPS[pro.grant_map]['name']} unlocked.", "ok")
            self.dave("pro")
        else:
            need = pro.min_tunes - self.bro.tunes_sold
            self.log(f"{pro.name}: {pro.chatter()} (sell {need} more tune{'s' if need != 1 else ''} first)", "warn")

    # -- save --------------------------------------------------------------
    def to_dict(self) -> dict:
        """A full career snapshot: the bro, the car library (build + mods), the rival
        ladder, the discord presence, and the career counters/achievements. Restored
        in place by ``from_dict`` so live panel references stay valid."""
        return {
            "version": SAVE_VERSION,
            "bro": self.bro.to_dict(),
            "cars": self.cars.to_dict(),
            "rivals": [rival.to_dict() for rival in self.rivals],
            "discord": self.discord.to_dict(),
            "achievements": sorted(self.achievements),
            "total_pops": self.total_pops,
            "map_switches": self.map_switches,
            "simon_tick": self.simon_tick,
        }

    def from_dict(self, data: dict):
        self.bro.from_dict(data.get("bro", {}))
        self.cars.from_dict(data.get("cars", {}))
        for rival, saved in zip(self.rivals, data.get("rivals", [])):
            rival.from_dict(saved)
        self.discord.from_dict(data.get("discord", {}))
        self.achievements = set(data.get("achievements", []))
        self.total_pops = data.get("total_pops", 0)
        self.map_switches = data.get("map_switches", 0)
        self.simon_tick = data.get("simon_tick", 0)
