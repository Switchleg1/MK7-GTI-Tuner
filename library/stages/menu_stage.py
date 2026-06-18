from __future__ import annotations

from panda3d.core import TextNode

from library.core import storage
from library.core.constants import (
    BLUE, DIM, GREEN, GREEN_2, MENU_BTN, MENU_BTN_GAP, MENU_ITEMS, MENU_MUSIC_KEY,
    MENU_PANEL, MENU_VOL_RANGE, PANEL, PANEL_DARK, TEXT,
)
from library.stages.hud import Hud


class MenuStage(Hud):
    """The front-end + pause menu. One stage that walks three pages -- root (New
    Game / Load / Save / Options / Quit), options (sound volumes + a Graphics link),
    and graphics (a placeholder for later) -- on a centred glass card. The app passes
    the actions in ``actions``; New Game runs the same cinematic the app boots into.

    ``resumable`` is True when a career is in progress (opened as a pause menu, so
    Resume + Save Game show); False on the title screen."""

    music_key = MENU_MUSIC_KEY  # share the hub track so music is continuous

    def __init__(self, app, game, *, resumable: bool, actions: dict):
        super().__init__(app, "menu")
        self.game = game
        self.resumable = resumable
        self.actions = actions      # {"new","load","save","resume","quit"} -> callables
        self.config = app.options   # the player's options (Config); app.config is Panda's
        self.page = "root"

    def enter(self):
        self.draw()

    def exit(self):
        self.config.save()  # persist any options tweaks on the way out
        self.destroy()

    # -- pages -------------------------------------------------------------
    def go(self, page: str):
        self.page = page
        self.draw()

    def draw(self):
        self.clear()
        left, right = self.bounds()
        self.frame((left, right, -1.0, 1.0), color=PANEL_DARK, border=None)  # full backdrop
        self.frame(MENU_PANEL, (0, 0, 0), PANEL)                              # centred card
        {"root": self._draw_root, "options": self._draw_options,
         "graphics": self._draw_graphics}[self.page]()

    def _draw_root(self):
        self.image("logo", (0, 0, 0.50), (0.34, 1, 0.09))
        self.label("CAREER", (0, 0, 0.37), 0.034, DIM, align=TextNode.ACenter)
        handlers = {
            "resume": self.actions["resume"], "new": self.actions["new"],
            "load": self.actions["load"], "save": self.actions["save"],
            "options": lambda: self.go("options"), "quit": self.actions["quit"],
        }
        items = [item for item in MENU_ITEMS if self._visible(item[2])]
        z = 0.20
        for key, text, _ in items:
            enabled = storage.has_save() if key == "load" else True
            color = GREEN_2 if key in ("resume", "new") else None
            self.button(text, (0, 0, z), MENU_BTN, handlers[key], enabled, color, 0.05)
            z -= MENU_BTN_GAP
        hint = "Esc resumes" if self.resumable else "Pick New Game to start the cinematic"
        self.label(hint, (0, 0, z - 0.02), 0.028, DIM, align=TextNode.ACenter)

    def _visible(self, visibility: str) -> bool:
        if visibility == "pause":
            return self.resumable
        if visibility == "main":
            return not self.resumable
        return True

    def _draw_options(self):
        self.label("OPTIONS", (0, 0, 0.50), 0.06, BLUE, align=TextNode.ACenter)
        self.label("SOUND", (-0.58, 0, 0.34), 0.03, DIM)
        self.sl_music, self.lbl_music = self._volume_row("Music", self.config.music_volume, 0.20, self._on_music)
        self.sl_fx, self.lbl_fx = self._volume_row("Effects", self.config.fx_volume, 0.02, self._on_fx)
        self.button("Graphics", (0, 0, -0.24), (0.7, 0.11), lambda: self.go("graphics"), True, None, 0.046)
        self.button("Back", (0, 0, -0.42), (0.7, 0.11), lambda: self.go("root"), True, GREEN_2, 0.046)

    def _volume_row(self, name, value, z, command):
        self.label(name, (-0.58, 0, z + 0.018), 0.04, TEXT)
        node = self.slider((0.10, 0, z), MENU_VOL_RANGE, value, width=0.6)
        node["command"] = command  # wired after creation so it doesn't fire on init
        pct = self.label(f"{round(value * 100)}%", (0.58, 0, z + 0.018), 0.04, GREEN, align=TextNode.ARight)
        return node, pct

    def _draw_graphics(self):
        self.label("GRAPHICS", (0, 0, 0.50), 0.06, BLUE, align=TextNode.ACenter)
        self.label("Resolution, V-Sync and display options are coming soon.",
                   (0, 0, 0.16), 0.036, DIM, align=TextNode.ACenter, wordwrap=22)
        self.button("Back", (0, 0, -0.34), (0.7, 0.11), lambda: self.go("options"), True, GREEN_2, 0.046)

    # -- volume handlers (apply live + persist) ----------------------------
    def _on_music(self):
        self.config.music_volume = round(self.sl_music["value"], 2)
        self.app.music.set_volume(self.config.music_volume)
        self.lbl_music["text"] = f"{round(self.config.music_volume * 100)}%"
        self.config.save()

    def _on_fx(self):
        self.config.fx_volume = round(self.sl_fx["value"], 2)
        self.app.audio.set_fx_volume(self.config.fx_volume)
        self.lbl_fx["text"] = f"{round(self.config.fx_volume * 100)}%"
        self.config.save()
