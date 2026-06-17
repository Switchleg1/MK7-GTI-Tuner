from __future__ import annotations

from library.core import assets
from library.core.constants import BLUE, GREEN_2, RIVALS, TEXT, TRACK_M
from library.stages.task_base import TaskBase

STRIP_LENGTH = 28.0  # scene units the quarter mile maps onto


class RaceTask(TaskBase):
    """Quarter-mile vs the street ladder: stage, launch on green, shift up."""

    title = "RACE"
    key = "race"
    live = True

    def build_scene(self):
        assets.load_model("ground").reparentTo(self.scene)
        self.player_car = assets.load_model("car")
        self.player_car.reparentTo(self.scene)
        self.rival_car = assets.load_model("car")
        self.rival_car.reparentTo(self.scene)
        self.rival_car.setColorScale(0.5, 0.6, 1.25, 1)  # tint the rival blue
        self._place(self.player_car, -2.2, 0.0)
        self._place(self.rival_car, 2.2, 0.0)

    def _place(self, car, x, distance):
        car.setPos(x, -2.0 + (distance / TRACK_M) * STRIP_LENGTH, 0.0)

    def tick(self, dt):
        if self.game.race_active():
            self.game.step_race(dt)
            self._place(self.player_car, -2.2, self.game.race["p"]["d"])
            self._place(self.rival_car, 2.2, self.game.race["r"]["d"])

    def bind_keys(self):
        self.accept("space", self.do_key)

    def do_key(self):
        event = self.game.race_key()
        if event in ("launch", "shift"):
            self.spawn_flames(self.player_car, 2)
        self.dirty = True

    def build_ui(self, left, right):
        game = self.game
        lbox, rbox = self.panel_pair(left, right)
        self.label("QUARTER MILE", (lbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        self.button("Stage & Race", (lbox[0] + 0.28, 0, 0.22), (0.40, 0.11), self.bind(game.start_race), game.flashed and not game.race_active(), GREEN_2)
        self.button("Launch / Shift", (lbox[0] + 0.72, 0, 0.22), (0.40, 0.11), self.do_key, game.race_active())
        self.label(game.race_result_text(), (lbox[0] + 0.05, 0, 0.02), 0.036, TEXT, wordwrap=30)
        self.label("STREET LADDER", (rbox[0] + 0.05, 0, 0.40), 0.044, BLUE)
        for index, rival in enumerate(RIVALS):
            self.button(f"{rival['name']} ${rival['purse']}", (rbox[0] + 0.45, 0, 0.27 - index * 0.09), (0.76, 0.075), self.bind(game.select_rival, index), index <= game.unlocked_rival)
