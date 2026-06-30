from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectLabel import DirectLabel
from direct.gui.OnscreenImage import OnscreenImage
from direct.interval.IntervalGlobal import (
    Func, LerpColorScaleInterval, LerpPosInterval, LerpScaleInterval, Parallel, Sequence,
)
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib

from library.core import assets
from library.core.constants import OVERLAY_BIN

# A "browser window" that animates open from the pressed button and back into it on close.
WINDOW_FS = (-1.30, 1.30, -0.82, 0.82)   # symmetric about origin so it scales about its centre
BAR_BOTTOM = 0.70
OPEN_SECONDS = 0.30
SHADE = (0.02, 0.03, 0.05, 0.55)          # slightly-translucent backdrop
PAGE = (0.95, 0.96, 0.97, 1)              # white-ish browser page
BAR = (0.82, 0.85, 0.89, 1)               # browser chrome bar
INK = (0.10, 0.13, 0.16, 1)               # heading ink
BODY = (0.18, 0.23, 0.28, 1)              # body text
URLC = (0.30, 0.36, 0.42, 1)


class ReviewOverlay(DirectObject):
    """A faux-browser review pane. ``open(item, from_pos)`` grows a tiny rectangle at the
    pressed Read-review button out to a near-fullscreen, slightly-translucent window
    (LerpPos + LerpScale); the title-bar **X** (or Esc) animates it back into the button.
    Built once and reused; raw DirectGui (not the managed controller) because it needs a
    nested, interval-animated node tree -- same toolkit ``unlock_stage`` uses."""

    def __init__(self, app):
        self.app = app
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode("review-overlay")
        self.root.setBin(OVERLAY_BIN, 1100)   # above the shop UI + chrome + toasts
        self.shade = DirectFrame(parent=self.root, frameSize=(-2.2, 2.2, -1.2, 1.2),
                                 frameColor=SHADE, relief=DGG.FLAT, state=DGG.NORMAL)
        self.shade.setTransparency(TransparencyAttrib.MAlpha)
        self.shade.bind(DGG.B1PRESS, lambda _=None: None)  # eat background clicks
        self.window = DirectFrame(parent=self.root, frameSize=WINDOW_FS, frameColor=PAGE,
                                  relief=DGG.FLAT, frameTexture=assets.image_path("ui_box"))
        self.window.setTransparency(TransparencyAttrib.MAlpha)
        bar = DirectFrame(parent=self.window, frameSize=(WINDOW_FS[0], WINDOW_FS[1], BAR_BOTTOM, WINDOW_FS[3]),
                          frameColor=BAR, relief=DGG.FLAT, frameTexture=assets.image_path("ui_box"))
        bar.setTransparency(TransparencyAttrib.MAlpha)
        self.url = DirectLabel(parent=bar, text="", text_scale=0.045, text_fg=URLC,
                               text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0),
                               pos=(WINDOW_FS[0] + 0.10, 0, 0.745))
        self.close_btn = DirectButton(parent=bar, text="X", text_scale=0.06, text_fg=(0.97, 0.98, 1, 1),
                                      text_pos=(0, -0.02), frameColor=(0.80, 0.24, 0.24, 1), relief=DGG.FLAT,
                                      frameTexture=assets.image_path("ui_box"), frameSize=(-0.05, 0.05, -0.05, 0.05),
                                      pos=(WINDOW_FS[1] - 0.08, 0, 0.76), command=self.close)
        self.close_btn.setTransparency(TransparencyAttrib.MAlpha)
        self.heading = DirectLabel(parent=self.window, text="", text_scale=0.085, text_fg=INK,
                                   text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0),
                                   pos=(WINDOW_FS[0] + 0.12, 0, 0.52))
        self.subhead = DirectLabel(parent=self.window, text="Reviews", text_scale=0.05, text_fg=URLC,
                                   text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0),
                                   pos=(WINDOW_FS[0] + 0.12, 0, 0.40))
        self.body = DirectLabel(parent=self.window, text="", text_scale=0.052, text_fg=BODY,
                                text_align=TextNode.ALeft, text_wordwrap=36, text_font=self.font,
                                frameColor=(0, 0, 0, 0), pos=(WINDOW_FS[0] + 0.12, 0, 0.30))
        # The fact-checker clipart on the right (placeholder; swap data/images/detective.png).
        self.detective = OnscreenImage(parent=self.window, image=assets.image_path("detective"),
                                       pos=(0.84, 0, -0.04), scale=0.42)
        self.detective.setTransparency(TransparencyAttrib.MAlpha)
        self.root.hide()
        self._open = False
        self._from = (0, 0, 0)
        self._anim = None

    # -- open / close ------------------------------------------------------
    def open(self, item, from_pos):
        if self._open:
            return
        self._open = True
        self._stop_anim()
        self.url["text"] = f"mygolfmk7.com/reviews/{item.key}"
        self.heading["text"] = item.name
        self.body["text"] = item.review
        self._from = (from_pos[0], 0, from_pos[2])
        self.root.reparentTo(self.app.aspect2d)  # to the end -> its shade catches clicks
        self.root.show()
        self.window.setPos(*self._from)
        self.window.setScale(0.04)
        self.shade.setColorScale(1, 1, 1, 0)
        self._anim = Parallel(
            LerpPosInterval(self.window, OPEN_SECONDS, (0, 0, 0), blendType="easeOut"),
            LerpScaleInterval(self.window, OPEN_SECONDS, 1.0, blendType="easeOut"),
            LerpColorScaleInterval(self.shade, OPEN_SECONDS, (1, 1, 1, 1), (1, 1, 1, 0)),
        )
        self._anim.start()
        self.accept("escape", self.close)

    def close(self):
        if not self._open:
            return
        self._open = False
        self.ignore("escape")
        self._stop_anim()
        self._anim = Sequence(
            Parallel(
                LerpPosInterval(self.window, OPEN_SECONDS, self._from, blendType="easeIn"),
                LerpScaleInterval(self.window, OPEN_SECONDS, 0.04, blendType="easeIn"),
                LerpColorScaleInterval(self.shade, OPEN_SECONDS, (1, 1, 1, 0), (1, 1, 1, 1)),
            ),
            Func(self.root.hide),
        )
        self._anim.start()

    def is_open(self) -> bool:
        return self._open

    def _stop_anim(self):
        if self._anim is not None:
            self._anim.finish()
            self._anim = None

    def destroy(self):
        self.ignoreAll()
        self._stop_anim()
        if not self.root.isEmpty():
            self.root.removeNode()
