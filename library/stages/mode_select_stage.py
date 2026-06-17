from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib

from library.core import assets
from library.core.constants import BG, DIM, GREEN, LINE, MODES, PANEL, TEXT, WHITE

COLUMNS = 3
CARD_W = 0.95
CARD_H = 0.52
GAP_X = 0.08
GAP_Z = 0.10
TOP_Z = 0.18


class ModeSelectStage(DirectObject):
    """Full-screen 'SELECT MODE' menu shown after the unlock. Each card maps to a
    garage tab; picking one calls ``on_pick(tab_key)`` to enter the garage there."""

    def __init__(self, base, on_pick):
        super().__init__()
        self.base = base
        self.on_pick = on_pick
        self.ui = base.aspect2d.attachNewNode("mode-select")
        self._build()

    def _build(self):
        aspect = self.base.getAspectRatio()
        DirectFrame(parent=self.ui, frameSize=(-aspect, aspect, -1, 1), frameColor=(BG[0], BG[1], BG[2], 0.92), relief=DGG.FLAT)
        logo = OnscreenImage(parent=self.ui, image=assets.image_path("logo"), pos=(0, 0, 0.82), scale=(0.42, 1, 0.115))
        logo.setTransparency(TransparencyAttrib.MAlpha)
        DirectLabel(parent=self.ui, text="SELECT MODE", pos=(0, 0, 0.58), scale=0.085, text_fg=GREEN, text_align=TextNode.ACenter, frameColor=(0, 0, 0, 0), relief=None)
        DirectLabel(parent=self.ui, text="ECU unlocked. The MK7 is yours to ruin - pick your poison.", pos=(0, 0, 0.48), scale=0.038, text_fg=DIM, text_align=TextNode.ACenter, frameColor=(0, 0, 0, 0), relief=None)

        span = COLUMNS * CARD_W + (COLUMNS - 1) * GAP_X
        x0 = -span / 2 + CARD_W / 2
        for index, (tab, title, blurb) in enumerate(MODES):
            row, col = divmod(index, COLUMNS)
            x = x0 + col * (CARD_W + GAP_X)
            z = TOP_Z - row * (CARD_H + GAP_Z)
            self._card(tab, title, blurb, x, z)

    def _card(self, tab, title, blurb, x, z):
        button = DirectButton(
            parent=self.ui,
            pos=(x, 0, z),
            frameSize=(-CARD_W / 2, CARD_W / 2, -CARD_H / 2, CARD_H / 2),
            frameColor=PANEL,
            relief=DGG.FLAT,
            pressEffect=0,
            command=self._pick,
            extraArgs=[tab],
        )
        DirectFrame(parent=button, frameSize=(-CARD_W / 2, CARD_W / 2, CARD_H / 2 - 0.02, CARD_H / 2), frameColor=GREEN, relief=DGG.FLAT)
        DirectLabel(parent=button, text=title, pos=(0, 0, 0.08), scale=0.06, text_fg=WHITE, text_align=TextNode.ACenter, frameColor=(0, 0, 0, 0), relief=None)
        DirectLabel(parent=button, text=blurb, pos=(0, 0, -0.04), scale=0.034, text_fg=TEXT, text_align=TextNode.ACenter, text_wordwrap=12, frameColor=(0, 0, 0, 0), relief=None)

    def _pick(self, tab):
        self.cleanup()
        self.on_pick(tab)

    def cleanup(self):
        self.ui.removeNode()
        self.ignoreAll()
