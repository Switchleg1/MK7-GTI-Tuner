from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, TransparencyAttrib

from library.core.assets import assets
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
    WHITE,
)
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
        self._flash_command = None
        self._armed = False
        self.log_lines: list[tuple[str, tuple]] = []
        self._build()
        self.root.hide()

    # -- construction ------------------------------------------------------
    def _label(self, text, pos, scale, color, align=TextNode.ALeft, parent=None):
        return DirectLabel(parent=parent or self.root, text=text, pos=pos, scale=scale, text_fg=color, text_align=align, frameColor=(0, 0, 0, 0), relief=None)

    def _build(self):
        body = DirectFrame(parent=self.root, frameSize=(CX - PHONE_UI_HALF_W, CX + PHONE_UI_HALF_W, -PHONE_UI_HALF_H, PHONE_UI_HALF_H), frameColor=PHONE_FRAME, relief=DGG.FLAT)
        DirectFrame(parent=body, frameSize=(CX - 0.315, CX + 0.315, -0.685, 0.685), frameColor=PHONE_BEZEL, relief=DGG.FLAT)
        screen = DirectFrame(parent=body, frameSize=(CX - 0.30, CX + 0.30, -0.66, 0.65), frameColor=PHONE_SCREEN, relief=DGG.FLAT)

        wallpaper = OnscreenImage(parent=screen, image=assets.image_path("wallpaper"), pos=(CX, 0, -0.005), scale=(0.30, 1, 0.655))
        wallpaper.setTransparency(TransparencyAttrib.MAlpha)

        self._label("9:41", (CX - 0.27, 0, 0.595), 0.03, DIM)
        self._label("SimosTools  -  LTE  -  87%", (CX + 0.27, 0, 0.595), 0.03, DIM, align=TextNode.ARight)

        icon = OnscreenImage(parent=self.root, image=assets.image_path("app_icon"), pos=(CX - 0.225, 0, 0.50), scale=0.045)
        icon.setTransparency(TransparencyAttrib.MAlpha)
        self._label("SimosTools", (CX - 0.165, 0, 0.485), 0.05, GREEN)
        self._label("ECM3 bench flash", (CX - 0.27, 0, 0.42), 0.03, DIM)
        DirectFrame(parent=self.root, frameSize=(CX - 0.27, CX + 0.27, -0.004, 0.004), frameColor=(0.16, 0.30, 0.34, 1), pos=(0, 0, 0.385), relief=DGG.FLAT)

        self.log_labels = [self._label("", (CX - 0.275, 0, LOG_TOP - i * LOG_STEP), 0.03, TEXT) for i in range(PHONE_LOG_LINES)]

        self.flash_button = DirectButton(
            parent=self.root,
            text="FLASH",
            pos=(CX, 0, -0.55),
            scale=1,
            text_scale=0.06,
            text_fg=WHITE,
            text_align=TextNode.ACenter,
            frameSize=(-0.26, 0.26, -0.06, 0.06),
            frameColor=GREEN_2,
            relief=DGG.FLAT,
            pressEffect=0,
            command=self._on_flash,
        )
        self.flash_button.hide()

        self.percent = self._label("", (CX, 0, -0.50), 0.045, GREEN, align=TextNode.ACenter)
        self.progress = ProgressBar(self.root, (CX, 0, -0.57), 0.54, 0.045, (0.05, 0.08, 0.10, 1), GREEN)
        self.progress.track.hide()

        self.check = OnscreenImage(parent=self.root, image=assets.image_path("check"), pos=(CX, 0, -0.50), scale=0.13)
        self.check.setTransparency(TransparencyAttrib.MAlpha)
        self.check.hide()
        self.done_label = self._label("", (CX, 0, -0.66), 0.038, GREEN, align=TextNode.ACenter)

    # -- behaviour ---------------------------------------------------------
    def show(self):
        self.root.show()

    def hide(self):
        self.root.hide()

    def arm_flash(self, command):
        self._flash_command = command
        self._armed = True
        self.flash_button.show()

    def _on_flash(self):
        if self._armed and self._flash_command:
            self._armed = False
            self.flash_button.hide()
            self._flash_command()

    def begin_progress(self):
        self.flash_button.hide()
        self.progress.track.show()
        self.set_progress(0.0)

    def set_progress(self, fraction: float):
        self.progress.set(fraction)
        self.percent["text"] = f"{round(fraction * 100)}%"

    def append_log(self, text: str, color=TEXT):
        self.log_lines.append((text, color))
        visible = self.log_lines[-PHONE_LOG_LINES:]
        for i, label in enumerate(self.log_labels):
            if i < len(visible):
                label["text"], label["text_fg"] = visible[i]
            else:
                label["text"] = ""

    def show_complete(self, message: str):
        self.progress.track.hide()
        self.percent["text"] = ""
        self.check.show()
        self.done_label["text"] = message
        self.done_label["text_fg"] = GREEN

    def destroy(self):
        self.progress.destroy()
        self.root.removeNode()
