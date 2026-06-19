from __future__ import annotations

from library.core.constants import AMBER, BLUE, GREEN_2, TEXT
from library.stages.task_base import TaskBase


class BenchTask(TaskBase):
    """Re-flash the ECU with the current tune (the cinematic did the first flash)."""

    title = "BENCH"
    key = "bench"

    def build_buttons(self):
        game = self.game
        lbox, _ = self.panel_boxes(*self.bounds())
        self.buttons.add("switch", f"switch patch: {'ON' if game.car.switch_patch else 'OFF'}",
                         (lbox[0] + 0.32, 0, 0.02), (0.48, 0.10), self.bind(game.toggle_switch))
        self.buttons.add("flash", "FLASH ECU", ((lbox[0] + lbox[1]) / 2, 0, -0.24),
                         (lbox[1] - lbox[0] - 0.12, 0.12), self.bind(game.flash_ecu), True, GREEN_2)

    def build_ui(self, left, right):
        game = self.game
        lbox, rbox = self.panel_pair(left, right)
        self.label("SIMOSTOOLS - RE-FLASH", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.label("ECU is unlocked. Build a map in TUNE, then write it to the car here.", (lbox[0] + 0.05, 0, 0.29), 0.034, TEXT, wordwrap=24)
        self.label(f"Loaded tune: {game.car.tune.get('name', 'Your Tune')}", (lbox[0] + 0.05, 0, 0.16), 0.036, TEXT)
        self.buttons.get("switch").text(f"switch patch: {'ON' if game.car.switch_patch else 'OFF'}")
        if game.car.dirty:
            self.label("Flash required for changed tune.", (lbox[0] + 0.05, 0, -0.40), 0.033, AMBER)
        self.label("BENCH LOG", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for offset, (msg, kind) in enumerate(game.logs[-9:]):
            self.label(msg, (rbox[0] + 0.05, 0, 0.30 - offset * 0.08), 0.031, self.kind_color(kind), wordwrap=30)
