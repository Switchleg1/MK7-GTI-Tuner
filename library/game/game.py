from __future__ import annotations

import random

from library.core.constants import (
    ACHIEVEMENTS, DAVE_LINES, DISCORD_GREEN_BRUSHOFF, ED_DISCORD_BAD, ED_DISCORD_GOOD_HEAL,
    ED_TAUNT_THRESHOLD, ED_TAUNTS, GOD_PAYOUT, GREEN_NAME_CRED, MAX_LOG_LINES,
    SAVE_VERSION, WIZARD_CRED, TRIAL_ACHIEVEMENT,
)
from library.core.utils import pick
from library.game.car import Car
from library.game.car_library import CarLibrary
from library.game.discord import Discord
from library.game.pro_tuner import ProTuner
from library.game.rival_green_name import RivalGreenName
from library.game.tuner_bro import TunerBro


class Game:
    """Root of the save-ready model tree: a TunerBro, and a CarLibrary, plus transient 
    session state (logs, advisors, unlock queues). Task-specific actions live in their
    tasks; shared career state and cross-stage helpers stay here. Display reads go
    straight to ``game.bro`` / ``game.car``."""
    
    # How each Discord outcome effect lands on the bro/car -- table-dispatched
    # instead of an if/elif staircase. An unknown/"none" effect falls through to
    # just the emotional-damage swing and the log line.
    _DISCORD_EFFECTS = {
        "cash": lambda self, o: self.bro.earn(o["amount"]),
        "cred": lambda self, o: self.bro.add_cred(o["amount"]),
        "map": lambda self, o: self._grant_community_map(o["map_key"]),
        "part": lambda self, o: self.bro.pay_repair(o["amount"]),
        "clients": lambda self, o: self.bro.add_cred(-o["amount"]),
    }

    def __init__(self):
        self.pros = ProTuner.roster()  # static reference data (never reset)
        # The advisor UI panels live here (built once by the app on first hub entry,
        # kept for the session -- NOT reset by new_game). The Discord *model* is
        # ``self.discord``; the on-screen panels are ``*_panel``. ``advisors_visible``
        # lets a task hide the pills (e.g. the race hides them while it's live).
        self.simon_panel = None
        self.discord_panel = None
        # Game-level chrome buttons (Ask Simon / Ask Discord / Back), a UIObjectController
        # built by the app on first hub entry. The Ask buttons open the panels above;
        # the Back button is pointed at the active task's on_back by TaskBase.
        self.ui = None
        self.advisors_visible = True
        self.new_game()

    def new_game(self):
        """(Re)initialise a fresh career in place. Mutating the existing Game (rather
        than building a new one) keeps the shared panels' ``game`` references valid."""
        self.bro                            = TunerBro()
        self.rivals                         = RivalGreenName.ladder()
        self.cars                           = CarLibrary()
        self.discord                        = Discord()
        self.logs: list[tuple[str, str]]    = []
        self.simon_tick                     = 0  # rotates Simon through his ranked insights
        self.achievements: set[str]         = set()  # unlocked ids
        self.toast_queue: list[str]         = []     # achievement labels awaiting a toast
        self.dave_queue: list[str]          = []       # Dyno Dave quips awaiting display
        self._wizard_announced              = False    # transient: the Wizard DM flavour fired this session

    @property
    def car(self) -> Car:
        return self.cars.active()

    # -- advisor panels (Ask Simon / Ask Discord) --------------------------
    def set_advisors_visible(self, visible: bool):
        """Show or hide the Ask-Simon + Ask-Discord buttons (closing any open panel when
        hiding). A task calls this to clear them off-screen -- e.g. the race hides them
        while it's live and restores them when it concludes. No-op before the chrome
        buttons / panels are built (first hub entry)."""
        self.advisors_visible = visible
        if self.ui is not None:
            for key in ("ask_simon", "ask_discord"):
                button = self.ui.get(key)
                if button is not None:
                    button.is_visible(visible)
        if not visible:
            for panel in (self.simon_panel, self.discord_panel):
                if panel is not None:
                    panel.close()

    def log(self, message: str, kind: str = "dim"):
        self.logs.append((message, kind))
        self.logs = self.logs[-MAX_LOG_LINES:]

    # -- achievements (table-driven; drained by the Notifications overlay) ---
    def check_unlocks(self):
        """Poll the ACHIEVEMENTS table (called ~4x/sec at the game level): unlock every
        still-locked achievement whose check now reads true. Achievements are stat-driven,
        so gameplay code only has to keep the stats current -- no scattered unlock() calls.
        An empty check is skipped (those are unlocked explicitly, e.g. the Wizard endings)."""
        for key, ach in ACHIEVEMENTS.items():
            if not ach.check or key in self.achievements:
                continue
            for path, required in ach.check:
                value = self._resolve(path)
                try:
                    hit = value is not None and value >= required
                except TypeError:
                    hit = False
                if hit:
                    self.unlock(key)
                    break

    def _resolve(self, path: str):
        """Resolve a dotted stat path against the game -- 'bro.total_pops' -> self.bro.
        total_pops, 'car.flashed' -> self.car.flashed, 'wizard_ready' -> self.wizard_ready."""
        obj = self
        for part in path.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return None
        return obj

    def unlock(self, key: str) -> bool:
        """Mark an achievement earned (idempotent): toast its label + pay its cred, both
        from the ACHIEVEMENTS table. Returns True only the first time. Used by
        check_unlocks() for polled trophies and called directly for the manual ones."""
        if key in self.achievements or key not in ACHIEVEMENTS:
            return False
        ach = ACHIEVEMENTS[key]
        self.achievements.add(key)
        self.toast_queue.append(ach.label)
        self.bro.add_cred(ach.cred)  # achievements feed cred (= the arcade score)
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

    def _grant_community_map(self, key: str):
        self.bro.unlock_map(key)  # the "community_map" trophy is polled off bro.community_maps

    def _apply_discord(self, outcome: dict):
        handler = self._DISCORD_EFFECTS.get(outcome["effect"])
        if handler:
            handler(self, outcome)
        if outcome["kind"] == "good":
            self.soothe_bro(ED_DISCORD_GOOD_HEAL)
        else:
            self.hurt_bro(ED_DISCORD_BAD)
        self.log(outcome["summary"], "ok" if outcome["kind"] == "good" else "warn")

    # -- green name (verified pro path) ------------------------------------
    def maybe_green(self):
        """Promote to verified green name once cred crosses the bar (once). The
        "green_name" trophy itself is polled off ``bro.green_name``; this just flips the
        gameplay flag + flavour."""
        if not self.bro.green_name and self.bro.cred >= GREEN_NAME_CRED:
            self.bro.green_name = True
            self.dave("green")
            self.log("VERIFIED: you got the green name. the noobs DM you now.", "ok")
        self.maybe_wizard()

    def wizard_available(self) -> bool:
        """The Bench Wizard only DMs an established green name (until you pass)."""
        return self.bro.green_name and self.bro.cred >= WIZARD_CRED and not self.bro.god

    @property
    def wizard_ready(self) -> bool:
        """Pollable alias for the ACHIEVEMENTS table ('wizard_ready' -> wizard_summon)."""
        return self.wizard_available()

    def maybe_wizard(self):
        # The "wizard_summon" trophy is polled off wizard_ready; this just drops the
        # flavour DM once (transient guard, so it doesn't re-log every cred tick).
        if self.wizard_available() and not self._wizard_announced:
            self._wizard_announced = True
            self.log("a hooded tuner DMs you a three-part Trial. prove yourself.", "violet")
            self.dave("wizard")

    def grant_god(self, achievement: str = TRIAL_ACHIEVEMENT):
        """A Wizard challenge passed -- bench an ECU (the Trial) OR build a dongle: god
        status + a giant one-time payout. ``achievement`` is the trophy KEY for the path
        taken (its cred reward comes from the table); the reward is identical, name differs."""
        if self.bro.god:
            return
        self.bro.god = True
        self.bro.earn(GOD_PAYOUT)
        self.unlock(achievement)  # the trophy's table cred (GOD_UNLOCK_CRED) is the big arcade payout
        self.dave("god")
        self.log(f"WIZARD CHALLENGE PASSED. god status granted. +${GOD_PAYOUT:,}.", "ok")

    # -- save --------------------------------------------------------------
    def to_dict(self) -> dict:
        """A full career snapshot: the bro, the car library (build + mods), the rival
        ladder, the discord presence, and the career counters/achievements. Restored
        in place by ``from_dict`` so live panel references stay valid."""
        return {
            "version": SAVE_VERSION,
            "bro": self.bro.to_dict(),
            "cars": self.cars.to_dict(),
            "discord": self.discord.to_dict(),
            "achievements": sorted(self.achievements),
            "simon_tick": self.simon_tick,
        }

    def from_dict(self, data: dict):
        self.bro.from_dict(data.get("bro", {}))
        self.cars.from_dict(data.get("cars", {}))
        self.discord.from_dict(data.get("discord", {}))
        self.achievements = set(data.get("achievements", []))
        self.simon_tick = data.get("simon_tick", 0)
