from __future__ import annotations

import math
import time

from library.core.constants import AMBER, AUDIO, DIM, GREEN, GREEN_2, PANEL, RED, TEXT
from library.core.utils import clamp
from library.stages.task_base import TaskBase


class StreetTask(TaskBase):
    """Idle the GTI on the street: blip the throttle, preview pops for cred, and
    watch the Karen meter climb. Pops/throttle spit exhaust flames."""

    title = "SKREETS"
    key = "street"
    live = True

    def build_scene(self):
        self.car = self.add_garage_scene()
        self.wheels = list(self.car.findAllMatches("**/tire_*")) + list(self.car.findAllMatches("**/rim_*"))
        self.rpm = 850.0
        self.throttle = 0.0
        self.prev_throttle = 0.0
        self.spin = 0.0

    def bind_keys(self):
        self.accept("space", self.do_throttle)

    def tick(self, dt):
        self.throttle = max(0.0, self.throttle - dt * 1.6)
        self.rpm += (850 + self.throttle * 6200 - self.rpm) * clamp(dt * 5, 0, 1)
        self.spin += dt * (4 + self.rpm / 220) * 40
        for wheel in self.wheels:
            wheel.setP(self.spin)
        self.car.setH(math.sin(time.perf_counter() * 1.3) * 1.3)
        self.app.audio.set_engine(self.rpm, 0.12 + 0.88 * self.throttle)
        # Lifting off the throttle at speed is where the overrun crackle lives.
        if self.prev_throttle > 0.25 and self.throttle <= 0.06 and self.rpm > AUDIO["overrun_min_rpm"]:
            self.app.audio.bov()
            self.app.audio.overrun(self.game.car.active_pop(), 0.9)
        self.prev_throttle = self.throttle

    def do_throttle(self):
        if not self.game.car.flashed:
            return
        self.throttle = 1.0
        self.spawn_flames(self.car, 3)

    def do_pops(self):
        if not self.game.car.flashed:
            return
        count = self.game.register_pops()
        self.spawn_flames(self.car, count)
        self.app.audio.bov()
        self.app.audio.overrun(self.game.car.active_pop(), 1.0)
        self.dirty = True

    def build_ui(self, left, right):
        bro = self.game.bro
        self.label(f"{round(self.rpm)} RPM", (left + 0.06, 0, 0.34), 0.055, TEXT)
        self.image("emoji_cred", (left + 0.10, 0, 0.20), 0.05)
        self.label(f"Cred {round(bro.cred)}", (left + 0.20, 0, 0.185), 0.046, GREEN)
        self.image("emoji_karen", (left + 0.10, 0, 0.04), 0.05)
        self.label(f"Karen {round(bro.karen)}%", (left + 0.20, 0, 0.025), 0.046, RED if bro.karen >= 80 else AMBER)
        bar_x, bar_w = left + 0.06, 0.62
        self.frame((bar_x, bar_x + bar_w, -0.075, -0.05), color=PANEL, border=None)
        fill = bar_w * clamp(bro.karen / 100, 0, 1)
        self.frame((bar_x, bar_x + max(0.001, fill), -0.075, -0.05), color=RED, border=None)
        self.button("Throttle", (left + 0.28, 0, -0.34), (0.42, 0.12), self.do_throttle, self.game.car.flashed, GREEN_2)
        self.button("Preview Pops", (left + 0.78, 0, -0.34), (0.46, 0.12), self.do_pops, self.game.car.flashed)
        self.label("Tap Throttle (Space) and Preview Pops for cred - but the Karen meter is watching.", (left + 0.06, 0, -0.50), 0.034, DIM, wordwrap=46)
