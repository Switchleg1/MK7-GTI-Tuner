from __future__ import annotations

import random
import time

from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import MouseButton, Point3, TextNode, TransparencyAttrib, Vec3, Vec4

from library.core.assets import assets
from library.core.constants import (
    BLUE,
    DIM,
    GARAGE_CAMERA,
    GREEN,
    PANEL,
    RED,
    TASK_CAMERAS,
    TEXT,
    UI_REFRESH_SECONDS,
    WHEEL_PREFIX,
    WHEEL_STATIC,
)
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
        self.allow_back = True
        # Task UI objects are built once on enter and then only updated in place, so
        # redraws do not destroy widgets, drop clicks, or churn labels.

    # -- lifecycle ---------------------------------------------------------
    def enter(self):
        self.set_camera()
        self.build_scene()
        self._build_header_objects()
        self.build_ui()  # create this task's UI objects once
        self.redraw()
        self.bind_keys()

    def exit(self):
        audio = getattr(self.app, "audio", None)
        if audio:
            audio.silence()  # stop the engine note from droning into the next stage
        back = self.game.ui.get("back") if self.game.ui is not None else None
        if back is not None:
            back.is_visible(False)  # hide the shared Back button leaving the task
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

    def build_ui(self):
        """Create this task's persistent UI objects ONCE (on enter) via
        ``self.ui.add_text(key, ...)`` / ``self.ui.add_button(key, ...)`` /
        ``self.ui.add_frame(key, ...)`` / ``self.ui.add_image(key, ...)``. After this,
        only change their properties (``text``/``color``/``enabled``/``is_visible`` /
        ``frame_size``), typically from ``update_ui`` or ``tick``."""

    def update_ui(self, left, right):
        pass

    def bind_keys(self):
        pass

    def tick(self, dt):
        pass

    # -- helpers -----------------------------------------------------------
    def add_garage_scene(self):
        assets.load_model(assets.ModelType.GEOMETRY, "ground").reparentTo(self.scene)
        car = assets.load_model(assets.ModelType.CAR, "mk7_gti")
        car.reparentTo(self.scene)
        return car

    def prepare_wheels(self, car):
        """Return per-corner pivots to rotate so the wheels spin in place about their
        axle (X), for any of the detailed car .glb models.

        Wheel meshes pivot at the *model* origin, so spinning them directly flings them
        across the scene. We gather the spinnable wheel geometry (the geom leaves under
        any ``WHEEL_PREFIX`` node, brake calipers dropped -- they don't turn), cluster
        it into the four corners by car-space position, and wrap each corner in a pivot
        at that wheel's centre, reparenting the geometry under it (preserving world
        position). Returns the four pivots to rotate (``setP``).

        Works regardless of how the model groups its wheels -- ``mk7_gti.glb`` uses flat
        per-corner ``w:`` siblings, while ``civic_type_r.glb`` lumps all four into one
        ``w:wheels`` group; position clustering handles both. The caliper label can sit
        on a leaf *or* an ancestor (e.g. the named ``w:Calliper…`` node above a generic
        mesh), so ``_wheel_static`` checks the whole chain. Falls back to the old
        procedural ``tire_``/``rim_`` nodes if there's no ``WHEEL_PREFIX`` geometry."""
        roots = [n for n in car.findAllMatches("**/" + WHEEL_PREFIX + "*")
                 if not n.getParent().getName().startswith(WHEEL_PREFIX)]
        leaves, seen = [], set()
        for root in roots:
            geoms = list(root.findAllMatches("**/+GeomNode"))
            if root.node().isGeomNode():
                geoms.append(root)
            for geom in geoms:
                key = geom.getKey()
                if key in seen or self._wheel_static(geom, root):
                    seen.add(key)
                    continue
                seen.add(key)
                leaves.append(geom)
        if not leaves:
            return list(car.findAllMatches("**/tire_*")) + list(car.findAllMatches("**/rim_*"))
        corners: dict = {}
        for leaf in leaves:
            bounds = leaf.getTightBounds(car)
            if not bounds:
                continue
            center = (bounds[0] + bounds[1]) * 0.5
            corners.setdefault((center.x >= 0, center.y >= 0), []).append((leaf, bounds[0], bounds[1]))
        pivots = []
        for index, group in enumerate(corners.values()):
            lo = Point3(min(b0.x for _, b0, _ in group), min(b0.y for _, b0, _ in group), min(b0.z for _, b0, _ in group))
            hi = Point3(max(b1.x for _, _, b1 in group), max(b1.y for _, _, b1 in group), max(b1.z for _, _, b1 in group))
            pivot = car.attachNewNode(f"wheel-pivot-{index}")
            pivot.setPos((lo + hi) * 0.5)
            for leaf, _, _ in group:
                leaf.wrtReparentTo(pivot)
            pivots.append(pivot)
        return pivots

    @staticmethod
    def _wheel_static(geom, root):
        """True if ``geom`` (or any ancestor up to ``root``) is a brake caliper -- the
        caliper label may live on a named parent above a generically-named mesh."""
        node = geom
        while not node.isEmpty():
            if any(token in node.getName().lower() for token in WHEEL_STATIC):
                return True
            if node == root:
                break
            node = node.getParent()
        return False

    def bind(self, fn, *args):
        """Wrap a model action so the persistent UI resyncs after it runs."""
        def run():
            fn(*args)
            self.dirty = True
        return run

    def _log_result(self, result):
        if result:
            self.game.log(*result)

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
        managed by ``self.ui``) so it survives UI redraws and is freed on exit."""
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
        left, right = self.bounds()
        self.update_ui(left, right)  # sync persistent UI-object props (not create)
        self._sync_header(left, right)
        self._sync_back()            # point the shared (game-level) Back button at this task
        self.ui.lift()

    def _build_header_objects(self):
        left, right = self.bounds()
        self.ui.add_frame("header-frame", frame_size=(left, right, -0.085, 0.085),
                          pos=(0, 0, 0.86), color=PANEL, border=None)
        self.ui.add_text("header-title", "MK7 GTI TUNER", (left + 0.05, 0, 0.89), 0.05, GREEN)
        self.ui.add_text("header-subtitle", "EA888  .  SIMOS18.1  .  POPS & BANGS  .  CAREER",
                         (left + 0.05, 0, 0.835), 0.026, DIM)
        self.ui.add_text("header-cash", "", (right - 0.04, 0, 0.888), 0.033, GREEN, align=TextNode.ARight)
        self.ui.add_text("header-map", "", (right - 0.04, 0, 0.832), 0.027, TEXT, align=TextNode.ARight)
        self.ui.add_text("task-title", self.title, (0, 0, 0.64), 0.052, BLUE, align=TextNode.ACenter)

    def _sync_header(self, left, right):
        self.ui.get("header-frame").frame_size((left, right, -0.085, 0.085))
        self.ui.get("header-title").pos((left + 0.05, 0, 0.89))
        self.ui.get("header-subtitle").pos((left + 0.05, 0, 0.835))
        name = str(self.game.car.active_tune().get("name", "Stock"))[:16]
        self.ui.get("header-cash").pos((right - 0.04, 0, 0.888))
        cash = self.ui.get("header-cash")
        cash.text(f"${round(self.game.bro.cash)}   .   ECU {self.game.car.ecu_status()}")
        cash.color(RED if self.game.bro.is_broke() else GREEN)
        self.ui.get("header-map").pos((right - 0.04, 0, 0.832))
        self.ui.get("header-map").text(
            f"MAP {self.game.car.active_slot + 1} {name}   .   REP {self.game.bro.rep()}")
        self.ui.get("task-title").text(self.title)

    def _sync_back(self):
        """The Back button is a game-level chrome button shared across tasks. Point it at
        this task's on_back and show it only while Back is allowed (the race hides it
        mid-run via allow_back)."""
        back = self.game.ui.get("back") if self.game.ui is not None else None
        if back is not None:
            back.command_fn(self.on_back)
            back.is_visible(self.allow_back)

    def panel_boxes(self, left, right):
        """The two panel-box extents (no drawing) so build_ui can place matching
        persistent frames and controls from the same coordinates."""
        gap = 0.04
        mid = (left + right) / 2
        return ((left, mid - gap / 2, -0.62, 0.48), (mid + gap / 2, right, -0.62, 0.48))

    def kind_color(self, kind):
        from library.core.constants import AMBER, BLUE as _B, DIM, GREEN, RED, VIOLET
        return {"ok": GREEN, "info": _B, "warn": AMBER, "err": RED, "violet": VIOLET}.get(kind, DIM)

    def render(self, dt):
        """Called every frame by the app's render loop: advance flames/reactions,
        run the subclass ``tick``, and redraw when dirty (or on the live timer).

        The redraw now only syncs persistent UI-object values, but we still defer dirty
        updates while the mouse is held so command callbacks cannot race a click."""
        self.update_flames(dt)
        self.update_reactions(dt)
        self.tick(dt)
        self.ui.render(dt)  # advance object visibility + click-flash (cheap; runs even while held)
        if self._mouse_held():
            return
        now = time.perf_counter()
        if self.dirty or (self.live and now - self.last_draw > UI_REFRESH_SECONDS):
            self.redraw()
            self.dirty = False
            self.last_draw = now

    def _mouse_held(self) -> bool:
        """True while the left mouse button is down (so we can defer UI resyncs and
        not drop the click). Safe when there's no mouse watcher (offscreen)."""
        watcher = self.app.mouseWatcherNode
        return watcher is not None and watcher.is_button_down(MouseButton.one())
