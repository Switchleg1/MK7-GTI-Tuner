from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import AMBER, BLUE, DIM, GREEN, GREEN_2, LINE, PANEL_DARK, RED, TEXT, VIOLET
from library.game.discord import thread
from library.stages.hud import Hud

KIND_COLORS = {"dismiss": DIM, "help": GREEN, "hype": AMBER, "corn": GREEN, "dev": VIOLET, "troll": RED}


class DiscordPanel(Hud):
    """'Ask Discord' widget: a pill (above the Ask Simon pill) that opens a #help
    thread. First ask = everyone says 'post a log'; hit Post a log and ask again to
    get a real (state-aware) tip from the vet -- while someone still says post a log.

    Own node tree so it toggles without the host screen redrawing. Companion to
    SimonPanel; ``tab`` feeds the underlying rules context."""

    def __init__(self, app, game, tab: str = ""):
        super().__init__(app, "discord-panel")
        self.game = game
        self.tab = tab
        self.open = False
        self.posted = False
        self.replies = []
        self.tick = 0
        self.draw()

    def ask(self):
        self.open = True
        self.replies = thread(self.game, self.posted, self.tick)
        self.tick += 1
        self.draw()

    def post_log(self):
        self.posted = True
        self.ask()  # re-pull the thread -- now the vet usually actually helps

    def close(self):
        self.open = False
        self.posted = False
        self.draw()

    def draw(self):
        self.clear()
        left, right = self.bounds()
        self.pill("Ask Discord", (right - 0.34, 0, -0.71), self.ask, color=BLUE, width=0.62)
        if not self.open:
            return
        pw, ph = 1.52, 1.06
        cx, cz = 0.0, 0.04
        x0, x1 = cx - pw / 2, cx + pw / 2
        top, bot = cz + ph / 2, cz - ph / 2
        self.frame((x0, x1, bot, top), (0, 0, 0), PANEL_DARK, border=LINE)
        self.label("#help  -  SimosTools Discord", (x0 + 0.07, 0, top - 0.08), 0.040, BLUE)
        self.button("X", (x1 - 0.07, 0, top - 0.08), (0.10, 0.10), self.close, True, PANEL_DARK, 0.05)
        z = top - 0.21
        for reply in self.replies:
            color = KIND_COLORS.get(reply["kind"], DIM)
            self.label(reply["name"], (x0 + 0.08, 0, z), 0.029, color)
            self.label(reply["text"], (x0 + 0.08, 0, z - 0.05), 0.032, TEXT, wordwrap=40)
            z -= 0.155
        if not self.posted:
            self.button("Post a log", (cx - 0.32, 0, bot + 0.08), (0.50, 0.10), self.post_log, True, GREEN_2)
        else:
            self.label("log posted - check the replies", (cx - 0.32, 0, bot + 0.08), 0.030, GREEN, align=TextNode.ACenter)
        self.button("Ask again", (cx + 0.34, 0, bot + 0.08), (0.42, 0.10), self.ask, True)
