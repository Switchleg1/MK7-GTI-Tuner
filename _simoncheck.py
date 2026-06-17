"""Throwaway: walk the real flow to garage, open Simon, screenshot (clean)."""
from panda3d.core import loadPrcFileData

loadPrcFileData("", "window-type offscreen\nwin-size 1280 720")

from library.core.panda_config import configure_panda3d

configure_panda3d()

from panda3d.core import Filename
from library.game.app import MK7Tuner3D

app = MK7Tuner3D()
u = app.unlock
u._on_plug(); u.sequence.finish()
u._on_phone(); u.sequence.finish()
u._on_flash(); u.sequence.finish(); u.sequence.finish()
u._finish()                       # cleanup unlock -> mode select
app.mode_select._pick("maps")     # cleanup mode select -> garage
app.ask_simon()
app.draw_ui()
for _ in range(3):
    app.graphicsEngine.renderFrame()
app.win.saveScreenshot(Filename.fromOsSpecific("_simoncheck.png"))
print("font loaded:", app.simon_font is not None, "| FLOW OK")
