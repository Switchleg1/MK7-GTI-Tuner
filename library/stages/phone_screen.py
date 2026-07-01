from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import (
    DIM,
    GREEN,
    GREEN_2,
    PHONE_BEZEL,
    PHONE_FRAME,
    PHONE_LOG_LINES,
    PHONE_SCREEN,
    PHONE_UI_HALF_H,
    PHONE_UI_HALF_W,
    PHONE_UI_LEFT,
    TEXT,
)
from library.core.ui.ui_object_controller import UIObjectController
from library.stages.progress_bar import ProgressBar

CX = PHONE_UI_LEFT + PHONE_UI_HALF_W
LOG_TOP = 0.33
LOG_STEP = 0.055


class PhoneScreen:
    """The held-up phone's screen: a SimosTools-style app that streams the ECU
    readout, exposes the FLASH button, shows flash progress, then completion."""

    def __init__(self, base):
        self.base = base
        self.root = base.aspect2d.attachNewNode("phone-ui")
        self.ui = UIObjectController(base, self.root.attachNewNode("phone-managed-ui"))
        self._flash_command = None
        self._armed = False
        self.log_lines: list[tuple[str, tuple]] = []
        self._build()
        self.root.hide()

    # -- construction ------------------------------------------------------
    def _label(self, key, text, pos, scale, color, align=TextNode.ALeft):
        return self.ui.add_text(key, text, pos, scale, color, align)

    def _build(self):
        self.ui.add_frame("body", frame_size=(CX - PHONE_UI_HALF_W, CX + PHONE_UI_HALF_W, -PHONE_UI_HALF_H, PHONE_UI_HALF_H), color=PHONE_FRAME, border=None, texture=None)
        self.ui.add_frame("bezel", frame_size=(CX - 0.315, CX + 0.315, -0.685, 0.685), color=PHONE_BEZEL, border=None, texture=None)
        self.ui.add_frame("screen", frame_size=(CX - 0.30, CX + 0.30, -0.66, 0.65), color=PHONE_SCREEN, border=None, texture=None)
        self.ui.add_image("wallpaper", "wallpaper", (CX, 0, -0.005), (0.30, 1, 0.655))

        self._label("app-subtitle", "ECM3 bench flash", (CX - 0.27, 0, 0.42), 0.03, DIM)
        self.ui.add_frame("divider", frame_size=(CX - 0.27, CX + 0.27, -0.004, 0.004), pos=(0, 0, 0.385), color=(0.16, 0.30, 0.34, 1), border=None, texture=None)

        self.log_labels = [
            self._label(f"log-{i}", "", (CX - 0.275, 0, LOG_TOP - i * LOG_STEP), 0.03, TEXT)
            for i in range(PHONE_LOG_LINES)
        ]

        self.flash_button = self.ui.add_button(
            "flash", "FLASH", (CX, 0, -0.55), (0.52, 0.12),
            self._on_flash, True, GREEN_2, 0.06, is_visible=False)

        self.percent = self._label("percent", "", (CX, 0, -0.45), 0.045, GREEN, align=TextNode.ACenter)
        self.progress = ProgressBar(self.root, (CX, 0, -0.50), 0.54, 0.045, (0.05, 0.08, 0.10, 1), GREEN)
        self.progress.track.hide()

        self.done_label = self._label("done", "", (CX, 0, -0.66), 0.038, GREEN, align=TextNode.ACenter)

    # -- behaviour ---------------------------------------------------------
    def show(self):
        self.root.show()

    def hide(self):
        self.root.hide()

    def arm_flash(self, command):
        self._flash_command = command
        self._armed = True
        self.flash_button.is_visible(True)

    def _on_flash(self):
        if self._armed and self._flash_command:
            self._armed = False
            self.flash_button.is_visible(False)
            self._flash_command()

    def begin_progress(self):
        self.flash_button.is_visible(False)
        self.progress.track.show()
        self.set_progress(0.0)

    def set_progress(self, fraction: float):
        self.progress.set(fraction)
        self.percent.text(f"{round(fraction * 100)}%")

    def append_log(self, text: str, color=TEXT):
        self.log_lines.append((text, color))
        visible = self.log_lines[-PHONE_LOG_LINES:]
        for i, label in enumerate(self.log_labels):
            if i < len(visible):
                text, color = visible[i]
                label.text(text)
                label.color(color)
            else:
                label.text("")

    def show_complete(self, message: str):
        self.progress.track.hide()
        self.percent.text("")
        self.done_label.text(message)
        self.done_label.color(GREEN)

    def destroy(self):
        self.progress.destroy()
        self.ui.destroy()
        self.root.removeNode()
