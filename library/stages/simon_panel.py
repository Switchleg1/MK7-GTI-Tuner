from __future__ import annotations

from library.core.constants import DIM, LINE, PANEL_DARK, ROAST, TIP, VIOLET
from library.game.simos import build_context, select_insight
from library.stages.hud import Hud
from library.core.ui.ui_object_controller import UIObjectController


class SimonPanel(Hud):
    """The reusable Ask-Simon widget: a roast/tip popup (the trigger is a game-level
    chrome button that calls ``ask()``).

    Owns its own node tree so it sits above a screen's UI and toggles open/closed
    without that screen redrawing. All UI is managed objects on ``self.ui``, rebuilt on
    each ``draw()``. ``tab`` feeds Simon's context rules."""

    def __init__(self, app, game, tab: str = ""):
        super().__init__(app, "simon-panel")
        self.game       = game
        self.tab        = tab
        self.open       = False
        self.current    = None
        self.show       = True
        self.ui         = UIObjectController(app, self.root.attachNewNode("simon-ui"))


    def ask(self):
        self.current = select_insight(build_context(self.game, self.tab), self.game.simon_tick)
        self.game.simon_tick += 1
        self._set_opened(True)


    def close(self):
        self._set_opened(False)


    def set_context(self, key: str):
        """Re-point Simon at the new stage (feeds his rules) and close any popup."""
        self.tab = key
        self._set_opened(False)


    def render(self, dt):
        self.ui.render(dt)  # popup objects: visibility + the X button's click flash
        
        
    def _set_opened(self, value):
        if value == True:
            self._create_window(self.open == False)
        else:
            self._clear_window()
        self.open = value
                

    def _create_window(self, create=True):
        if not self.current:
            return
        
        right = self.bounds()[1]
        pw, ph = 1.32, 1.05
        cx, cz = right - 0.05 - pw / 2, 0.06
        left = cx - pw / 2 + 0.10
        right_in = cx + pw / 2 - 0.10
        top, bottom = cz + ph / 2, cz - ph / 2
        
        if create:
            self.ui.add_image("panel", "simon_panel", (cx, 0, cz), (pw / 2, 1, ph / 2))
            self.ui.add_image("avatar", "simon", (left + 0.09, 0, top - 0.13), 0.085)
            self.ui.add_text("name", "SIMON", (left + 0.22, 0, top - 0.10), 0.060, VIOLET)
            self.ui.add_text("subtitle", "master tuner . zero chill", (left + 0.22, 0, top - 0.18), 0.030, DIM)
            self.ui.add_button("close", "X", (right_in, 0, top - 0.10), (0.10, 0.10), self.close, True, PANEL_DARK, 0.05)
            self.ui.add_text("roast", self.current["roast"], (left, 0, cz + 0.12), 0.043, ROAST, wordwrap=23)
            self.ui.add_frame("divider", frame_size=(left, right_in, cz - 0.14, cz - 0.135), color=LINE, border=None)
            self.ui.add_image("bulb", "tip_bulb", (left + 0.04, 0, bottom + 0.21), 0.038)
            self.ui.add_text("tip", self.current["tip"], (left + 0.12, 0, bottom + 0.23), 0.036, TIP, wordwrap=25)
        else:
            self.ui.get("roast").text(self.current["roast"])
            self.ui.get("tip").text(self.current["tip"])
            

    def _clear_window(self):
        self.current = None
        self.ui.clear()