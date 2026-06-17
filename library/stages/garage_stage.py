from __future__ import annotations

from direct.task import Task
from panda3d.core import ClockObject, TextNode

from library.core import assets
from library.core.constants import DIM, GREEN, MODES, PANEL, TEXT
from library.stages.hud import Hud
from library.stages.simon_panel import SimonPanel


class GarageStage(Hud):
    """The home hub: the GTI slowly turning in the bay with a row of task buttons.
    Picking one calls ``on_pick(key)``; this is where Back returns you."""

    def __init__(self, app, game, on_pick):
        super().__init__(app, "garage-hub")
        self.game = game
        self.on_pick = on_pick
        self.scene = app.render.attachNewNode("scene-garage")
        self.car = None
        self.simon = None
        self._tick_name = f"garage-spin-{id(self)}"

    def enter(self):
        from library.core.constants import GARAGE_CAMERA

        if self.app.camLens:
            self.app.camLens.setFov(GARAGE_CAMERA.get("fov", 42))
        self.app.camera.setPos(*GARAGE_CAMERA["pos"])
        self.app.camera.lookAt(*GARAGE_CAMERA["look_at"])
        assets.load_model("ground").reparentTo(self.scene)
        self.car = assets.load_model("car")
        self.car.reparentTo(self.scene)
        self.simon = SimonPanel(self.app, self.game, "")
        self.draw()
        self.app.taskMgr.add(self._spin, self._tick_name)

    def exit(self):
        self.app.taskMgr.remove(self._tick_name)
        if self.simon:
            self.simon.destroy()
        self.scene.removeNode()
        self.destroy()

    def _spin(self, task):
        if self.car:
            self.car.setH(ClockObject.getGlobalClock().getFrameTime() * 14.0)
        return Task.cont

    def draw(self):
        self.clear()
        left, right = self.bounds()
        self.draw_header(self.game)
        self.label("GARAGE", (0, 0, 0.66), 0.06, GREEN, align=TextNode.ACenter)
        self.label("Pick a task. Ask Simon if you're stuck.", (0, 0, 0.58), 0.034, DIM, align=TextNode.ACenter)
        gap = 0.04
        count = len(MODES)
        width = (right - left - gap * (count - 1)) / count
        for index, (key, title, blurb) in enumerate(MODES):
            x = left + width / 2 + index * (width + gap)
            self._task_button(key, title, blurb, x, width)

    def _task_button(self, key, title, blurb, x, width):
        button = self.button(title, (x, 0, -0.60), (width, 0.20), lambda k=key: self.on_pick(k), color=PANEL, text_scale=0.05)
        self.label(blurb, (x, 0, -0.74), 0.026, DIM, align=TextNode.ACenter, wordwrap=int(width / 0.03))
        # green accent strip along the top of the card
        self.frame((x - width / 2, x + width / 2, -0.515, -0.50), color=GREEN, border=None)
