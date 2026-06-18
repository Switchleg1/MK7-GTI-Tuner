from __future__ import annotations

import random
import time

from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, TransparencyAttrib, Vec3, Vec4

from library.core import assets
from library.core.constants import BLUE, GARAGE_CAMERA, TASK_CAMERAS, UI_REFRESH_SECONDS
from library.game.geometry import make_box
from library.stages.hud import Hud


class TaskBase(Hud):
    """Base for a single full-screen task (BENCH/MAPS/DYNO/STREET/RACE/SHOP).

    Owns its own 2D UI (via Hud) and a 3D scene node, plus a Back button to the
    garage hub. The shared Simon/Discord panels live on the app, not here. Subclasses
    set ``title``/``key``/``live`` and override ``build_scene``/``build_ui``/
    ``bind_keys``/``tick``. The app's render loop calls ``render(dt)`` each frame;
    ``exit()`` tears it all down so nothing renders over the next stage."""

    title = "TASK"
    key = ""
    live = False  # True for animated tasks that redraw on a timer

    def __init__(self, app, game, on_back):
        super().__init__(app, f"task-{self.key}")
        self.game = game
        self.on_back = on_back
        self.scene = app.render.attachNewNode(f"scene-{self.key}")
        self.dirty = True
        self.last_draw = 0.0
        self.flames = []
        self.reactions = []

    # -- lifecycle ---------------------------------------------------------
    def enter(self):
        self.set_camera()
        self.build_scene()
        self.redraw()
        self.bind_keys()

    def exit(self):
        audio = getattr(self.app, "audio", None)
        if audio:
            audio.silence()  # stop the engine note from droning into the next stage
        self.scene.removeNode()
        self.destroy()

    def set_camera(self):
        cam = TASK_CAMERAS.get(self.key, GARAGE_CAMERA)
        if self.app.camLens:
            self.app.camLens.setFov(cam.get("fov", 45))
        self.app.camera.setPos(*cam["pos"])
        self.app.camera.lookAt(*cam["look_at"])

    # -- overridable hooks -------------------------------------------------
    def build_scene(self):
        self.add_garage_scene()

    def build_ui(self, left, right):
        pass

    def bind_keys(self):
        pass

    def tick(self, dt):
        pass

    # -- helpers -----------------------------------------------------------
    def add_garage_scene(self):
        assets.load_model("ground").reparentTo(self.scene)
        car = assets.load_model("car")
        car.reparentTo(self.scene)
        return car

    def bind(self, fn, *args):
        """Wrap a model action so the UI redraws after it runs."""
        def run():
            fn(*args)
            self.dirty = True
        return run

    # -- exhaust flames (shared by STREET pops + RACE shifts) -------------
    def spawn_flames(self, anchor, count=5):
        base = anchor.getPos(self.app.render)
        for _ in range(count):
            node = make_box("flame", 0.18, 0.18, 0.18, Vec4(1.0, random.uniform(0.35, 0.9), 0.08, 1))
            node.reparentTo(self.scene)
            node.setPos(base.x + random.uniform(-0.30, 0.30), base.y - 2.4, base.z + 0.32)
            self.flames.append({"node": node, "life": random.uniform(0.45, 0.85)})

    def update_flames(self, dt):
        for flame in list(self.flames):
            flame["life"] -= dt
            flame["node"].setScale(max(0.02, flame["life"] * 0.5))
            flame["node"].setPos(flame["node"].getPos() + Vec3(0, -dt * 4, dt * 1.4))
            if flame["life"] <= 0:
                flame["node"].removeNode()
                self.flames.remove(flame)

    # -- floating emoji reactions (crowd hype / Karen rage popups) ---------
    def spawn_reaction(self, key, x, z, scale, rise, life):
        """A 2D emoji that floats up and fades. Parented to the screen root (not
        tracked in self.nodes) so it survives UI redraws and is freed on exit."""
        node = OnscreenImage(parent=self.root, image=assets.image_path(key), pos=(x, 0, z), scale=scale)
        node.setTransparency(TransparencyAttrib.MAlpha)
        self.reactions.append({"node": node, "life": life, "max": life, "rise": rise})

    def update_reactions(self, dt):
        for r in list(self.reactions):
            r["life"] -= dt
            node = r["node"]
            node.setZ(node.getZ() + r["rise"] * dt)
            node.setColorScale(1, 1, 1, max(0.0, min(1.0, r["life"] / r["max"] * 1.5)))
            if r["life"] <= 0:
                node.removeNode()
                self.reactions.remove(r)

    def redraw(self):
        self.clear()
        left, right = self.bounds()
        self.draw_header(self.game)
        self.label(self.title, (0, 0, 0.64), 0.052, BLUE, align=TextNode.ACenter)
        self.back_button(self.on_back)
        self.build_ui(left, right)

    def panel_pair(self, left, right):
        gap = 0.04
        mid = (left + right) / 2
        boxes = ((left, mid - gap / 2, -0.62, 0.48), (mid + gap / 2, right, -0.62, 0.48))
        for box in boxes:
            self.frame(box, (0, 0, 0), border=None)
        return boxes

    def kind_color(self, kind):
        from library.core.constants import AMBER, BLUE as _B, DIM, GREEN, RED, VIOLET
        return {"ok": GREEN, "info": _B, "warn": AMBER, "err": RED, "violet": VIOLET}.get(kind, DIM)

    def render(self, dt):
        """Called every frame by the app's render loop: advance flames/reactions,
        run the subclass ``tick``, and redraw when dirty (or on the live timer)."""
        self.update_flames(dt)
        self.update_reactions(dt)
        self.tick(dt)
        now = time.perf_counter()
        if self.dirty or (self.live and now - self.last_draw > UI_REFRESH_SECONDS):
            self.redraw()
            self.dirty = False
            self.last_draw = now
