from __future__ import annotations

from panda3d.core import Plane, Point3, TextNode, TransparencyAttrib, Vec3, Vec4

from library.core.assets import assets
from library.core.constants import (
    DIM, DONGLE_ACHIEVEMENT, DONGLE_CAMERA, DONGLE_DRAG_Y, DONGLE_GHOST_ALPHA,
    DONGLE_GHOST_MIN, DONGLE_OK, DONGLE_PARTS, DONGLE_SCATTER, DONGLE_SNAP_DIST,
    DONGLE_TRAY_Y, GREEN, GREEN_2, PANEL, TEXT, VIOLET,
)
from library.game.geometry import make_box
from library.stages.hud import Hud
from library.stages.picker import Picker

_SEAT_FLASH = 0.45  # seconds a part glows after it seats


class DongleStage(Hud):
    """The Bench Wizard's *other* challenge -- Make Dongles. The model
    (``dongle.glb``) is the finished article, so each part's natural spot IS its home:
    we group the nodes by name prefix, scatter the loose parts (OBD port, blue IC, green
    IC, diode) onto the bench, and the player grabs and drags each onto its glowing
    socket on the PCB. Seat all four -> ``Game.grant_god(DONGLE_ACHIEVEMENT)`` (the same
    god status + payout as the bench Trial, a different trophy), then back to the hub.

    Drag is real: a left-press picks the part under the cursor, the part floats toward
    the camera and follows a board-plane projection of the mouse, and the release seats
    it (if close enough to home) or drops it back onto the bench."""

    music_key = "unlock"

    def __init__(self, app, game, on_done):
        super().__init__(app, "dongle")
        self.game = game
        self.on_done = on_done
        self.scene = app.render.attachNewNode("scene-dongle")
        self.board_root = None
        self.picker = None
        self.parts: dict[str, dict] = {}   # id -> {pivot, home, scatter, tint, placed, flash}
        self.sockets: dict[str, tuple] = {}  # id -> (ghost NodePath, label NodePath)
        self.dragging = None               # id of the part following the cursor
        self.won = False

    # -- stage protocol ----------------------------------------------------
    def enter(self):
        self._set_camera()
        self._build_board()
        self.draw()
        self.accept("mouse1-up", self._drop)  # release seats / drops the grabbed part

    def exit(self):
        self._clear_board()
        self.scene.removeNode()
        self.destroy()  # Hud.destroy() also ignoreAll()s the mouse handlers

    def render(self, dt):
        self._drag_follow()
        self._decay_seats(dt)
        self.ui.render(dt)  # 2D: Abort/Continue click flash + visibility

    def _set_camera(self):
        if self.app.camLens:
            self.app.camLens.setFov(DONGLE_CAMERA["fov"])
        self.app.camera.setPos(*DONGLE_CAMERA["pos"])
        self.app.camera.lookAt(*DONGLE_CAMERA["look_at"])

    # -- 3D board ----------------------------------------------------------
    def _build_board(self):
        """Load the dongle, split it into the fixed PCB + four draggable parts (each
        grouped under a pivot at its centroid), drop a glowing socket where each part
        belongs, then scatter the loose parts onto the bench."""
        self.picker = Picker(self.app)
        self.board_root = self.scene.attachNewNode("dongle-board")  # at the origin, so its frame == world
        model = assets.load_model(assets.ModelType.MISC, "dongle")
        model.reparentTo(self.board_root)
        for cid, prefix, label, tint in DONGLE_PARTS:
            nodes = [n for n in model.getChildren() if n.getName().startswith(prefix)]
            low, high = self._combined_bounds(nodes)
            home = (low + high) * 0.5
            pivot = self.board_root.attachNewNode(f"part-{cid}")
            pivot.setPos(home)
            for node in nodes:
                node.wrtReparentTo(pivot)   # keep world pos, so the dongle still looks assembled
            self.picker.register(pivot, cid, lambda c=cid: self._grab(c))
            self._make_socket(cid, home, high - low, tint, label)
            self.parts[cid] = {"pivot": pivot, "home": Point3(home), "tint": tint,
                               "scatter": DONGLE_SCATTER[cid], "placed": False, "flash": 0.0}
        for part in self.parts.values():       # scatter AFTER all are built
            sx, sz = part["scatter"]
            part["pivot"].setPos(sx, DONGLE_TRAY_Y, sz)

    def _make_socket(self, cid, home, size, tint, label):
        """A translucent footprint on the board + a floating label marking where ``cid``
        goes. Removed once the part seats."""
        sx = max(DONGLE_GHOST_MIN, size.getX())
        sz = max(DONGLE_GHOST_MIN, size.getZ())
        ghost = make_box(f"socket-{cid}", sx, 0.05, sz, Vec4(tint.getX(), tint.getY(), tint.getZ(), DONGLE_GHOST_ALPHA))
        ghost.reparentTo(self.board_root)
        ghost.setPos(home.getX(), 0.1, home.getZ())
        ghost.setLightOff()
        ghost.setTransparency(TransparencyAttrib.MAlpha)
        tn = TextNode(f"socket-lbl-{cid}")
        tn.setText(label)
        tn.setAlign(TextNode.ACenter)
        tn.setTextColor(Vec4(tint))
        if self.font:
            tn.setFont(self.font)
        lbl = self.board_root.attachNewNode(tn)
        lbl.setScale(0.32)
        lbl.setPos(home.getX(), 0.2, home.getZ())
        lbl.setBillboardPointEye()
        lbl.setLightOff()
        self.sockets[cid] = (ghost, lbl)

    def _combined_bounds(self, nodes):
        low = Point3(1e9, 1e9, 1e9)
        high = Point3(-1e9, -1e9, -1e9)
        for node in nodes:
            bounds = node.getTightBounds(self.board_root)
            if not bounds:
                continue
            lo, hi = bounds
            low.set(min(low.x, lo.x), min(low.y, lo.y), min(low.z, lo.z))
            high.set(max(high.x, hi.x), max(high.y, hi.y), max(high.z, hi.z))
        return low, high

    def _clear_board(self):
        if self.picker is not None:
            self.picker.destroy()
            self.picker = None
        if self.board_root is not None:
            self.board_root.removeNode()
            self.board_root = None
        self.parts = {}
        self.sockets = {}
        self.dragging = None

    # -- drag & drop -------------------------------------------------------
    def _grab(self, cid):
        part = self.parts.get(cid)
        if self.won or part is None or part["placed"] or self.dragging is not None:
            return
        self.dragging = cid
        part["pivot"].setY(DONGLE_DRAG_Y)  # lift toward the camera; render tracks the cursor

    def _drag_follow(self):
        if self.dragging is None:
            return
        hit = self._cursor_on_plane(DONGLE_DRAG_Y)
        if hit is not None:
            self.parts[self.dragging]["pivot"].setPos(hit.getX(), DONGLE_DRAG_Y, hit.getZ())

    def _drop(self):
        if self.dragging is None:
            return
        cid, self.dragging = self.dragging, None
        part = self.parts[cid]
        pivot, home = part["pivot"], part["home"]
        if (Vec3(pivot.getX() - home.getX(), 0, pivot.getZ() - home.getZ())).length() <= DONGLE_SNAP_DIST:
            self._seat(cid)
        else:
            sx, sz = part["scatter"]
            pivot.setPos(sx, DONGLE_TRAY_Y, sz)  # missed -- back to the bench

    def _seat(self, cid):
        part = self.parts[cid]
        part["pivot"].setPos(part["home"])
        part["placed"] = True
        part["flash"] = _SEAT_FLASH
        ghost, lbl = self.sockets[cid]
        ghost.hide()
        lbl.hide()
        self._sync_progress()
        if all(p["placed"] for p in self.parts.values()) and not self.won:
            self._win()

    def _decay_seats(self, dt):
        for part in self.parts.values():
            if part["flash"] > 0.0:
                part["flash"] -= dt
                if part["flash"] <= 0.0:
                    part["pivot"].clearColorScale()
                else:
                    part["pivot"].setColorScale(Vec4(DONGLE_OK))

    def _cursor_on_plane(self, y):
        """World point where the camera-through-cursor ray meets the horizontal plane at
        height ``y`` (board_root is unrotated at the origin, so world == board frame)."""
        watcher = self.app.mouseWatcherNode
        if watcher is None or not watcher.hasMouse() or self.app.camLens is None:
            return None
        mouse = watcher.getMouse()
        near, far = Point3(), Point3()
        self.app.camLens.extrude(mouse, near, far)
        near_w = self.app.render.getRelativePoint(self.app.camera, near)
        far_w = self.app.render.getRelativePoint(self.app.camera, far)
        hit = Point3()
        if Plane(Vec3(0, 1, 0), Point3(0, y, 0)).intersectsLine(hit, near_w, far_w):
            return hit
        return None

    # -- 2D overlay --------------------------------------------------------
    def draw(self):
        self.ui.clear()
        left, right = self.bounds()
        self.ui.add_frame("hdr-bg", frame_size=(left, right, 0.74, 0.94), pos=(0, 0, 0.84), color=PANEL, border=None)
        self.ui.add_image("hdr-av", "avatar", (left + 0.12, 0, 0.84), 0.06, color_scale=VIOLET)
        self.ui.add_text("hdr-title", "BUILD THE DONGLE", (left + 0.22, 0, 0.85), 0.046, VIOLET)
        self.ui.add_text("hdr-sub", "Grab each part and drag it onto its glowing socket.", (left + 0.22, 0, 0.79), 0.026, DIM)
        self.ui.add_button("abort", "Abort", (right - 0.12, 0, 0.84), (0.16, 0.09), self.on_done, True, PANEL, 0.034)
        self.ui.add_text("progress", "", (0, 0, -0.88), 0.032, TEXT, align=TextNode.ACenter)
        self._sync_progress()

    def _sync_progress(self):
        placed = sum(1 for p in self.parts.values() if p["placed"])
        text = self.ui.get("progress")
        if text is not None:
            text.text(f"parts seated: {placed}/{len(self.parts)}")

    def _win(self):
        self.won = True
        self.dragging = None
        self.game.grant_god(DONGLE_ACHIEVEMENT)
        from library.core.constants import GOD_PAYOUT, PANEL_DARK
        self.ui.add_frame("win-bg", frame_size=(-2.0, 2.0, -1.0, 1.0), color=PANEL_DARK, border=None)
        self.ui.add_text("win-title", "DONGLE COMPLETE", (0, 0, 0.34), 0.075, GREEN, align=TextNode.ACenter)
        self.ui.add_text("win-1", "The Wizard turns it over, nods once. You're a CERTIFIED PLUG.",
                         (0, 0, 0.20), 0.036, VIOLET, align=TextNode.ACenter, wordwrap=40)
        self.ui.add_text("win-2", f"+${GOD_PAYOUT:,} and god status.", (0, 0, 0.10), 0.040, GREEN, align=TextNode.ACenter)
        self.ui.add_button("continue", "Continue", (0, 0, -0.12), (0.5, 0.14), self.on_done, True, GREEN_2, 0.05)
        self.ui.lift()
