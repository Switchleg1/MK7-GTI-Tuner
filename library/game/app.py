from __future__ import annotations

from panda3d.core import (
    AmbientLight, ClockObject, CullBinManager, DirectionalLight, Filename, PerspectiveLens, Vec4, WindowProperties,
)

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from library.core import assets, storage
from library.core.audio import GameAudio
from library.core.config import Config
from library.core.constants import (
    BG, BLUE, DEFAULT_ASPECT, DEFAULT_HEIGHT, DEFAULT_WIDTH, OVERLAY_BIN, OVERLAY_SORT,
    TOAST_SECONDS, VIOLET, WINDOW_TITLE,
)
from library.core.music import MusicPlayer
from library.core.panda_config import enable_gltf
from library.game.game import Game
from library.stages.discord_panel import DiscordPanel
from library.stages.garage_stage import GarageStage
from library.stages.menu_stage import MenuStage
from library.stages.notifications import Notifications
from library.stages.simon_panel import SimonPanel
from library.stages.ui_object_controller import UIObjectController
from library.stages.tasks.bench_task import BenchTask
from library.stages.tasks.dyno_task import DynoTask
from library.stages.tasks.maps_task import MapsTask
from library.stages.tasks.race_task import RaceTask
from library.stages.tasks.shop_task import ShopTask
from library.stages.tasks.street_task import StreetTask
from library.stages.toast import Toast
from library.stages.unlock_stage import UnlockStage
from library.stages.wizard_trial_stage import WizardTrialStage

TASK_CLASSES = {
    "bench": BenchTask,
    "maps": MapsTask,
    "dyno": DynoTask,
    "street": StreetTask,
    "race": RaceTask,
    "shop": ShopTask,
}


