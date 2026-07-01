from __future__ import annotations

from library.core.constants import (
    BASE_EFFECTS, CAR_TABLE, EQUIP_FAMILIES, MOD_KEYS, PARTS, PRESETS,
    TURBO_DEFAULT, UNLOCKABLE_MAPS, DEFAULT_TUNE, IC_DEFAULT
)
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
        self.max_boost              = spec["max_boost"]      # stock boost slider ceiling (no aftermarket turbo)
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
        self.mods                   = mods if mods is not None else {k: False for k in MOD_KEYS}
        # Which turbo variant is fitted (None = stock). `mods["turbo"]` stays the bool
        # "owns an aftermarket turbo"; this picks WHICH from PARTS. A car built with
        # `mods["turbo"]` True but no explicit variant (rivals, old saves) defaults to IS38.
        self.turbo                  = TURBO_DEFAULT if self.mods.get("turbo") else None
        # Which intercooler variant is fitted (None = stock). `mods["ic"]` stays the bool
        # "owns an aftermarket IC"; this picks WHICH from PARTS. A car built with
        # `mods["ic"]` True but no explicit variant (rivals, old saves) defaults to the baseline.
        self.ic                     = IC_DEFAULT if self.mods.get("ic") else None
        # Turbos and intercoolers are equippable families: each part is OWNED (bought once)
        # and one is EQUIPPED. You can switch freely between ones you own (see EQUIP_FAMILIES).
        self.owned_turbos: list     = [self.turbo] if self.turbo else []
        self.owned_ic: list         = [self.ic] if self.ic else []
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
        return compute_tune(self.flashed_tune or self.tune, self.mods,
                            self._turbo_spec(), self._ic_spec(), self._boost_flow())

    def owned_mods(self) -> list:
        return [mod_id for mod_id in self.mods if self.mods[mod_id]]

    def _equipped_spec(self, kind: str) -> dict | None:
        """The fitted variant's spec for an equippable family (``"turbo"`` / ``"ic"``), or
        None when stock. Falls back to the family's baseline if its bool anchor is set but
        no explicit variant is chosen (rivals / old saves)."""
        fam = EQUIP_FAMILIES[kind]
        equipped = getattr(self, fam["equipped"])
        if equipped:
            return PARTS.get(equipped, PARTS[fam["default"]])
        return PARTS[fam["default"]] if self.mods.get(fam["anchor"]) else None

    def _turbo_spec(self) -> dict | None:
        return self._equipped_spec("turbo")

    def _ic_spec(self) -> dict | None:
        return self._equipped_spec("ic")

    def _effects_table(self) -> dict:
        """BASE_EFFECTS with each equippable family's generic anchor entry swapped for the
        SELECTED variant's spec, so the curve/perf math reflects what's actually fitted."""
        eff = dict(BASE_EFFECTS)
        for kind, fam in EQUIP_FAMILIES.items():
            eff[fam["anchor"]] = self._equipped_spec(kind) or BASE_EFFECTS[fam["anchor"]]
        return eff

    def _boost_flow(self) -> float:
        """Airflow multiplier on the boost->whp term: 1.0 + the ``flow`` of every equipped
        mod (turbo + IC + intake/dp), each family anchor resolved to its fitted variant.
        Higher-flowing hardware makes each psi of boost worth more power (see compute_tune)."""
        eff = self._effects_table()
        return 1.0 + sum(eff[m].get("flow", 0.0) for m in self.owned_mods())

    def boost_slider_max(self) -> float:
        """The boost slider's upper bound: the car's stock max boost raised by the
        ``max_boost`` of EVERY equipped mod (turbo + intercooler + bolt-ons). Each part's
        ``max_boost`` in PARTS is how much psi ceiling it unlocks; the equipped turbo/IC
        variants resolve through ``_effects_table``."""
        eff = self._effects_table()
        return self.max_boost + sum(eff[m]["max_boost"] for m in self.owned_mods())

    def build_whp(self) -> list:
        """The car's final rpm->whp curve = stock base curve scaled by the active tune,
        plus owned mods. The tune scales in once the car is flashed (the player flashes to
        write the map; rival cars are constructed already flashed, so their tune applies)."""
        return build_whp_curve(self.base_curve, self.owned_mods(), self._tune_factor(),
                               self.idle, self.redline, effects=self._effects_table(),
                               spool_rpm=self.spool_rpm)

    def stock_curve(self) -> list:
        """The stock (no mods, stock tune) rpm->whp curve -- the faint dyno reference. Runs
        through the same NA-floor + spool-ramp model so it has no low-rpm torque spike."""
        return build_whp_curve(self.base_curve, [], 1.0, self.idle, self.redline,
                               spool_rpm=self.spool_rpm)

    def _tune_factor(self) -> float:
        """The active tune's power *relative to the stock tune* (car-agnostic, since
        ``compute_tune`` is GTI-calibrated and absolute). 1.0 = stock / unflashed. The
        equipped parts' airflow (`_boost_flow`) is applied to both so a flowier build turns
        the same boost into a bigger tune factor (=> more whp on the composed curve)."""
        if not self.flashed:
            return 1.0
        flow = self._boost_flow()
        stock = compute_tune(PRESETS["stock"], self.mods, flow=flow)["whp"] or 1.0
        return compute_tune(self.flashed_tune or self.tune, self.mods, flow=flow)["whp"] / stock

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
            diag = compute_tune(self.flashed_tune or self.tune, self.mods,
                                self._turbo_spec(), self._ic_spec(), self._boost_flow())
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
        return (f"installed {PARTS[mod_id]['name']}", "ok")

    def buy_mod(self, part_id: str):
        """Purchase an equippable-family part (a turbo or intercooler): add it to that
        family's owned set, equip it, and set its bool anchor so the bool-based callers
        (fully_built/simos/etc.) see it. The part's ``kind`` selects which Car attrs to
        touch, via the EQUIP_FAMILIES table -- so adding a family needs no new method."""
        fam = EQUIP_FAMILIES[PARTS[part_id]["kind"]]
        owned = getattr(self, fam["owned"])
        if part_id not in owned:
            owned.append(part_id)
        setattr(self, fam["equipped"], part_id)
        self.mods[fam["anchor"]] = True
        return (f"bought + fitted {PARTS[part_id]['name']}", "ok")

    def equip_mod(self, part_id: str):
        """Switch to an equippable-family part you already own (free)."""
        fam = EQUIP_FAMILIES[PARTS[part_id]["kind"]]
        if part_id not in getattr(self, fam["owned"]):
            return None
        setattr(self, fam["equipped"], part_id)
        return (f"equipped {PARTS[part_id]['name']}", "ok")

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
            "ic",
            "owned_ic",
            "dyno_result",
            "grade"
        )}

    def from_dict(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)
        # Older saves predate the turbo/IC variants: a car that owned the (single) unit loads
        # as that family's baseline variant so its curve/caps/relief resolve. Then keep each
        # family's owned/equipped consistent (back-filling owned for pre-owned-set saves).
        for kind, fam in EQUIP_FAMILIES.items():
            equipped = getattr(self, fam["equipped"], None)
            if equipped is None and self.mods.get(fam["anchor"]):
                equipped = fam["default"]
                setattr(self, fam["equipped"], equipped)
            owned = list(getattr(self, fam["owned"], []) or [])
            if equipped and equipped not in owned:
                owned.append(equipped)
            setattr(self, fam["owned"], owned)
