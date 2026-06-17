from __future__ import annotations

import time

from panda3d.core import TextNode

from library.core import assets
from library.core.constants import AMBER, AUDIO, BLUE, DIM, FINAL_DRIVE, GEAR_RATIOS, GREEN, GREEN_2, RED, TEXT, TIRE_CIRC, TRACK_M
from library.core.utils import clamp
from library.stages.task_base import TaskBase

STRIP_LENGTH = 14.0  # scene units the quarter mile maps onto (keeps both cars in frame)


class RaceTask(TaskBase):
    """Quarter-mile vs the skreets ladder: stage, launch on green, shift up.

    The race model lives on ``Game`` (countdown, physics, payout). This task draws it:
    a live countdown -> GO! status, the running gap, and the win/loss + payout, plus
    a dynamic Launch/Shift prompt. Status text is refreshed every frame in ``tick`` so
    the countdown and distances stay smooth between the periodic full redraws."""

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
            player = self.game.race["p"]
            self._place(self.player_car, -2.2, player["d"])
            self._place(self.rival_car, 2.2, self.game.race["r"]["d"])
            gear = min(max(player["gear"], 1), len(GEAR_RATIOS))
            rpm = clamp(player["v"] / TIRE_CIRC * GEAR_RATIOS[gear - 1] * FINAL_DRIVE * 60, 850, 7200)
            load = AUDIO["pull_load"] if player["launched"] and not player["done"] else 0.2
            self.app.audio.set_engine(rpm, load)
        else:
            self.app.audio.idle(900)
        # Refresh the status/hint text every frame so the countdown + gap stay smooth.
        if getattr(self, "status", None):
            text, _, hint = self._race_status()
            self.status["text"] = text
            self.hint["text"] = hint

    def bind_keys(self):
        self.accept("space", self.do_key)

    def do_key(self):
        event = self.game.race_key()
        if event in ("launch", "shift"):
            self.spawn_flames(self.player_car, 2)
        if event == "shift":  # bang + a quick crackle on each upshift
            self.app.audio.bang()
            self.app.audio.overrun(28, 0.3)
        self.dirty = True  # flip the Launch button to Shift, etc.

    def _race_status(self):
        """Return (status text, color, hint) for the current race phase."""
        race = self.game.race
        if not race:
            return "Pick a rival, then Stage & Race.", DIM, "SPACE launches on GREEN, then shifts gears."
        player, rival = race["p"], race["r"]
        now = time.perf_counter()
        if race["active"]:
            if now < race["green_at"]:
                if not player["launched"]:
                    return f"STAGED - get ready  {race['green_at'] - now:0.1f}s", AMBER, "Hands on the wheel. Wait for GREEN."
                return "WAIT FOR GREEN!", RED, "Pre-loaded - you'll roll the moment it goes green."
            if not player["launched"]:
                return "GREEN - GO!", GREEN, "Press SPACE to LAUNCH now!"
            return f"GO!   You {player['d']:.0f} m   /   Rival {rival['d']:.0f} m", GREEN, f"SPACE to shift  (gear {player['gear']})"
        # finished
        won = player["et"] < rival["et"] if rival["et"] else True
        foe = self.game.rivals[self.game.bro.selected_rival]
        if won:
            return (f"WIN!  {player['et']:.2f}s @ {player['trap']:.0f} mph", GREEN,
                    f"+${foe.purse} banked. Rival ran {rival['et']:.2f}s. Stage to run it again.")
        return (f"LOSS  {player['et']:.2f}s @ {player['trap']:.0f} mph", RED,
                f"Rival ran {rival['et']:.2f}s. Tune up or buy parts, then run it back.")

    def build_ui(self, left, right):
        # No full-screen panels here: the 3D cars race up the centre of the screen,
        # so the UI hugs the edges (status top-left, ladder top-right, buttons low)
        # and leaves the middle clear instead of covering the strip.
        game = self.game
        text, color, hint = self._race_status()
        self.status = self.label(text, (left + 0.05, 0, 0.54), 0.052, color, wordwrap=20)
        self.hint = self.label(hint, (left + 0.05, 0, 0.43), 0.030, DIM, wordwrap=28)
        staged = game.race_active()
        launching = (not staged) or not game.race["p"]["launched"]
        self.button("Stage & Race", (-0.34, 0, -0.80), (0.42, 0.10),
                    self.bind(game.start_race), game.car.flashed and not staged, GREEN_2)
        self.button(("Launch" if launching else "Shift") + " (SPACE)", (0.34, 0, -0.80),
                    (0.42, 0.10), self.do_key, staged)
        self.label("SKREETS LADDER", (right - 0.05, 0, 0.54), 0.032, BLUE, align=TextNode.ARight)
        for index, rival in enumerate(game.rivals):
            sel = index == game.bro.selected_rival
            self.button(f"{rival.name}  ${rival.purse}", (right - 0.42, 0, 0.44 - index * 0.095), (0.74, 0.078),
                        self.bind(game.select_rival, index), index <= game.bro.unlocked_rival,
                        GREEN_2 if sel else None, 0.030)
