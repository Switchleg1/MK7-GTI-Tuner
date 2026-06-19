from __future__ import annotations

from library.core.constants import (
    AMBER, BLUE, DIM, FUELS, GREEN, GREEN_2, PRESET_BUTTONS, PRO_MAPS, SLIDERS, TEXT, UNLOCKABLE_MAPS,
)
from library.game.tuning import pop_score
from library.stages.task_base import TaskBase

# Derived once: slider attr -> tune key (the SLIDERS table itself lives in constants).
SLIDER_KEY = {attr: key for attr, key, _, _ in SLIDERS}


class MapsTask(TaskBase):
    """Edit the calibration with live sliders, load presets, manage switch-patch slots."""

    title = "TUNE"
    key = "maps"
    music_key = "tuning"  # data/music/tuning/

    def build_ui(self, left, right):
        self._ready = False
        self.value_labels = {}
        car = self.game.car
        lbox, rbox = self.panel_pair(left, right)

        # -- left panel: power maps --------------------------------------
        self.label("POWER MAPS", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        z = 0.30
        for attr, key, vrange, fmt in SLIDERS[:3]:
            self._param_row(lbox, attr, fmt, vrange, z)
            z -= 0.12
        self.label("Fuel", (lbox[0] + 0.06, 0, z + 0.005), 0.032, DIM)
        for i, fuel in enumerate(FUELS):
            sel = car.tune["fuel"] == fuel
            self.buttons.button(f"fuel-{fuel}", fuel, (lbox[0] + 0.42 + i * 0.20, 0, z + 0.01), (0.18, 0.075),
                                (lambda f=fuel: self._set_fuel(f)), True, GREEN_2 if sel else None, 0.036)
        z -= 0.17
        for index, (pkey, pname) in enumerate(PRESET_BUTTONS):
            self.buttons.button(f"preset-{pkey}", pname, (lbox[0] + 0.21 + index * 0.30, 0, z), (0.27, 0.085),
                                self.bind(self.game.apply_preset, pkey))
        self.lbl_dirty = self.label("Flash required for changed tune." if car.dirty else "",
                                    (lbox[0] + 0.06, 0, z - 0.13), 0.030, AMBER)
        maps = self.game.bro.unlocked_maps
        if maps:
            # pro-granted maps first (the rarer reward), then community; capped to fit.
            ordered = [k for k in maps if k in PRO_MAPS] + [k for k in maps if k not in PRO_MAPS]
            cz = z - 0.24
            self.label("UNLOCKED MAPS", (lbox[0] + 0.06, 0, cz + 0.05), 0.026, GREEN)
            for index, key in enumerate(ordered[:4]):
                self.buttons.button(f"umap-{key}", UNLOCKABLE_MAPS[key]["name"], (lbox[0] + 0.40, 0, cz - index * 0.082), (0.74, 0.072),
                                    self.bind(self.game.apply_preset, key))

        # -- right panel: pops & bangs + switch slots --------------------
        self.label("POPS & BANGS", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.image("emoji_pops", (rbox[0] + 0.10, 0, 0.305), 0.045)
        self.lbl_burble = self.label(f"Burble index: {round(pop_score(car.tune))}",
                                     (rbox[0] + 0.19, 0, 0.30), 0.046, AMBER)
        z = 0.18
        for attr, key, vrange, fmt in SLIDERS[3:]:
            self._param_row(rbox, attr, fmt, vrange, z)
            z -= 0.12
        self.label("SWITCH SLOTS", (rbox[0] + 0.05, 0, z + 0.0), 0.032, DIM)
        z -= 0.10
        for index, slot in enumerate(car.slots):
            if not car.switch_patch and index > 0:
                continue
            name = slot.get("name", "empty") if slot else "empty"
            self.buttons.button(f"slot-{index}", f"Slot {index + 1}: {name}", (rbox[0] + 0.34, 0, z), (0.56, 0.072),
                                self.bind(self.game.select_slot, index), bool(slot))
            z -= 0.082
        self.buttons.button("assign", "Assign Current Tune", (rbox[0] + 0.36, 0, z - 0.02), (0.58, 0.082),
                            self.bind(self.game.assign_slot), car.flashed)

        self._ready = True

    def _param_row(self, box, attr, fmt, vrange, z):
        value = self.game.car.tune[SLIDER_KEY[attr]]
        self.value_labels[attr] = self.label(fmt(value), (box[0] + 0.06, 0, z + 0.035), 0.030, TEXT)
        node = self.slider((box[0] + 0.64, 0, z), vrange, value, width=0.5)
        setattr(self, attr, node)
        node["command"] = self._on_slide  # wired after build so init doesn't fire it

    def _on_slide(self):
        if not getattr(self, "_ready", False):
            return
        tune = self.game.car.tune
        tune["boost"] = round(self.sl_boost["value"] * 2) / 2
        tune["timing"] = round(self.sl_timing["value"] * 2) / 2
        tune["lambda"] = round(self.sl_lambda["value"] / 0.005) * 0.005
        tune["of"] = float(round(self.sl_of["value"]))
        tune["or"] = float(round(self.sl_or["value"]))
        tune["th"] = float(round(self.sl_th["value"]))
        self.game.car.dirty = self.game.car.flashed
        self._refresh_readouts()

    def _refresh_readouts(self):
        car = self.game.car
        for attr, label in self.value_labels.items():
            _, _, _, fmt = next(s for s in SLIDERS if s[0] == attr)
            label["text"] = fmt(car.tune[SLIDER_KEY[attr]])
        self.lbl_burble["text"] = f"Burble index: {round(pop_score(car.tune))}"
        self.lbl_dirty["text"] = "Flash required for changed tune." if car.dirty else ""

    def _set_fuel(self, fuel):
        self.game.car.tune["fuel"] = fuel
        self.game.car.dirty = self.game.car.flashed
        self.dirty = True  # discrete click -> full redraw updates the highlight