class MK7Tuner3D(ShowBase):
    """Thin shell: owns the window/lights, the Game model, a single active stage, and
    the game-level overlays (music + now-playing toast, the achievement/Dave
    notifications). The shared Ask-Simon / Ask-Discord panels are owned by the Game
    (``game.simon_panel`` / ``game.discord_panel``) so a task can toggle them; the app
    still builds them on first hub entry and drives them from the one render loop (see
    ``_render``). Flow: MenuStage (title) -> UnlockStage (cinematic) -> GarageStage
    (hub) <-> a task at a time."""

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(BG)
        if self.win and hasattr(self.win, "requestProperties"):
            self.win.requestProperties(self.window_properties())
        if self.camLens is None:
            self.camLens = PerspectiveLens()
        self.camLens.setAspectRatio(DEFAULT_ASPECT)
        self._register_overlay_bin()
        enable_gltf(self)
        assets.preload_assets(self)
        self.setup_lights()
        self.mono_font = self.load_mono_font()
        self.audio = GameAudio(self)
        self.game = Game()
        # Game-level overlays (above every stage), driven by the one render loop.
        self.toast = Toast(self)                          # "now playing" + generic toasts
        self.music = MusicPlayer(self)                    # per-stage background music
        self.notifications = Notifications(self, self.game)  # achievement/Dave overlay
        # The shared Ask-Simon / Ask-Discord panels are owned by the Game
        # (game.simon_panel / game.discord_panel), built once on first hub entry, so
        # tasks can toggle them via game.set_advisors_visible().
        self.stage = None
        self.session_started = False                      # a career is in progress (enables pause menu)
        # NB: ``self.config`` is ShowBase's Panda config -- don't shadow it; ours is ``options``.
        self.options = Config.load()                      # options.cfg (sound, ...)
        self.options.apply(self)                          # push saved volumes into music + audio
        self.accept("escape", self._on_escape)            # Esc toggles the pause menu at the hub
        self.taskMgr.add(self._render, "game-render")     # the single render loop
        self.enter_menu(resumable=False)                  # boot to the title menu

    # -- render hierarchy --------------------------------------------------
    def _render(self, task):
        """game.render(): per-frame updates, then the current stage, then the
        game-level panels (Simon/Discord) -- so the panels are owned by the game,
        not by whatever task happens to be open."""
        dt = ClockObject.getGlobalClock().getDt()
        # 1. per-frame updates
        self.music.update(dt)
        self.toast.render(dt)
        self.notifications.render(dt)
        # 2. the current stage
        if self.stage is not None:
            self.stage.render(dt)
        # 3. the shared advisor panels + game-level chrome buttons (owned by the game)
        if self.game.simon_panel is not None:
            self.game.simon_panel.render(dt)
        if self.game.discord_panel is not None:
            self.game.discord_panel.render(dt)
        if self.game.ui is not None:
            self.game.ui.render(dt)
        return Task.cont

    # -- setup -------------------------------------------------------------
    def _register_overlay_bin(self):
        """A cull bin for the game-level overlays, sorted ABOVE the default bins
        (background/opaque/transparent/fixed/unsorted, sorts 10-50) so panels, the
        toast, and notifications always draw over stage UI. Idempotent."""
        cbm = CullBinManager.getGlobalPtr()
        if cbm.findBin(OVERLAY_BIN) < 0:
            cbm.addBin(OVERLAY_BIN, CullBinManager.BTFixed, 60)

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
        self._sync_overlays(stage)

    def _sync_overlays(self, stage):
        """Point the music + advisor panels at the new stage's context key, lift the
        overlays above the freshly-built stage UI (visually AND for mouse picking), then
        apply advisor visibility: hidden on the menu, shown by default on any real stage
        (a task may then hide them itself -- e.g. the race hides them while it's live)."""
        key = getattr(stage, "music_key", "") or getattr(stage, "key", "")
        self.music.set_track(key)
        for panel in (self.game.simon_panel, self.game.discord_panel):
            if panel is not None:
                panel.set_context(key)
        self._lift_overlays()  # reparents (which un-stashes) -- so set visibility AFTER it
        self.game.set_advisors_visible(not isinstance(stage, MenuStage))

    def _lift_overlays(self):
        """Reparent the overlays to the end of aspect2d so they're traversed AFTER the
        new stage's UI. PGTop assigns mouse-region priority by scene-graph order, so
        this is what lets the Discord modal shade actually block clicks to the task
        behind it (the cull bin only handles what's drawn on top, not what's clicked).
        The chrome buttons lift FIRST -- above the task UI but below the panels, so an
        open Discord window's shade still covers the Ask buttons."""
        if self.game.ui is not None:
            self.game.ui.lift()
        for overlay in (self.notifications, self.toast, self.game.simon_panel, self.game.discord_panel):
            if overlay is not None:
                overlay.root.reparentTo(self.aspect2d)

    def start_unlock(self):
        # UnlockStage self-manages its own cleanup before calling on_complete.
        if self.stage is not None:  # e.g. the menu we launched from -- tear it down
            self.stage.exit()
            self.stage = None
        self.music.set_track("unlock")
        self.unlock = UnlockStage(self, on_complete=self.on_unlocked)

    def on_unlocked(self):
        # Runs once, when the cinematic finishes: the ECU is now flashed/unlocked.
        # Kept OUT of enter_hub so returning to the hub from a task doesn't re-run
        # mark_unlocked() and wipe the player's flashed tune + switch-patch slots.
        self.game.car.mark_unlocked()
        self.session_started = True
        if self.game.unlock("first_flash", "Boot Patched, Baby"):
            self.game.dave("flash")
        self.enter_hub()

    # -- menu + save/load --------------------------------------------------
    def enter_menu(self, resumable: bool):
        actions = {"new": self._new_game, "load": self._load_game,
                   "save": self._save_game, "resume": self.enter_hub, "quit": self.userExit}
        self.set_stage(MenuStage(self, self.game, resumable=resumable, actions=actions))

    def _on_escape(self):
        """Esc opens the pause menu from the hub, and resumes from the menu. Inert
        during the cinematic / inside a task (those have their own Back / flow)."""
        if isinstance(self.stage, MenuStage):
            if self.stage.resumable:
                self.enter_hub()
        elif isinstance(self.stage, GarageStage):
            self.enter_menu(resumable=True)

    def _new_game(self):
        self.game.new_game()           # reset career in place (panels keep their ref)
        self.session_started = False
        self.start_unlock()            # same cinematic the app boots into

    def _load_game(self):
        data = storage.read_json(storage.save_path())
        if not data:
            self.toast.show("LOAD FAILED", "no save file found", TOAST_SECONDS)
            return
        self.game.from_dict(data)      # restore in place
        self.session_started = True
        self.enter_hub()               # skip the cinematic -- the ECU state is restored

    def _save_game(self):
        ok = storage.write_json(storage.save_path(), self.game.to_dict())
        self.toast.show("GAME SAVED" if ok else "SAVE FAILED",
                        "career stored" if ok else "could not write save file", TOAST_SECONDS)

    def _build_chrome_buttons(self):
        """The game-level chrome buttons: Ask Discord / Ask Simon (open the panels) and
        Back (TaskBase points it at the active task's on_back, and shows it only in a
        task). On their own OVERLAY_BIN layer so they draw over stage UI; lifted below
        the panels for mouse priority (an open Discord shade covers them)."""
        layer = self.aspect2d.attachNewNode("game-chrome")
        layer.setBin(OVERLAY_BIN, OVERLAY_SORT["panel"])
        self.game.ui = UIObjectController(self, layer)
        right = self.getAspectRatio() - 0.04
        left = -self.getAspectRatio() + 0.04
        self.game.ui.add_button("ask_discord", "Ask Discord", (right - 0.34, 0, -0.71), (0.62, 0.155),
                                self.game.discord_panel.ask, True, BLUE, 0.05, style="pill")
        self.game.ui.add_button("ask_simon", "Ask Simon", (right - 0.34, 0, -0.85), (0.60, 0.155),
                                self.game.simon_panel.ask, True, VIOLET, 0.05, style="pill", icon="simon")
        self.game.ui.add_button("back", "< Back", (left + 0.34, 0, -0.85), (0.60, 0.155),
                                lambda: None, True, VIOLET, 0.05, style="pill", is_visible=False)

    def enter_hub(self):
        if self.game.simon_panel is None:  # build the shared panels + chrome once, on first hub entry
            self.game.simon_panel = SimonPanel(self, self.game, "garage")
            self.game.discord_panel = DiscordPanel(self, self.game, "garage")
            for panel in (self.game.simon_panel, self.game.discord_panel):
                panel.root.setBin(OVERLAY_BIN, OVERLAY_SORT["panel"])  # over stage UI, under toasts
            self._build_chrome_buttons()
        self.set_stage(GarageStage(self, self.game, on_pick=self.open_task,
                                   on_summon=self.open_wizard, on_menu=lambda: self.enter_menu(resumable=True)))

    def open_task(self, key: str):
        self.set_stage(TASK_CLASSES[key](self, self.game, on_back=self.enter_hub))

    def open_wizard(self):
        self.set_stage(WizardTrialStage(self, self.game, on_done=self.enter_hub))
