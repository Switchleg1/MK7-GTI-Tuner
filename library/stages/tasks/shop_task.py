from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import BLUE, DIM, GREEN, GREEN_2, GREEN_NAME_CRED, LINE, MODS, TEXT
from library.stages.task_base import TaskBase


class ShopTask(TaskBase):
    """Spend race winnings on mods. Once you hit verified GREEN NAME, this is also
    your pro storefront: sell tunes for cash and DM the pros (Ed/Dave) for stages."""

    title = "SHOP"
    key = "shop"

    def build_buttons(self):
        game = self.game
        left, _ = self.bounds()
        for index, (mod_id, name, cost, _desc) in enumerate(MODS):
            row, col = divmod(index, 2)
            self.buttons.add(f"mod-{mod_id}", name, (left + 0.28 + col * 0.82, 0, 0.25 - row * 0.12),
                             (0.72, 0.08), self.bind(game.buy_mod, mod_id))
        # Pro storefront: built now, shown only once the bro goes verified green name.
        self.buttons.add("sell", "Sell a tune  (+$)", (left + 0.32, 0, -0.45), (0.54, 0.10),
                         self.bind(game.sell_tune), True, GREEN_2, is_visible=False)
        for i, pro in enumerate(game.pros):
            self.buttons.add(f"pro-{pro.handle}", f"Ask {pro.name}", (left + 0.92 + i * 0.42, 0, -0.45),
                             (0.38, 0.10), self.bind(game.ask_pro, pro.handle), is_visible=False)

    def build_ui(self, left, right):
        game = self.game
        bro = game.bro
        self.frame((left, right, -0.62, 0.48), border=None)
        self.image("emoji_cash", (left + 0.10, 0, 0.405), 0.045)
        self.label(f"SHOP  -  CASH ${round(bro.cash)}", (left + 0.18, 0, 0.40), 0.044, BLUE)
        for mod_id, name, cost, _desc in MODS:
            owned = game.car.mods[mod_id]
            button = self.buttons.get(f"mod-{mod_id}")
            button.text(f"{name} - {'owned' if owned else '$' + str(cost)}")
            button.enabled(not owned and bro.cash >= cost)
        self._green_section(left, right)

    def _green_section(self, left, right):
        game, bro = self.game, self.game.bro
        self.frame((left + 0.04, right - 0.04, -0.275, -0.272), (0, 0, 0), LINE, None)  # divider
        green = bro.green_name
        self.buttons.get("sell").is_visible(green)
        for pro in game.pros:
            have = pro.grant_map in bro.unlocked_maps
            button = self.buttons.get(f"pro-{pro.handle}")
            button.is_visible(green)
            button.text(f"Ask {pro.name}" + (" (got it)" if have else ""))
            button.enabled(not have)
        if not green:
            self.label("PRO STOREFRONT - locked", (left + 0.06, 0, -0.34), 0.036, DIM)
            self.label(f"Go verified GREEN NAME at {GREEN_NAME_CRED} cred  (you: {round(bro.cred)}).",
                       (left + 0.06, 0, -0.41), 0.030, DIM, wordwrap=44)
            self.label("Earn cred with pops and race wins, then sell tunes & DM the pros here.",
                       (left + 0.06, 0, -0.47), 0.028, DIM, wordwrap=46)
            return
        self.label("[ GREEN NAME ]  verified pro", (left + 0.06, 0, -0.345), 0.038, GREEN)
        self.label(f"Tunes sold: {bro.tunes_sold}", (right - 0.06, 0, -0.345), 0.032, TEXT, align=TextNode.ARight)
        pro_keys = [p.grant_map for p in game.pros]
        have_n = sum(1 for k in pro_keys if k in bro.unlocked_maps)
        self.label(f"Pro map stages unlocked: {have_n}/{len(pro_keys)}  -  sell tunes to earn the rest.",
                   (left + 0.06, 0, -0.55), 0.028, DIM, wordwrap=52)
