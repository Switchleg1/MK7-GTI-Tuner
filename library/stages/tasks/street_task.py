from __future__ import annotations

import math
import random
import time

from library.core.constants import AMBER, DIM, GREEN, GREEN_2, PANEL, RED, TEXT
from library.core.utils import clamp
from library.stages.task_base import TaskBase


class StreetTask(TaskBase):
    """Idle the GTI on the street: blip the throttle, preview pops for cred, and
    watch the Karen meter climb. Pops/throttle spit exhaust flames."""

    title = "SKREETS"
    key = "street"
    live = True
    music_key = "skreetz"  # data/music/skreetz/

    def build_scene(self):
        self.car = self.add_garage_scene()
        self.wheels = list(self.car.findAllMatches("**/tire_*")) + list(self.car.findAllMatches("**/rim_*"))
        self.rpm = 850.0
        self.throttle = 0.0
        self.spin = 0.0
        self._held = False
        self._lift_armed = False
        self._peak_rpm = 0.0

    def bind_keys(self):
        # Hold Space to hold the throttle wide open; release to lift and crackle.
        self.accept("space", self.hold_throttle)
        self.accept("space-up", self.release_throttle)

    def tick(self, dt):
        if self._held:
            self.throttle = 1.0
        else:
            self.throttle = max(0.0, self.throttle - dt * 1.6)
        self.rpm += (850 + self.throttle * 6200 - self.rpm) * clamp(dt * 5, 0, 1)
        self.spin += dt * (4 + self.rpm / 220) * 40
        for wheel in self.wheels:
            wheel.setP(self.spin)
        self.car.setH(math.sin(time.perf_counter() * 1.3) * 1.3)
        self._peak_rpm = max(self._peak_rpm, self.rpm)
        self.app.audio.set_engine(self.rpm, 0.12 + 0.88 * self.throttle)
        # A rev arms the lift; as the throttle decays back down, fire the crackle.
        if self._lift_armed and self.throttle < 0.15:
            self._lift_armed = False
            if self._peak_rpm > 1800:
                self.app.audio.bov()
                self.app.audio.overrun(self.game.car.active_pop(), 0.9)
                self.spawn_flames(self.car, self.game.register_pops())  # cred + Karen + flames
                self._spawn_reactions()  # floating crowd / Karen emoji popups
                self.dirty = True  # refresh the cred / Karen readout now
            self._peak_rpm = 0.0

    def hold_throttle(self):
        """Space pressed: peg the throttle open and arm the lift-off crackle."""
        if not self.game.car.flashed or self._held:
            return
        self._held = True
        self._lift_armed = True
        self.spawn_flames(self.car, 3)

    def release_throttle(self):
        """Space released: let the revs fall -- tick() fires the overrun pops."""
        self._held = False

    def do_throttle(self):
        """Throttle button = a quick blip (Space is the hold)."""
        if not self.game.car.flashed:
            return
        self.throttle = 1.0
        self._lift_armed = True
        self.spawn_flames(self.car, 3)

    def do_pops(self):
        if not self.game.car.flashed:
            return
        count = self.game.register_pops()
        self.spawn_flames(self.car, count)
        self.app.audio.bov()
        self.app.audio.overrun(self.game.car.active_pop(), 1.0)
        self._spawn_reactions()
        self.dirty = True

    def _spawn_reactions(self):
        """Float crowd-hype emojis up on the right and Karen-rage on the left,
        scaled by the active tune's burble and the current heat (like the original)."""
        pop = self.game.car.active_pop()
        karen = self.game.bro.karen
        hype = int(clamp(round(pop / 18), 1, 5))
        anger = (1 if pop > 35 or karen > 30 else 0) + (1 if karen > 70 else 0)
        for _ in range(hype):
            self.spawn_reaction(random.choice(("emoji_fire", "emoji_cred")),
                                x=random.uniform(0.25, 1.30), z=random.uniform(-0.30, 0.05),
                                scale=random.uniform(0.05, 0.085), rise=random.uniform(0.30, 0.55),
                                life=random.uniform(0.9, 1.3))
        for _ in range(anger):
            self.spawn_reaction("emoji_karen",
                                x=random.uniform(-1.30, -0.25), z=random.uniform(-0.30, 0.05),
                                scale=random.uniform(0.05, 0.075), rise=random.uniform(0.30, 0.50),
                                life=random.uniform(0.9, 1.2))

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
        label = "Throttle [HELD]" if self._held else "Throttle"
        self.button(label, (left + 0.28, 0, -0.34), (0.42, 0.12), self.do_throttle, self.game.car.flashed, GREEN if self._held else GREEN_2)
        self.button("Preview Pops", (left + 0.78, 0, -0.34), (0.46, 0.12), self.do_pops, self.game.car.flashed)
        self.label("Hold Space to keep it pinned, then release to crackle - Preview Pops for cred. The Karen meter is watching.", (left + 0.06, 0, -0.50), 0.034, DIM, wordwrap=46)
