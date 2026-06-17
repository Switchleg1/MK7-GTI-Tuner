from __future__ import annotations

import sys

from panda3d.core import AmbientLight, DirectionalLight, Filename, PerspectiveLens, Vec4, WindowProperties

from direct.showbase.ShowBase import ShowBase

from library.core.audio import GameAudio
from library.core.constants import BG, DEFAULT_ASPECT, DEFAULT_HEIGHT, DEFAULT_WIDTH, WINDOW_TITLE
from library.core.panda_config import enable_gltf
from library.game.game import Game
from library.stages.garage_stage import GarageStage
from library.stages.notifications import Notifications
from library.stages.tasks.bench_task import BenchTask
from library.stages.tasks.dyno_task import DynoTask
from library.stages.tasks.maps_task import MapsTask
from library.stages.tasks.race_task import RaceTask
from library.stages.tasks.shop_task import ShopTask
from library.stages.tasks.street_task import StreetTask
from library.stages.unlock_stage import UnlockStage

TASK_CLASSES = {
    "bench": BenchTask,
    "maps": MapsTask,
    "dyno": DynoTask,
    "street": StreetTask,
    "race": RaceTask,
    "shop": ShopTask,
}


class MK7Tuner3D(ShowBase):
    """Thin shell: owns the window/lights, the GameState model, and a single active
    stage. Flow: UnlockStage (cinematic) -> GarageStage (hub) <-> a task at a time."""

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(BG)
        if self.win and hasattr(self.win, "requestProperties"):
            self.win.requestProperties(self.window_properties())
        if self.camLens is None:
            self.camLens = PerspectiveLens()
        self.camLens.setAspectRatio(DEFAULT_ASPECT)
        enable_gltf(self)
        self.setup_lights()
        self.mono_font = self.load_mono_font()
        self.audio = GameAudio(self)
        self.game = Game()
        self.notifications = Notifications(self, self.game)  # session-long toast/Dave overlay
        self.stage = None
        self.accept("escape", sys.exit)
        self.start_unlock()

    # -- setup -------------------------------------------------------------
    def window_properties(self) -> WindowProperties:
        props = WindowProperties()
        props.setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        props.setTitle(WINDOW_TITLE)
        return props

    def setup_lights(self):
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.34, 0.40, 0.45, 1))
        self.render.setLight(self.render.attachNewNode(ambient))
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(0.90, 0.95, 1.0, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-45, -55, 0)
        self.render.setLight(sun_np)

    def load_mono_font(self):
        """Monospace font for the UI; falls back to the default font off-Windows."""
        for path in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"):
            try:
                font = self.loader.loadFont(str(Filename.fromOsSpecific(path)))
            except Exception:  # noqa: BLE001
                font = None
            if font and font.isValid():
                font.setPixelsPerUnit(64)
                return font
        return None

    # -- stage manager -----------------------------------------------------
    def set_stage(self, stage):
        if self.stage is not None:
            self.stage.exit()
        self.stage = stage
        stage.enter()

    def start_unlock(self):
        # UnlockStage self-manages its own cleanup before calling on_complete.
        self.stage = None
        self.unlock = UnlockStage(self, on_complete=self.on_unlocked)

    def on_unlocked(self):
        # Runs once, when the cinematic finishes: the ECU is now flashed/unlocked.
        # Kept OUT of enter_hub so returning to the hub from a task doesn't re-run
        # mark_unlocked() and wipe the player's flashed tune + switch-patch slots.
        self.game.car.mark_unlocked()
        if self.game.unlock("first_flash", "Boot Patched, Baby"):
            self.game.dave("flash")
        self.enter_hub()

    def enter_hub(self):
        self.set_stage(GarageStage(self, self.game, on_pick=self.open_task))

    def open_task(self, key: str):
        self.set_stage(TASK_CLASSES[key](self, self.game, on_back=self.enter_hub))
