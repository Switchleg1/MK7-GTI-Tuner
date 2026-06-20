from __future__ import annotations

from panda3d.core import ClockObject, TextNode

import library.core.assets as assets
from library.core.constants import DIM, GREEN, MODES, PANEL, TEXT, VIOLET
from library.stages.hud import Hud
from library.stages.ui_object_controller import UIObjectController


class GarageStage(Hud):
    """The home hub: the GTI slowly turning in the bay with a row of task buttons.
    Picking one calls ``on_pick(key)``; this is where Back returns you. The shared
    Simon/Discord panels live on the app, so the hub shows them too."""

    music_key = "garage"

    def __init__(self, app, game, on_pick, on_summon=None, on_menu=None):
        super().__init__(app, "garage-hub")
        self.game = game
        self.on_pick = on_pick
        self.on_summon = on_summon  # launch the Bench Wizard Trial when summoned
        self.on_menu = on_menu      # open the pause menu (save / load / options)
        self.scene = app.render.attachNewNode("scene-garage")
        self.car = None
        # The hub's own UI objects (task cards in the "garage" style + MENU + the DM).
        self.ui = UIObjectController(app, self.root.attachNewNode("garage-ui"))

    def enter(self):
        from library.core.constants import GARAGE_CAMERA

        if self.app.camLens:
            self.app.camLens.setFov(GARAGE_CAMERA.get("fov", 42))
        self.app.camera.setPos(*GARAGE_CAMERA["pos"])
        self.app.camera.lookAt(*GARAGE_CAMERA["look_at"])
        assets.load_model(assets.ModelType.GEOMETRY, "ground").reparentTo(self.scene)
        self.car = assets.load_model(assets.ModelType.CAR, "mk7_gti")
        self.car.reparentTo(self.scene)
        self.draw()

    def exit(self):
        self.ui.destroy()
        self.scene.removeNode()
        self.destroy()

    def render(self, dt):
        if self.car:
            self.car.setH(ClockObject.getGlobalClock().getFrameTime() * 14.0)
        self.ui.render(dt)  # garage buttons: visibility + click flash

    def draw(self):
        self.clear()
        self.ui.clear()
        left, right = self.bounds()
        self.draw_header(self.game)
        if self.on_menu:
            self.ui.add_button("menu", "MENU", (left + 0.21, 0, 0.66), (0.34, 0.09), self.on_menu, True, PANEL, 0.04)
        self.label("GARAGE", (0, 0, 0.66), 0.06, GREEN, align=TextNode.ACenter)
        self.label("Pick a task. Ask Simon if you're stuck.", (0, 0, 0.58), 0.034, DIM, align=TextNode.ACenter)
        if self.on_summon and self.game.wizard_available():
            self.ui.add_button("wizard", "> A MYSTERIOUS DM - ANSWER IT <", (0, 0, 0.46), (1.4, 0.10), self.on_summon, True, VIOLET, 0.036)
        gap = 0.04
        count = len(MODES)
        width = (right - left - gap * (count - 1)) / count
        for index, (key, title, blurb) in enumerate(MODES):
            x = left + width / 2 + index * (width + gap)
            self._task_button(key, title, blurb, x, width)
        self.ui.lift()  # keep the buttons above the header/labels

    def _task_button(self, key, title, blurb, x, width):
        # The "garage" style draws the green top accent strip itself.
        self.ui.add_button(f"task-{key}", title, (x, 0, -0.60), (width, 0.20),
                           lambda k=key: self.on_pick(k), True, PANEL, 0.05, style="garage")
        self.label(blurb, (x, 0, -0.74), 0.026, DIM, align=TextNode.ACenter, wordwrap=int(width / 0.03))
