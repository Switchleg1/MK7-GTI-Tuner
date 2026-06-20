from __future__ import annotations

from library.core.constants import AMBER, BLUE, DIM, GREEN_2, TEXT
from library.stages.task_base import TaskBase


class BenchTask(TaskBase):
    """Re-flash the ECU with the current tune (the cinematic did the first flash)."""

    title = "BENCH"
    key = "bench"

    def build_objects(self):
        game = self.game
        lbox, rbox = self.panel_boxes(*self.bounds())
        self.ui.add_button("switch", "", (lbox[0] + 0.32, 0, 0.02), (0.48, 0.10), self.bind(game.toggle_switch))
        self.ui.add_button("flash", "FLASH ECU", ((lbox[0] + lbox[1]) / 2, 0, -0.24),
                           (lbox[1] - lbox[0] - 0.12, 0.12), self.bind(game.flash_ecu), True, GREEN_2)
        self.ui.add_text("title_l", "SIMOSTOOLS - RE-FLASH", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.ui.add_text("info", "ECU is unlocked. Build a map in TUNE, then write it to the car here.",
                         (lbox[0] + 0.05, 0, 0.29), 0.034, TEXT, wordwrap=24)
        self.ui.add_text("loaded", "", (lbox[0] + 0.05, 0, 0.16), 0.036, TEXT)
        self.ui.add_text("dirty", "Flash required for changed tune.", (lbox[0] + 0.05, 0, -0.40), 0.033, AMBER, is_visible=False)
        self.ui.add_text("title_r", "BENCH LOG", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for i in range(9):
            self.ui.add_text(f"log-{i}", "", (rbox[0] + 0.05, 0, 0.30 - i * 0.08), 0.031, DIM, wordwrap=30, is_visible=False)

    def build_ui(self, left, right):
        game = self.game
        self.panel_pair(left, right)  # the two panel frames (transient)
        self.ui.get("loaded").text(f"Loaded tune: {game.car.tune.get('name', 'Your Tune')}")
        self.ui.get("switch").text(f"switch patch: {'ON' if game.car.switch_patch else 'OFF'}")
        self.ui.get("dirty").is_visible(game.car.dirty)
        logs = game.logs[-9:]
        for i in range(9):
            line = self.ui.get(f"log-{i}")
            if i < len(logs):
                msg, kind = logs[i]
                line.text(msg)
                line.color(self.kind_color(kind))
                line.is_visible(True)
            else:
                line.is_visible(False)
