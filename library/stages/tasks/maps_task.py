from __future__ import annotations

from library.core.constants import AMBER, BLUE, TEXT
from library.game.tuning import pop_score
from library.stages.task_base import TaskBase

PRESET_BUTTONS = [("stock", "Stock"), ("stage1", "Stage 1"), ("stage2", "Stage 2"), ("crackle", "Crackle")]


class MapsTask(TaskBase):
    """Edit the calibration, load presets, and manage switch-patch map slots."""

    title = "TUNE"
    key = "maps"

    def build_ui(self, left, right):
        game = self.game
        lbox, rbox = self.panel_pair(left, right)
        self.label("CALIBRATION", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        lines = [f"Boost: {game.tune['boost']:.1f} psi", f"Timing: {game.tune['timing']:.1f} deg", f"Lambda: {game.tune['lambda']:.3f}", f"Fuel: {game.tune['fuel']}"]
        for offset, line in enumerate(lines):
            self.label(line, (lbox[0] + 0.07, 0, 0.28 - offset * 0.10), 0.043, TEXT)
        for index, (key, name) in enumerate(PRESET_BUTTONS):
            self.button(name, (lbox[0] + 0.19 + index * 0.29, 0, -0.25), (0.25, 0.095), self.bind(game.apply_preset, key))
        self.label("POPS & SLOTS", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.image("emoji_pops", (rbox[0] + 0.10, 0, 0.275), 0.05)
        self.label(f"Burble index: {round(pop_score(game.tune))}", (rbox[0] + 0.19, 0, 0.27), 0.05, AMBER)
        y = 0.14
        for index, slot in enumerate(game.slots):
            if not game.switch_patch and index > 0:
                continue
            label = f"Slot {index + 1}: {slot.get('name', 'empty') if slot else 'empty'}"
            self.button(label, (rbox[0] + 0.34, 0, y), (0.56, 0.085), self.bind(game.select_slot, index), bool(slot))
            y -= 0.10
        self.button("Assign Current Tune", (rbox[0] + 0.36, 0, -0.34), (0.58, 0.10), self.bind(game.assign_slot), game.flashed)
