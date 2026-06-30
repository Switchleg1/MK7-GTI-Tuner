from __future__ import annotations

from library.core.constants import CAR_TABLE, MOD_TABLE, MODS, PRESETS, TURBOS, UNLOCKABLE_MAPS, DEFAULT_TUNE
from library.game.tuning import (
    build_whp_curve, clone_tune, compute_tune, default_tune, grade_for_result, pop_score, whp_at,
)


class Car:
    """A car -- the player's build OR a rival's. Its physics (rpm->whp curve, gearing,
    tire, mass, grip) are pulled from ``CAR_TABLE[car_id]``; mods + tune reshape the curve
    via ``build_whp``. The player also uses the ECU/tune/slot state below (inert on rival
    cars, which never flash and aren't saved).

    State-change methods return ``(message, kind)`` so the session (Game) can log them;
    Car itself does no logging. Built to serialize for save games."""

    def __init__(self, car_id: str = "mk7_gti", mods: dict | None = None, tune: dict = DEFAULT_TUNE):
        spec = CAR_TABLE[car_id]
        self.car_id                 = car_id
        self.name                   = spec["name"]
        self.model                  = spec["model"]
        # Physics spec (from the table -- not serialized; reloaded from car_id on load).
        self.base_curve             = list(spec["power_curve"])
        self.gears                  = list(spec["gears"])
        self.final_drive            = spec["final_drive"]
        self.tire_circ              = spec["tire_circ"]
        self.base_weight            = spec["weight"]
        self.base_grip              = spec["grip"]
        self.idle                   = spec["idle"]
        self.redline                = spec["redline"]
        self.spool_rpm              = spec["spool_rpm"]
        self.boost_ceiling          = spec["boost_ceiling"]
        # ECU / build state (player; defaults are inert for rivals).
        self.connected              = False
        self.read                   = False
        self.patched                = False
        self.flashed                = False
        self.switch_patch           = False
        self.dirty                  = False
        self.tune                   = clone_tune(tune) if tune is not None else default_tune()
        self.flashed_tune           = None
        self.slots                  = [clone_tune(self.tune), None, None, None]
        self.active_slot            = 0
        self.mods                   = mods if mods is not None else {mod[0]: False for mod in MODS}
        # Which turbo variant is fitted (None = stock). `mods["turbo"]` stays the bool
        # "owns an aftermarket turbo"; this picks WHICH from TURBOS. A car built with
        # `mods["turbo"]` True but no explicit variant (rivals, old saves) defaults to IS38.
        self.turbo                  = "is38" if self.mods.get("turbo") else None
        # Turbos are OWNED (bought once) and one is EQUIPPED. You can switch freely between
        # ones you own. (Intercoolers will become the same kind of equippable family next.)
        self.owned_turbos: list     = [self.turbo] if self.turbo else []
        self.dyno_result            = None
        self.grade                  = ""
        if tune is not None and tune != DEFAULT_TUNE:
            self.flash_ecu()

    # -- achievement stats (read by the ACHIEVEMENTS check table) ----------
    @property
    def e30_lifestyle(self) -> bool:
        """Flashed an E30 map at 24+ psi -> the "It's a Lifestyle" trophy."""
        tune = self.flashed_tune
        return bool(self.flashed and tune and tune.get("fuel") == "E30" and tune.get("boost", 0) >= 24)

    @property
    def is_grade_s(self) -> bool:
        return self.grade.startswith("Grade S")

    @property
    def last_blown(self) -> bool:
        return bool(self.dyno_result and self.dyno_result.get("blown"))

    @property
    def dyno_pop(self) -> float:
        return self.dyno_result.get("pop", 0.0) if self.dyno_result else 0.0

    @property
    def fully_built(self) -> bool:
        return bool(self.mods) and all(self.mods.values())

    # -- queries -----------------------------------------------------------
    def ecu_status(self) -> str:
        return "FLASHED" if self.flashed else "UNLOCKED" if self.patched else "LOCKED"

    def active_tune(self) -> dict:
        return self.slots[self.active_slot] or self.flashed_tune or self.tune

    def active_pop(self) -> float:
        return pop_score(self.active_tune())

    def compute(self) -> dict:
        """The calibration diagnostics for the running tune (whp/knock/EGT/rel/pop/blown).
        Power-from-mods is not here -- see ``build_whp``."""
        return compute_tune(self.flashed_tune or self.tune, self.mods, self._turbo_spec())

    def owned_mods(self) -> list:
        return [mod_id for mod_id in self.mods if self.mods[mod_id]]

    def _turbo_spec(self) -> dict | None:
        """The fitted turbo's spec (a TURBOS entry), or None when stock. Falls back to
        IS38 if the bool ``mods["turbo"]`` is set but no explicit variant (rivals/old saves)."""
        if self.turbo:
            return TURBOS.get(self.turbo, TURBOS["is38"])
        return TURBOS["is38"] if self.mods.get("turbo") else None

    def _effects_table(self) -> dict:
        """MOD_TABLE with its generic ``"turbo"`` entry swapped for the SELECTED turbo's
        spec, so the curve/perf math reflects which turbo is fitted."""
        return {**MOD_TABLE, "turbo": self._turbo_spec() or MOD_TABLE["turbo"]}

    def build_whp(self) -> list:
        """The car's final rpm->whp curve = stock base curve scaled by the active tune,
        plus owned mods. The tune scales in once the car is flashed (the player flashes to
        write the map; rival cars are constructed already flashed, so their tune applies)."""
        return build_whp_curve(self.base_curve, self.owned_mods(), self._tune_factor(),
                               self.idle, self.redline, effects=self._effects_table())

    def _tune_factor(self) -> float:
        """The active tune's power *relative to the stock tune* (car-agnostic, since
        ``compute_tune`` is GTI-calibrated and absolute). 1.0 = stock / unflashed."""
        if not self.flashed:
            return 1.0
        stock = compute_tune(PRESETS["stock"], self.mods)["whp"] or 1.0
        return compute_tune(self.flashed_tune or self.tune, self.mods)["whp"] / stock

    def whp_at(self, rpm: float, curve: list | None = None) -> float:
        return whp_at(curve if curve is not None else self.build_whp(), rpm)

    def car_perf(self) -> dict:
        """Race/launch performance: the built curve + its peak whp, mass and grip
        (base ± owned-mod deltas), and the blown/reliability flags from the tune."""
        curve = self.build_whp()
        owned = self.owned_mods()
        eff = self._effects_table()
        weight = self.base_weight + sum(eff[m]["weight"] for m in owned)
        grip = self.base_grip + sum(eff[m]["grip"] for m in owned)
        if self.flashed:
            diag = compute_tune(self.flashed_tune or self.tune, self.mods, self._turbo_spec())
            blown, rel = diag["blown"], diag["rel"]
        else:
            blown, rel = False, 100.0
        peak = max((w for _, w in curve), default=0.0)
        return {"curve": curve, "whp": peak, "weight": weight, "grip": grip, "blown": blown, "rel": rel}

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

    def buy_turbo(self, turbo_id: str):
        """Purchase a turbo: add it to the owned set and equip it. Also sets the
        ``mods["turbo"]`` bool so the bool-based callers (fully_built/simos/etc.) see it."""
        if turbo_id not in self.owned_turbos:
            self.owned_turbos.append(turbo_id)
        self.turbo = turbo_id
        self.mods["turbo"] = True
        return (f"bought + fitted {TURBOS[turbo_id]['name']}", "ok")

    def equip_turbo(self, turbo_id: str):
        """Switch to a turbo you already own (free)."""
        if turbo_id not in self.owned_turbos:
            return None
        self.turbo = turbo_id
        return (f"equipped {TURBOS[turbo_id]['name']}", "ok")

    def blow_dave_pool(self) -> str:
        """Which DAVE_LINES pool plays when this car grenades on the dyno (a turbo can
        override it -- e.g. the Vortex makes Dave deny it ever happened)."""
        spec = self._turbo_spec()
        return spec["dave_on_blow"] if spec else "blown"

    def record_dyno(self, result: dict):
        self.dyno_result = result
        self.grade = grade_for_result(result)
        return ("dyno pull complete: " + self.grade, "ok")

    # -- save --------------------------------------------------------------
    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in (
            "car_id",
            "name",
            "connected",
            "read",
            "patched",
            "flashed",
            "switch_patch",
            "dirty",
            "tune",
            "flashed_tune",
            "slots",
            "active_slot",
            "mods",
            "turbo",
            "owned_turbos",
            "dyno_result",
            "grade"
        )}

    def from_dict(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)
        # v3 saves predate the turbo variant: a car that owned the (single) turbo loads
        # as the IS38 baseline so its curve/caps resolve.
        if self.turbo is None and self.mods.get("turbo"):
            self.turbo = "is38"
        # keep owned/equipped consistent (and back-fill owned for pre-owned_turbos saves)
        if self.turbo and self.turbo not in self.owned_turbos:
            self.owned_turbos = list(self.owned_turbos) + [self.turbo]
