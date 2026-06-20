from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG

from library.core.constants import (
    AMBER, BLUE, BOX_LINE, DISCORD_CHANNEL_GROUP, DISCORD_MSG_LINES, DISCORD_OFFLINE_MAX,
    DISCORD_ONLINE_MAX, DISCORD_SERVER, DISCORD_WIN, DISCORD_RAIL_W, DISCORD_CHAN_W,
    DISCORD_MEMBER_W, DIM, GREEN, LINE, MUTED, PANEL, PANEL_DARK, RED, TEXT, WHITE,
)
from library.core.utils import rgba
from library.stages.hud import Hud
from library.core.ui.ui_object_controller import UIObjectController

RAIL_BG = rgba("#070b0e", 0.85)
CHAN_ACTIVE = rgba("#1b242c", 0.9)


class DiscordPanel(Hud):
    """The 'Ask Discord' chat window (MQB Vibe Coders).

    A game-level chrome button opens a Discord-style window: a server rail, the channel
    list, the #ecu-tuning message area with a text box, and the member list on the right
    (only a sampled fraction online). Type a help request, press Enter, and the Discord
    (game model) resolves it into an outcome -- money / a community map / clout, or a
    broken part / lost clients. All UI is managed objects on ``self.ui``, rebuilt on each
    ``draw()`` (its own node tree, so the host screen doesn't redraw)."""

    def __init__(self, app, game, tab: str = ""):
        super().__init__(app, "discord-panel")
        self.game                   = game
        self.tab                    = tab
        self.open                   = False
        self.open_changed           = False
        self.messages: list[dict]   = []
        self.entry                  = None
        self.ui                     = UIObjectController(app, self.root.attachNewNode("discord-ui"))

    # -- actions -----------------------------------------------------------
    def ask(self):
        self.game.discord.refresh_online()  # re-sample who's around
        self.messages = self.game.discord.backlog(4)
        self._set_opened(True)


    def close(self):
        self._set_opened(False)


    def set_context(self, key: str):
        """Re-point the panel at the new stage and close the window if open."""
        self.tab = key
        self._set_opened(False)


    def render(self, dt):
        self.ui.render(dt)  # window objects: visibility + the X/close buttons' click flash


    def _submit(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        
        self.messages.append({"name": "You", "color": WHITE, "text": text})
        ed_before = self.game.bro.emotional_damage
        outcome = self.game.ask_discord(text)
        self.messages.extend(outcome["replies"])
        self.messages.append({"name": "# result", "color": GREEN if outcome["kind"] == "good" else RED,
                              "text": outcome["summary"]})
        self._note_damage(ed_before)
        self._refresh_host()  # the screen behind drew cash/cred before this changed them
        
        input = self.ui.get("input")
        input.text("")
        input.focus()
        self._update_messages()
        

    def _note_damage(self, before: float):
        """Surface the emotional-damage swing right in the thread (it's otherwise
        only shown on the race screen). Bad outcomes hurt, good ones heal."""
        ed = self.game.bro.emotional_damage
        delta = ed - before
        if abs(delta) < 0.5:
            return
        self.messages.append({"name": "# emotional damage",
                              "color": RED if delta > 0 else GREEN,
                              "text": f"{round(ed)}%  ({'+' if delta > 0 else ''}{round(delta)})"})
        

    def _refresh_host(self):
        """The outcome moved cash / cred / ED on the model, but the task screen
        behind this window drew those values before the interaction. Mark it dirty
        so its header (and any cash readout) rebuilds on the next frame."""
        stage = getattr(self.app, "stage", None)
        if stage is not None and hasattr(stage, "dirty"):
            stage.dirty = True
            
            
    def _set_opened(self, value):
        if self.open != value:
            self.open = value
            if self.open:
                self._create_window()
            else:
                self._clear_window()
            

    def _create_window(self):
        self._modal_shade()  # added first so it sits below the window's controls in pick order
        hw, hh, cz = DISCORD_WIN["half_w"], DISCORD_WIN["half_h"], DISCORD_WIN["center_z"]
        x0, x1, top, bot = -hw, hw, cz + hh, cz - hh
        self.ui.add_frame("window", frame_size=(x0, x1, bot, top), color=PANEL_DARK, border=BOX_LINE)
        rail_x1 = x0 + DISCORD_RAIL_W
        chan_x1 = rail_x1 + DISCORD_CHAN_W
        mem_x0 = x1 - DISCORD_MEMBER_W
        self._rail(x0, rail_x1, bot, top)
        self._channels(rail_x1, chan_x1, bot, top)
        self._members(mem_x0, x1, bot, top)
        self._chat(chan_x1, mem_x0, bot, top)
        
        
    def _clear_window(self):
        self.ui.clear()
        self.entry = None
        
            
    def _modal_shade(self):
        """A full-screen, click-eating dim layer behind the window. ``state=NORMAL``
        makes it grab mouse events; because the app lifts this panel to the end of
        aspect2d (``_lift_overlays``), its region sorts above the task's widgets, so
        clicks and slider drags can't pass through. The window's own button + entry
        are added after this (later in the controller) so they pick on top of it."""
        self.ui.add_frame("shade", frame_size=(-2.2, 2.2, -1.2, 1.2), color=(0.02, 0.03, 0.05, 0.5),
                          border=None, texture=None, state=DGG.NORMAL)


    def _rail(self, x0, x1, bot, top):
        self.ui.add_frame("rail-bg", frame_size=(x0, x1, bot, top), color=RAIL_BG, border=None)
        cx = (x0 + x1) / 2
        self.ui.add_image("rail-active", "avatar", (cx, 0, top - 0.13), 0.05, color_scale=GREEN)
        for i, color in enumerate((AMBER, BLUE, RED, DIM)):
            self.ui.add_image(f"rail-{i}", "avatar", (cx, 0, top - 0.27 - i * 0.13), 0.044, color_scale=color)


    def _channels(self, x0, x1, bot, top):
        self.ui.add_text("chan-server", DISCORD_SERVER, (x0 + 0.05, 0, top - 0.07), 0.038, WHITE)
        self.ui.add_frame("chan-rule", frame_size=(x0 + 0.03, x1 - 0.03, top - 0.115, top - 0.112), color=LINE, border=None)
        self.ui.add_text("chan-group", DISCORD_CHANNEL_GROUP, (x0 + 0.05, 0, top - 0.17), 0.028, DIM)
        z = top - 0.235
        for i, channel in enumerate(self.game.discord.channels):
            active = channel == self.game.discord.active_channel
            if active:
                self.ui.add_frame(f"chan-hl-{i}", frame_size=(x0 + 0.03, x1 - 0.03, z - 0.022, z + 0.032), color=CHAN_ACTIVE, border=None)
            self.ui.add_text(f"chan-{i}", f"#  {channel}", (x0 + 0.07, 0, z), 0.028, TEXT if active else DIM)
            z -= 0.066


    def _members(self, x0, x1, bot, top):
        discord = self.game.discord
        online, offline = discord.online(), discord.offline()
        self.ui.add_text("mem-online-h", f"Online - {len(online)}", (x0 + 0.06, 0, top - 0.07), 0.026, DIM)
        z = top - 0.135
        for i, member in enumerate(online[:DISCORD_ONLINE_MAX]):
            self._member_row(f"on-{i}", x0, member, z, True)
            z -= 0.105
        if len(online) > DISCORD_ONLINE_MAX:
            self.ui.add_text("mem-more-online", f"+{len(online) - DISCORD_ONLINE_MAX} more online", (x0 + 0.10, 0, z + 0.01), 0.022, DIM)
            z -= 0.06
        self.ui.add_text("mem-offline-h", f"Offline - {len(offline)}", (x0 + 0.06, 0, z - 0.005), 0.026, DIM)
        z -= 0.075
        for i, member in enumerate(offline[:DISCORD_OFFLINE_MAX]):
            self._member_row(f"off-{i}", x0, member, z, False)
            z -= 0.082
        if len(offline) > DISCORD_OFFLINE_MAX:
            self.ui.add_text("mem-more-offline", f"+{len(offline) - DISCORD_OFFLINE_MAX} more", (x0 + 0.10, 0, z + 0.01), 0.022, MUTED)


    def _member_row(self, prefix, x0, member, z, online):
        self.ui.add_image(f"{prefix}-av", "avatar", (x0 + 0.10, 0, z), 0.036,
                          color_scale=member.color if online else MUTED)
        self.ui.add_frame(f"{prefix}-dot", frame_size=(x0 + 0.125, x0 + 0.15, z - 0.028, z - 0.004),
                          color=GREEN if online else MUTED, border=None)
        name = ("* " if getattr(member, "crown", False) else "") + member.name
        self.ui.add_text(f"{prefix}-name", name, (x0 + 0.18, 0, z + (0.008 if online and member.status else -0.006)), 0.029,
                         member.color if online else MUTED)
        if online and member.status:
            self.ui.add_text(f"{prefix}-status", member.status, (x0 + 0.18, 0, z - 0.032), 0.020, DIM)


    def _chat(self, x0, x1, bot, top):
        discord = self.game.discord
        self.ui.add_text("chat-title", f"#  {discord.active_channel}", (x0 + 0.06, 0, top - 0.07), 0.038, BLUE)
        self.ui.add_button("chat-close", "X", (x1 - 0.07, 0, top - 0.06), (0.09, 0.075), self.close, True, PANEL_DARK, 0.045)
        self.ui.add_frame("chat-rule", frame_size=(x0 + 0.02, x1 - 0.02, top - 0.115, top - 0.112), color=LINE, border=None)
        wrap = int((x1 - x0 - 0.14) / 0.018)
        z = top - 0.18
        self._create_messages(x0, wrap, z)
        self._update_messages()
        self._input(x0, x1, bot)


    def _input(self, x0, x1, bot):
        iz = bot + 0.09
        self.ui.add_text("input-hint", "type a help request and press Enter (mention a datalog for better odds)",
                         (x0 + 0.06, 0, iz + 0.075), 0.022, DIM)
        self.ui.add_frame("input-box", frame_size=(x0 + 0.04, x1 - 0.04, iz - 0.05, iz + 0.05), color=PANEL, border=BOX_LINE)
        self.entry = self.ui.add_entry("input", self._submit, (x0 + 0.09, 0, iz - 0.013),
                                       width=42, scale=0.038, color=TEXT, initial="", focus=True)
        
        
    def _create_messages(self, x0, wrap, z):
        for i in range(DISCORD_MSG_LINES):
            self.ui.add_text(f"entry-{i}-name", "", (x0 + 0.06, 0, z), 0.026, TEXT)
            self.ui.add_text(f"entry-{i}-text", "", (x0 + 0.06, 0, z - 0.042), 0.030, TEXT, wordwrap=wrap)
            z -= 0.123
        
        
    def _update_messages(self):
        for i, entry in enumerate(self.messages[-DISCORD_MSG_LINES:]):
            msg = self.ui.get(f"entry-{i}-name")
            msg.text(entry["name"])
            msg.color(entry["color"])
                
            text = self.ui.get(f"entry-{i}-text")
            text.text(entry["text"])