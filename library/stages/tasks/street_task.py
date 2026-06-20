from __future__ import annotations

import math
import random
import time

from library.core.constants import (
    AMBER, BUST_FINE, DIM, ED_BUST, GREEN, GREEN_2, KAREN_AFTER_BUST,
    KAREN_COOLDOWN_PER_SEC, PANEL, RED, TEXT,
)
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
        self.wheels = self.prepare_wheels(self.car)
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
        self.spin -= dt * (4 + self.rpm / 220) * 40
        for wheel in self.wheels:
            wheel.setP(self.spin)
        self.car.setH(math.sin(time.perf_counter() * 1.3) * 1.3)
        self._peak_rpm = max(self._peak_rpm, self.rpm)
        self.app.audio.set_engine(self.rpm, 0.12 + 0.88 * self.throttle)
        # Karen cools down whenever the bro isn't actively making noise.
        if self.throttle < 0.08:
            self._cool_karen(dt)
        # A rev arms the lift; as the throttle decays back down, fire the crackle.
        if self._lift_armed and self.throttle < 0.15:
            self._lift_armed = False
            if self._peak_rpm > 1800:
                self.app.audio.bov()
                self.app.audio.overrun(self.game.car.active_pop(), 0.9)
                self.spawn_flames(self.car, self._pops())  # cred + Karen + flames
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
        count = self._pops()
        self.spawn_flames(self.car, count)
        self.app.audio.bov()
        self.app.audio.overrun(self.game.car.active_pop(), 1.0)
        self._spawn_reactions()
        self.dirty = True

    # -- Karen / cops (street-only mechanics) ------------------------------
    def _cool_karen(self, dt):
        """Karen cools down while the bro isn't making noise (throttle down).
        No-op once the meter is already at 0."""
        if self.game.bro.karen > 0:
            self.game.bro.add_heat(-dt * KAREN_COOLDOWN_PER_SEC)

    def _pops(self) -> int:
        """Register a pop blip on the model (cred / Karen / quip) and, if that just
        capped the Karen meter, take the bust. Returns the flame count for the scene."""
        count = self.game.register_pops()
        if self.game.bro.karen >= 100:
            self._bust()
        return count

    def _bust(self):
        """Karen meter capped -> the cops roll up: a citation (scaled by rep), a
        partial meter reset, an emotional-damage hit, and the achievement. Repeatable
        -- every cap-out is a fresh citation."""
        bro = self.game.bro
        fine = int(BUST_FINE * (1 + bro.cred / 300.0))
        bro.pay_repair(fine)
        bro.karen = KAREN_AFTER_BUST
        self.game.log(f"COPS rolled up - noise complaint citation: -${fine}", "err")
        self.game.hurt_bro(ED_BUST)
        self.game.dave("cops")
        self.game.unlock("menace", "Neighborhood Menace")

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

    def build_objects(self):
        left, _ = self.bounds()
        flashed = self.game.car.flashed
        self.ui.add_button("throttle", "Throttle", (left + 0.28, 0, -0.34), (0.42, 0.12), self.do_throttle, flashed, GREEN_2)
        self.ui.add_button("pops", "Preview Pops", (left + 0.78, 0, -0.34), (0.46, 0.12), self.do_pops, flashed)
        self.ui.add_text("rpm", "", (left + 0.06, 0, 0.34), 0.055, TEXT)
        self.ui.add_text("cred", "", (left + 0.20, 0, 0.185), 0.046, GREEN)
        self.ui.add_text("karen", "", (left + 0.20, 0, 0.025), 0.046, AMBER)
        self.ui.add_text("hint", "Hold Space to keep it pinned, then release to crackle - Preview Pops for cred. The Karen meter is watching.",
                         (left + 0.06, 0, -0.50), 0.034, DIM, wordwrap=46)

    def build_ui(self, left, right):
        bro = self.game.bro
        self.ui.get("rpm").text(f"{round(self.rpm)} RPM")
        self.image("emoji_cred", (left + 0.10, 0, 0.20), 0.05)
        self.ui.get("cred").text(f"Cred {round(bro.cred)}")
        self.image("emoji_karen", (left + 0.10, 0, 0.04), 0.05)
        karen = self.ui.get("karen")
        karen.text(f"Karen {round(bro.karen)}%")
        karen.color(RED if bro.karen >= 80 else AMBER)
        bar_x, bar_w = left + 0.06, 0.62
        self.frame((bar_x, bar_x + bar_w, -0.075, -0.05), color=PANEL, border=None)
        fill = bar_w * clamp(bro.karen / 100, 0, 1)
        self.frame((bar_x, bar_x + max(0.001, fill), -0.075, -0.05), color=RED, border=None)
        throttle = self.ui.get("throttle")
        throttle.text("Throttle [HELD]" if self._held else "Throttle")
        throttle.color(GREEN if self._held else GREEN_2)
