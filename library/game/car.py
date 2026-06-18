from __future__ import annotations

from library.core.constants import MODS, PRESETS, UNLOCKABLE_MAPS
from library.game.tuning import clone_tune, compute_tune, default_tune, grade_for_result, pop_score


class Car:
    """The player's build: ECU state, the calibration, map slots, mods, last dyno.

    State-change methods return ``(message, kind)`` so the session (Game) can log
    them; Car itself does no logging. Built to serialize for save games.
    """

    def __init__(self, name: str = "MK7 GTI"):
        self.name = name
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
        self.mods = {mod[0]: False for mod in MODS}
        self.dyno_result = None
        self.grade = ""

    # -- queries -----------------------------------------------------------
    def ecu_status(self) -> str:
        return "FLASHED" if self.flashed else "UNLOCKED" if self.patched else "LOCKED"

    def active_tune(self) -> dict:
        return self.slots[self.active_slot] or self.flashed_tune or self.tune

    def active_pop(self) -> float:
        return pop_score(self.active_tune())

    def compute(self) -> dict:
        return compute_tune(self.flashed_tune or self.tune, self.mods)

    def car_perf(self) -> dict:
        result = self.compute()
        return {"whp": result["whp"], "weight": 1400 * (0.965 if self.mods["wheels"] else 1), "grip": 0.92 + (0.18 if self.mods["clutch"] else 0), "blown": result["blown"], "rel": result["rel"]}

    # -- ECU / tune --------------------------------------------------------
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
        return ("switch patch " + ("ENABLED" if self.switch_patch else "disabled"), "ok" if self.switch_patch else "dim")

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
        return ("FLASH OK - new map written to the ECU.", "ok")

    def apply_preset(self, key: str):
        table = PRESETS if key in PRESETS else UNLOCKABLE_MAPS
        self.tune = clone_tune(table[key])
        self.dirty = self.flashed
        return (f"preset loaded: {self.tune['name']}", "info")

    def assign_slot(self):
        if not self.flashed:
            return None
        self.slots[self.active_slot] = clone_tune(self.tune)
        self.slots[self.active_slot]["name"] = "Your Tune"
        return (f"assigned tune to slot {self.active_slot + 1}", "info")

    def select_slot(self, index: int):
        if index < len(self.slots) and self.slots[index]:
            self.active_slot = index

    def set_mod(self, mod_id: str):
        self.mods[mod_id] = True
        name = next(item[1] for item in MODS if item[0] == mod_id)
        return (f"installed {name}", "ok")

    def record_dyno(self, result: dict):
        self.dyno_result = result
        self.grade = grade_for_result(result)
        return ("dyno pull complete: " + self.grade, "ok")

    # -- save --------------------------------------------------------------
    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("name", "connected", "read", "patched", "flashed", "switch_patch", "dirty", "tune", "flashed_tune", "slots", "active_slot", "mods")}

    def from_dict(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)
