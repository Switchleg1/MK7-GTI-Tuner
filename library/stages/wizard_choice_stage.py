from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import BLUE, DIM, GREEN_2, PANEL, PANEL_DARK, TEXT, VIOLET
from library.stages.hud import Hud


class WizardChoiceStage(Hud):
    """When the hooded Bench Wizard's DM is answered, he offers a choice of proofs:
    bench an ECU (the three-part Trial) or hand-build a dongle. Either path, passed,
    grants god status + the same payout -- only the trophy differs. A pure-2D modal;
    each card just hands off to the matching mini-game stage."""

    music_key = "unlock"

    def __init__(self, app, game, on_bench, on_dongle, on_back):
        super().__init__(app, "wizard-choice")
        self.game = game
        self.on_bench = on_bench
        self.on_dongle = on_dongle
        self.on_back = on_back

    def enter(self):
        self.draw()

    def exit(self):
        self.destroy()

    def draw(self):
        left, right = self.bounds()
        self.ui.add_frame("backdrop", frame_size=(-2.0, 2.0, -1.0, 1.0), color=PANEL_DARK, border=None)
        self.ui.add_frame("hdr-bg", frame_size=(left, right, 0.74, 0.94), pos=(0, 0, 0.84), color=PANEL, border=None)
        self.ui.add_image("hdr-av", "avatar", (left + 0.12, 0, 0.84), 0.06, color_scale=VIOLET)
        self.ui.add_text("hdr-title", "THE BENCH WIZARD", (left + 0.22, 0, 0.85), 0.046, VIOLET)
        self.ui.add_text("hdr-sub", "Prove yourself. Pick your proof.", (left + 0.22, 0, 0.79), 0.026, DIM)
        self.ui.add_button("abort", "Abort", (right - 0.12, 0, 0.84), (0.16, 0.09), self.on_back, True, PANEL, 0.034)
        self.ui.add_text("prompt", '"Show me you\'re real. Choose one."', (0, 0, 0.52), 0.04, TEXT, align=TextNode.ACenter)
        # Two big choice cards: same reward, different challenge.
        self.ui.add_button("bench", "BENCH AN ECU", (-0.55, 0, 0.12), (0.86, 0.42), self.on_bench, True, BLUE, 0.05)
        self.ui.add_text("bench-blurb", "The three-part Trial: power the rig, probe the board, hit the sync window.",
                         (-0.55, 0, -0.22), 0.026, DIM, align=TextNode.ACenter, wordwrap=30)
        self.ui.add_button("dongle", "MAKE DONGLES", (0.55, 0, 0.12), (0.86, 0.42), self.on_dongle, True, GREEN_2, 0.05)
        self.ui.add_text("dongle-blurb", "Hand-build a dongle: grab the loose parts and drag each onto its socket.",
                         (0.55, 0, -0.22), 0.026, DIM, align=TextNode.ACenter, wordwrap=30)
        self.ui.add_text("foot", "Same reward either way. Different bragging rights.",
                         (0, 0, -0.6), 0.028, VIOLET, align=TextNode.ACenter)
        self.ui.lift()
