from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame


class ProgressBar:
    """A simple 2D progress bar: a left-anchored fill inside a track frame."""

    def __init__(self, parent, pos, width, height, track_color, fill_color):
        self.width = width
        self.height = height
        self.track = DirectFrame(
            parent=parent,
            frameSize=(-width / 2, width / 2, -height / 2, height / 2),
            frameColor=track_color,
            pos=pos,
            relief=DGG.FLAT,
        )
        self.fill = DirectFrame(
            parent=self.track,
            frameColor=fill_color,
            relief=DGG.FLAT,
            frameSize=(0, 0.0001, -height / 2, height / 2),
            pos=(-width / 2, 0, 0),
        )
        self.set(0.0)

    def set(self, fraction: float):
        fraction = max(0.0, min(1.0, fraction))
        self.fill["frameSize"] = (0, max(0.0001, self.width * fraction), -self.height / 2, self.height / 2)

    def destroy(self):
        self.track.destroy()
