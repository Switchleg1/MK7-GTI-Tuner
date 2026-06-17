from __future__ import annotations

from library.core.constants import AMBER, BLUE, DIM, GREEN, GREEN_2, TEXT
from library.stages.task_base import TaskBase


class DynoTask(TaskBase):
    """Strap the GTI to the dyno; a pull spins the wheels and grades the map."""

    title = "DYNO"
    key = "dyno"
    live = True

    def build_scene(self):
        self.car = self.add_garage_scene()
        self.wheels = list(self.car.findAllMatches("**/tire_*")) + list(self.car.findAllMatches("**/rim_*"))
        self.spin = 0.0

    def tick(self, dt):
        if self.game.dyno_running:
            self.spin += dt * 1600
            for wheel in self.wheels:
                wheel.setP(self.spin)
            if self.game.dyno_done():
                self.game.finish_dyno()
                self.dirty = True

    def build_ui(self, left, right):
        game = self.game
        self.frame((left, right, -0.62, 0.48), border=None)
        self.label("DYNO CELL", (left + 0.05, 0, 0.40), 0.044, BLUE)
        self.button("Run Dyno Pull", (left + 0.30, 0, 0.24), (0.42, 0.11), self.bind(game.run_dyno), game.flashed and not game.dyno_running, GREEN_2)
        state = "pulling..." if game.dyno_running else "Loaded. Send it." if game.flashed else "Flash a tune first."
        self.label(state, (left + 0.58, 0, 0.245), 0.036, AMBER if game.dyno_running else DIM)
        result = game.dyno_preview()
        self.label(f"WHP {round(result['whp'])}   KR {result['KR']:.1f}   EGT {round(result['egt'])} C   REL {round(result['rel'])}%   POP {round(result['pop'])}", (left + 0.05, 0, 0.06), 0.045, TEXT)
        self.label(game.grade or "Dyno results will appear here.", (left + 0.05, 0, -0.10), 0.038, GREEN if game.grade.startswith("Grade") else DIM, wordwrap=56)
