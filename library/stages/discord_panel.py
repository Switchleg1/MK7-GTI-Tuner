from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectEntry
from panda3d.core import TextNode, TransparencyAttrib

from library.core import assets
from library.core.constants import (
    AMBER, BLUE, BOX_LINE, DISCORD_CHANNEL_GROUP, DISCORD_MSG_LINES, DISCORD_SERVER,
    DISCORD_WIN, DISCORD_RAIL_W, DISCORD_CHAN_W, DISCORD_MEMBER_W, DIM, GREEN, LINE,
    MUTED, PANEL, PANEL_DARK, RED, TEXT, WHITE,
)
from library.core.utils import rgba
from library.stages.hud import Hud

RAIL_BG = rgba("#070b0e", 0.85)
CHAN_ACTIVE = rgba("#1b242c", 0.9)


class DiscordPanel(Hud):
    """The 'Ask Discord' chat window (MQB Vibe Coders).

    A pill opens a Discord-style window: a server rail, the channel list, the
    #ecu-tuning message area with a text box, and the member list on the right
    (only a sampled fraction online). Type a help request, press Enter, and the
    Discord (game model) resolves it into an outcome -- money / a community map /
    clout, or a broken part / lost clients. Own node tree, so it toggles without
    the host screen redrawing."""

    def __init__(self, app, game, tab: str = ""):
        super().__init__(app, "discord-panel")
        self.game = game
        self.tab = tab
        self.open = False
        self.messages: list[dict] = []
        self.entry = None
        self.draw()

    # -- actions -----------------------------------------------------------
    def ask(self):
        self.open = True
        self.game.discord.refresh_online()  # re-sample who's around
        self.messages = self.game.discord.backlog(4)
        self.draw()

    def close(self):
        self.open = False
        self.draw()

    def set_context(self, key: str):
        """Re-point the panel at the new stage and close the window if open."""
        self.tab = key
        self.open = False
        self.draw()

    def _submit(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.messages.append({"name": "You", "color": WHITE, "text": text})
        outcome = self.game.ask_discord(text)
        self.messages.extend(outcome["replies"])
        self.messages.append({"name": "# result", "color": GREEN if outcome["kind"] == "good" else RED,
                              "text": outcome["summary"]})
        self.draw()  # recreates the entry with focus

    # -- draw --------------------------------------------------------------
    def draw(self):
        self.clear()
        self.entry = None
        right = self.bounds()[1]
        self.pill("Ask Discord", (right - 0.34, 0, -0.71), self.ask, color=BLUE, width=0.62)
        if self.open:
            self._window()

    def _window(self):
        hw, hh, cz = DISCORD_WIN["half_w"], DISCORD_WIN["half_h"], DISCORD_WIN["center_z"]
        x0, x1, top, bot = -hw, hw, cz + hh, cz - hh
        self.frame((x0, x1, bot, top), (0, 0, 0), PANEL_DARK, border=BOX_LINE)
        rail_x1 = x0 + DISCORD_RAIL_W
        chan_x1 = rail_x1 + DISCORD_CHAN_W
        mem_x0 = x1 - DISCORD_MEMBER_W
        self._rail(x0, rail_x1, bot, top)
        self._channels(rail_x1, chan_x1, bot, top)
        self._members(mem_x0, x1, bot, top)
        self._chat(chan_x1, mem_x0, bot, top)

    def _rail(self, x0, x1, bot, top):
        self.frame((x0, x1, bot, top), (0, 0, 0), RAIL_BG, border=None)
        cx = (x0 + x1) / 2
        active = self.image("avatar", (cx, 0, top - 0.13), 0.05)
        active.setColorScale(GREEN)
        for i, color in enumerate((AMBER, BLUE, RED, DIM)):
            icon = self.image("avatar", (cx, 0, top - 0.27 - i * 0.13), 0.044)
            icon.setColorScale(color)

    def _channels(self, x0, x1, bot, top):
        self.label(DISCORD_SERVER, (x0 + 0.05, 0, top - 0.07), 0.038, WHITE)
        self.frame((x0 + 0.03, x1 - 0.03, top - 0.115, top - 0.112), (0, 0, 0), LINE, None)
        self.label(DISCORD_CHANNEL_GROUP, (x0 + 0.05, 0, top - 0.17), 0.028, DIM)
        z = top - 0.235
        for channel in self.game.discord.channels:
            active = channel == self.game.discord.active_channel
            if active:
                self.frame((x0 + 0.03, x1 - 0.03, z - 0.022, z + 0.032), (0, 0, 0), CHAN_ACTIVE, None)
            self.label(f"#  {channel}", (x0 + 0.07, 0, z), 0.028, TEXT if active else DIM)
            z -= 0.066

    def _members(self, x0, x1, bot, top):
        discord = self.game.discord
        online, offline = discord.online(), discord.offline()
        self.label(f"Online - {len(online)}", (x0 + 0.06, 0, top - 0.07), 0.026, DIM)
        z = top - 0.135
        for member in online:
            self._member_row(x0, member, z, True)
            z -= 0.105
        self.label(f"Offline - {len(offline)}", (x0 + 0.06, 0, z - 0.005), 0.026, DIM)
        z -= 0.075
        for member in offline:
            self._member_row(x0, member, z, False)
            z -= 0.082

    def _member_row(self, x0, member, z, online):
        avatar = self.image("avatar", (x0 + 0.10, 0, z), 0.036)
        avatar.setColorScale(member.color if online else MUTED)
        self.frame((x0 + 0.125, x0 + 0.15, z - 0.028, z - 0.004), (0, 0, 0), GREEN if online else MUTED, None)
        name = ("* " if getattr(member, "crown", False) else "") + member.name
        self.label(name, (x0 + 0.18, 0, z + (0.008 if online and member.status else -0.006)), 0.029,
                   member.color if online else MUTED)
        if online and member.status:
            self.label(member.status, (x0 + 0.18, 0, z - 0.032), 0.020, DIM)

    def _chat(self, x0, x1, bot, top):
        discord = self.game.discord
        self.label(f"#  {discord.active_channel}", (x0 + 0.06, 0, top - 0.07), 0.038, BLUE)
        self.button("X", (x1 - 0.07, 0, top - 0.06), (0.09, 0.075), self.close, True, PANEL_DARK, 0.045)
        self.frame((x0 + 0.02, x1 - 0.02, top - 0.115, top - 0.112), (0, 0, 0), LINE, None)
        wrap = int((x1 - x0 - 0.14) / 0.018)
        z = top - 0.18
        for msg in self.messages[-DISCORD_MSG_LINES:]:
            self.label(msg["name"], (x0 + 0.06, 0, z), 0.026, msg["color"])
            self.label(msg["text"], (x0 + 0.06, 0, z - 0.042), 0.030, TEXT, wordwrap=wrap)
            z -= 0.123
        self._input(x0, x1, bot)

    def _input(self, x0, x1, bot):
        iz = bot + 0.09
        self.label("type a help request and press Enter (mention a datalog for better odds)",
                   (x0 + 0.06, 0, iz + 0.075), 0.022, DIM)
        self.frame((x0 + 0.04, x1 - 0.04, iz - 0.05, iz + 0.05), (0, 0, 0), PANEL, BOX_LINE)
        self.entry = DirectEntry(
            parent=self.root, command=self._submit, initialText="", focus=1,
            width=42, scale=0.038, pos=(x0 + 0.09, 0, iz - 0.013),
            frameColor=(0, 0, 0, 0), text_fg=TEXT, text_font=self.font,
            relief=None, numLines=1, overflow=1,
        )
        self.entry.setTransparency(TransparencyAttrib.MAlpha)
        self.nodes.append(self.entry)
