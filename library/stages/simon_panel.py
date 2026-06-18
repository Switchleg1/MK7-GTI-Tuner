from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import DIM, LINE, PANEL_DARK, ROAST, TIP, VIOLET
from library.game.simos import build_context, select_insight
from library.stages.hud import Hud


class SimonPanel(Hud):
    """The reusable Ask-Simon widget: a pill button plus a roast/tip popup.

    Owns its own node tree so it sits above a screen's UI and toggles open/closed
    without that screen redrawing. ``tab`` feeds Simon's context rules."""

    def __init__(self, app, game, tab: str = ""):
        super().__init__(app, "simon-panel")
        self.game = game
        self.tab = tab
        self.open = False
        self.current = None
        self.draw()

    def ask(self):
        self.current = select_insight(build_context(self.game, self.tab), self.game.simon_tick)
        self.game.simon_tick += 1
        self.open = True
        self.draw()

    def close(self):
        self.open = False
        self.draw()

    def set_context(self, key: str):
        """Re-point Simon at the new stage (feeds his rules) and close any popup."""
        self.tab = key
        self.open = False
        self.current = None
        self.draw()

    def draw(self):
        self.clear()
        right = self.bounds()[1]
        self.pill("Ask Simon", (right - 0.34, 0, -0.85), self.ask, icon="simon")
        if not self.open or not self.current:
            return
        pw, ph = 1.32, 1.05
        cx, cz = right - 0.05 - pw / 2, 0.06
        left = cx - pw / 2 + 0.10
        right_in = cx + pw / 2 - 0.10
        top, bottom = cz + ph / 2, cz - ph / 2
        self.image("simon_panel", (cx, 0, cz), (pw / 2, 1, ph / 2))
        self.image("simon", (left + 0.09, 0, top - 0.13), 0.085)
        self.label("SIMON", (left + 0.22, 0, top - 0.10), 0.060, VIOLET)
        self.label("master tuner . zero chill", (left + 0.22, 0, top - 0.18), 0.030, DIM)
        self.button("X", (right_in, 0, top - 0.10), (0.10, 0.10), self.close, True, PANEL_DARK, 0.05)
        self.label(self.current["roast"], (left, 0, cz + 0.12), 0.043, ROAST, wordwrap=23)
        self.frame((left, right_in, cz - 0.14, cz - 0.135), (0, 0, 0), LINE, None)
        self.image("tip_bulb", (left + 0.04, 0, bottom + 0.21), 0.038)
        self.label(self.current["tip"], (left + 0.12, 0, bottom + 0.23), 0.036, TIP, wordwrap=25)
