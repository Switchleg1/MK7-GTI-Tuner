from __future__ import annotations

import random

from panda3d.core import TextNode

from library.core.constants import (
    BLUE, DIM, ED_BAD_REVIEW, GREEN, GREEN_2, GREEN_NAME_CRED, LINE, MODS, PRO_MAPS, RED,
    SALE_BAD, TEXT, TUNE_SALE,
)
from library.core.utils import pick
from library.stages.task_base import TaskBase


class ShopTask(TaskBase):
    """Spend race winnings on mods. Once you hit verified GREEN NAME, this is also
    your pro storefront: sell tunes for cash and DM the pros (Ed/Dave) for stages."""

    title = "SHOP"
    key = "shop"

    def build_ui(self):
        game = self.game
        left, right = self.bounds()
        self.ui.add_frame("panel", frame_size=(left, right, -0.62, 0.48), border=None)
        self.ui.add_image("emoji-cash", "emoji_cash", (left + 0.10, 0, 0.405), 0.045)
        self.ui.add_frame("green-divider", frame_size=(left + 0.04, right - 0.04, -0.275, -0.272),
                          color=LINE, border=None)
        for index, (mod_id, name, cost, _desc) in enumerate(MODS):
            row, col = divmod(index, 2)
            self.ui.add_button(f"mod-{mod_id}", name, (left + 0.28 + col * 0.82, 0, 0.25 - row * 0.12),
                               (0.72, 0.08), self.bind(self._buy_mod, mod_id))
        # Pro storefront: built now, shown only once the bro goes verified green name.
        self.ui.add_button("sell", "Sell a tune  (+$)", (left + 0.32, 0, -0.45), (0.54, 0.10),
                           self.bind(self._sell_tune), True, GREEN_2, is_visible=False)
        for i, pro in enumerate(game.pros):
            self.ui.add_button(f"pro-{pro.handle}", f"Ask {pro.name}", (left + 0.92 + i * 0.42, 0, -0.45),
                               (0.38, 0.10), self.bind(self._ask_pro, pro.handle), is_visible=False)
        self.ui.add_text("cash", "", (left + 0.18, 0, 0.40), 0.044, BLUE)
        self.ui.add_text("lock1", "PRO STOREFRONT - locked", (left + 0.06, 0, -0.34), 0.036, DIM, is_visible=False)
        self.ui.add_text("lock2", "", (left + 0.06, 0, -0.41), 0.030, DIM, wordwrap=44, is_visible=False)
        self.ui.add_text("lock3", "Earn cred with pops and race wins, then sell tunes & DM the pros here.",
                         (left + 0.06, 0, -0.47), 0.028, DIM, wordwrap=46, is_visible=False)
        self.ui.add_text("green1", "[ GREEN NAME ]  verified pro", (left + 0.06, 0, -0.345), 0.038, GREEN, is_visible=False)
        self.ui.add_text("green2", "", (right - 0.06, 0, -0.345), 0.032, TEXT, TextNode.ARight, is_visible=False)
        self.ui.add_text("green3", "", (left + 0.06, 0, -0.55), 0.028, DIM, wordwrap=52, is_visible=False)

    def update_ui(self, left, right):
        game = self.game
        bro = game.bro
        cash = self.ui.get("cash")
        cash.text(f"SHOP  -  CASH ${round(bro.cash)}")
        cash.color(RED if bro.is_broke() else BLUE)
        for mod_id, name, cost, _desc in MODS:
            owned = game.car.mods[mod_id]
            button = self.ui.get(f"mod-{mod_id}")
            button.text(f"{name} - {'owned' if owned else '$' + str(cost)}")
            button.enabled(not owned and bro.cash >= cost)
        self._green_section(left, right)

    def _green_section(self, left, right):
        game, bro = self.game, self.game.bro
        green = bro.green_name
        self.ui.get("sell").is_visible(green)
        for pro in game.pros:
            have = pro.grant_map in bro.unlocked_maps
            button = self.ui.get(f"pro-{pro.handle}")
            button.is_visible(green)
            button.text(f"Ask {pro.name}" + (" (got it)" if have else ""))
            button.enabled(not have)
        for key in ("lock1", "lock2", "lock3"):
            self.ui.get(key).is_visible(not green)
        self.ui.get("lock2").text(f"Go verified GREEN NAME at {GREEN_NAME_CRED} cred  (you: {round(bro.cred)}).")
        for key in ("green1", "green2", "green3"):
            self.ui.get(key).is_visible(green)
        self.ui.get("green2").text(f"Tunes sold: {bro.tunes_sold}")
        pro_keys = [p.grant_map for p in game.pros]
        have_n = sum(1 for k in pro_keys if k in bro.unlocked_maps)
        self.ui.get("green3").text(f"Pro map stages unlocked: {have_n}/{len(pro_keys)}  -  sell tunes to earn the rest.")

    def _buy_mod(self, mod_id: str):
        game = self.game
        cost = next(item[2] for item in MODS if item[0] == mod_id)
        if game.car.mods[mod_id] or not game.bro.spend(cost):
            return
        self._log_result(game.car.set_mod(mod_id))  # fully_built trophy is polled off car.fully_built
        game.dave("shop")

    def _sell_tune(self):
        """Green-name income: flog a tune to a random user."""
        game = self.game
        if not game.bro.green_name:
            return
        if random.random() < TUNE_SALE["bad_chance"]:
            game.bro.add_cred(-4)
            game.hurt_bro(ED_BAD_REVIEW)
            game.log(pick(SALE_BAD), "warn")
            return
        whp = game.car.compute()["whp"]
        pay = int(TUNE_SALE["base"] + max(0.0, whp - 210) * TUNE_SALE["per_whp"])
        game.bro.earn(pay)
        game.bro.add_cred(TUNE_SALE["cred"])
        game.bro.tunes_sold += 1  # first_sale / tune_mill trophies are polled off tunes_sold
        game.log(f"sold a tune for ${pay}  ({game.bro.tunes_sold} sold)", "ok")
        game.dave("sell")
        game.maybe_green()

    def _ask_pro(self, handle: str):
        """DM a pro for a pro-only map stage from the shop storefront."""
        game = self.game
        if not game.bro.green_name:
            return
        pro = next((p for p in game.pros if p.handle == handle), None)
        if pro is None:
            return
        if pro.grant_map in game.bro.unlocked_maps:
            game.log(f"{pro.name}: you already have {PRO_MAPS[pro.grant_map]['name']}.", "info")
        elif game.bro.tunes_sold >= pro.min_tunes:
            game.bro.unlock_map(pro.grant_map)  # pro_network trophy is polled off bro.pro_maps
            game.log(f"{pro.name} hooked you up: {PRO_MAPS[pro.grant_map]['name']} unlocked.", "ok")
            game.dave("pro")
        else:
            need = pro.min_tunes - game.bro.tunes_sold
            game.log(f"{pro.name}: {pro.chatter()} (sell {need} more tune{'s' if need != 1 else ''} first)", "warn")
