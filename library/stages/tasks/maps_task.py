from __future__ import annotations

import random

from library.core.constants import (
    AMBER, BLUE, DIM, FUELS, GREEN, GREEN_2, PRESET_BUTTONS, PRO_MAPS, SLIDERS, TEXT, UNLOCKABLE_MAPS,
)
from library.game.tuning import pop_score
from library.stages.task_base import TaskBase

# Derived once: slider attr -> tune key, and each row's (attr, box index, z).
SLIDER_KEY = {attr: key for attr, key, _, _ in SLIDERS}
_ROW_Z = (0.30, 0.18, 0.06, 0.18, 0.06, -0.06)  # first 3 left panel, last 3 right
SLIDER_ROWS = [(SLIDERS[i][0], 0 if i < 3 else 1, _ROW_Z[i]) for i in range(len(SLIDERS))]


class MapsTask(TaskBase):
    """Edit the calibration with live sliders, load presets, manage switch-patch slots."""

    title = "TUNE"
    key = "maps"
    music_key = "tuning"  # data/music/tuning/

    # Fixed button Z rows (the slider rows above them are static, so these don't move).
    FUEL_Z, PRESET_Z, UMAP_Z, SLOT_Z, ASSIGN_Z = -0.05, -0.23, -0.47, -0.28, -0.628

    def build_ui(self):
        car = self.game.car
        lbox, rbox = self.panel_boxes(*self.bounds())
        boxes = (lbox, rbox)
        for index, box in enumerate(boxes):
            self.ui.add_frame(f"panel-{index}", frame_size=box, border=None)
        self.ui.add_image("emoji-pops", "emoji_pops", (rbox[0] + 0.10, 0, 0.305), 0.045)
        for i, fuel in enumerate(FUELS):
            self.ui.add_button(f"fuel-{fuel}", fuel, (lbox[0] + 0.42 + i * 0.20, 0, self.FUEL_Z), (0.18, 0.075),
                               (lambda f=fuel: self._set_fuel(f)), True, GREEN_2, 0.036)
        for index, (pkey, pname) in enumerate(PRESET_BUTTONS):
            self.ui.add_button(f"preset-{pkey}", pname, (lbox[0] + 0.21 + index * 0.30, 0, self.PRESET_Z),
                               (0.27, 0.085), self.bind(self._apply_preset, pkey))
        # A fixed pool of "unlocked map" buttons -- shown/retargeted as maps are earned.
        for i in range(4):
            self.ui.add_button(f"umap-{i}", "", (lbox[0] + 0.40, 0, self.UMAP_Z - i * 0.082), (0.74, 0.072),
                               None, is_visible=False)
        for index in range(len(car.slots)):
            self.ui.add_button(f"slot-{index}", "", (rbox[0] + 0.34, 0, self.SLOT_Z - index * 0.082),
                               (0.56, 0.072), self.bind(self._select_slot, index), is_visible=(index == 0))
        self.ui.add_button("assign", "Assign Current Tune", (rbox[0] + 0.36, 0, self.ASSIGN_Z), (0.58, 0.082),
                           self.bind(self._assign_slot), car.flashed)
        # text: static titles + dynamic readouts (slider values / burble / dirty)
        self.ui.add_text("t-power", "POWER MAPS", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui.add_text("t-fuel", "Fuel", (lbox[0] + 0.06, 0, -0.055), 0.032, DIM)
        self.ui.add_text("dirty", "", (lbox[0] + 0.06, 0, self.PRESET_Z - 0.13), 0.030, AMBER)
        self.ui.add_text("t-unlocked", "UNLOCKED MAPS", (lbox[0] + 0.06, 0, self.UMAP_Z + 0.05), 0.026, GREEN, is_visible=False)
        self.ui.add_text("t-pops", "POPS & BANGS", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui.add_text("burble", "", (rbox[0] + 0.19, 0, 0.30), 0.046, AMBER)
        self.ui.add_text("t-slots", "SWITCH SLOTS", (rbox[0] + 0.05, 0, -0.18), 0.032, DIM)
        for attr, box_i, z in SLIDER_ROWS:
            vrange = next(s[2] for s in SLIDERS if s[0] == attr)
            value = car.tune[SLIDER_KEY[attr]]
            slider = self.ui.add_slider(attr, (boxes[box_i][0] + 0.64, 0, z), vrange, value, width=0.5)
            slider.command_fn(self._on_slide)  # wired after build so init doesn't fire it
            setattr(self, attr, slider)
            self.ui.add_text(f"val-{attr}", "", (boxes[box_i][0] + 0.06, 0, z + 0.035), 0.030, TEXT)

    def update_ui(self, left, right):
        self._ready = False
        car = self.game.car
        # Sliders are persistent; redraws only sync their values and labels.
        for attr, box_i, z in SLIDER_ROWS:
            fmt = next(s[3] for s in SLIDERS if s[0] == attr)
            value = car.tune[SLIDER_KEY[attr]]
            getattr(self, attr).value(value)
            self.ui.get(f"val-{attr}").text(fmt(value))
        self.ui.get("burble").text(f"Burble index: {round(pop_score(car.tune))}")
        self.ui.get("dirty").text("Flash required for changed tune." if car.dirty else "")
        # Unlocked maps: pro-granted first (rarer), then community; capped to the pool.
        maps = self.game.bro.unlocked_maps
        ordered = ([k for k in maps if k in PRO_MAPS] + [k for k in maps if k not in PRO_MAPS])[:4]
        self.ui.get("t-unlocked").is_visible(bool(ordered))
        for i in range(4):
            button = self.ui.get(f"umap-{i}")
            if i < len(ordered):
                key = ordered[i]
                button.text(UNLOCKABLE_MAPS[key]["name"])
                button.command_fn(self.bind(self._apply_preset, key))
                button.is_visible(True)
            else:
                button.is_visible(False)
        for index, slot in enumerate(car.slots):
            button = self.ui.get(f"slot-{index}")
            button.is_visible(car.switch_patch or index == 0)
            button.text(f"Slot {index + 1}: {slot.get('name', 'empty') if slot else 'empty'}")
            button.enabled(bool(slot))
        self._ready = True

    def _on_slide(self):
        if not getattr(self, "_ready", False):
            return
        tune = self.game.car.tune
        tune["boost"] = round(self.sl_boost.value() * 2) / 2
        tune["timing"] = round(self.sl_timing.value() * 2) / 2
        tune["lambda"] = round(self.sl_lambda.value() / 0.005) * 0.005
        tune["of"] = float(round(self.sl_of.value()))
        tune["or"] = float(round(self.sl_or.value()))
        tune["th"] = float(round(self.sl_th.value()))
        self.game.car.dirty = self.game.car.flashed
        self._refresh_readouts()

    def _refresh_readouts(self):
        car = self.game.car
        for attr, key, vrange, fmt in SLIDERS:
            self.ui.get(f"val-{attr}").text(fmt(car.tune[SLIDER_KEY[attr]]))
        self.ui.get("burble").text(f"Burble index: {round(pop_score(car.tune))}")
        self.ui.get("dirty").text("Flash required for changed tune." if car.dirty else "")

    def _set_fuel(self, fuel):
        self.game.car.tune["fuel"] = fuel
        self.game.car.dirty = self.game.car.flashed
        self.dirty = True  # discrete click -> resync the readouts and slot state

    def _apply_preset(self, key: str):
        self._log_result(self.game.car.apply_preset(key))

    def _assign_slot(self):
        self._log_result(self.game.car.assign_slot())

    def _select_slot(self, index: int):
        game = self.game
        game.car.select_slot(index)
        if 0 <= index < len(game.car.slots) and game.car.slots[index]:
            game.bro.map_switches += 1  # the stalk_wizard trophy is polled off map_switches
            if random.random() < 0.4:
                game.dave("mapswitch")
