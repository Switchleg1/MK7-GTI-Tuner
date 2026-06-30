from __future__ import annotations

import random

from panda3d.core import TextNode

from library.core.constants import (
    AMBER, BLUE, BOX_LINE, DIM, ED_BAD_REVIEW, GREEN, GREEN_2, GREEN_NAME_CRED, LINE, PANEL,
    PRO_MAPS, RED, SALE_BAD, TEXT, TUNE_SALE, TURBOS, VIOLET, WHITE,
)
from library.core.utils import pick
from library.stages.review_overlay import ReviewOverlay
from library.stages.shop_item import build_catalog
from library.stages.task_base import TaskBase

CENTER, RIGHT = TextNode.ACenter, TextNode.ARight
COLS, ROWS = 2, 3
N_CARDS = COLS * ROWS              # 2x3 grid of cards (the catalog scrolls through them)
ROW_Z = (0.26, 0.045, -0.17)       # the 3 row centres
CARD_HH = 0.105                    # card half-height


class ShopTask(TaskBase):
    """Spend race winnings on parts, shown as a 2x3 grid of cards (one per `ShopItem`:
    thumbnail · name · brief description · owned/equipped tag · Read review · Buy/Equip).
    Turbos are an equippable family (own many, equip one, switch free); bolt-ons are
    cumulative. Once verified GREEN NAME this is also the pro storefront."""

    title = "SHOP"
    key = "shop"

    def build_ui(self):
        game = self.game
        left, right = self.bounds()
        self.items = build_catalog()
        self.scroll = 0
        self.review = ReviewOverlay(self.app)

        self.ui.add_frame("panel", frame_size=(left, right, -0.62, 0.48), border=None)
        self.ui.add_image("emoji-cash", "emoji_cash", (left + 0.10, 0, 0.405), 0.045)
        self.ui.add_text("cash", "", (left + 0.18, 0, 0.40), 0.044, BLUE)

        # ── 2x3 card grid (built once; items bind into slots on scroll) ───────────
        gap = 0.05
        col_w = (right - left - 0.04 - gap) / 2
        hw = col_w / 2
        col_x = (left + 0.02 + hw, left + 0.02 + hw + col_w + gap)
        for i in range(N_CARDS):
            cx, cz = col_x[i % COLS], ROW_Z[i // COLS]
            self.ui.add_frame(f"card{i}-bg", frame_size=(cx - hw, cx + hw, cz - CARD_HH, cz + CARD_HH),
                              color=PANEL, border=BOX_LINE)
            self.ui.add_frame(f"card{i}-thumb", frame_size=(cx - hw + 0.03, cx - hw + 0.18, cz - 0.045, cz + 0.075),
                              color=BLUE, border=None)
            self.ui.add_text(f"card{i}-tag", "", (cx - hw + 0.105, 0, cz + 0.005), 0.030, WHITE, align=CENTER)
            self.ui.add_text(f"card{i}-name", "", (cx - hw + 0.22, 0, cz + 0.05), 0.034, BLUE)
            self.ui.add_text(f"card{i}-own", "", (cx + hw - 0.04, 0, cz + 0.055), 0.024, AMBER, align=RIGHT)
            self.ui.add_text(f"card{i}-desc", "", (cx - hw + 0.22, 0, cz + 0.008), 0.023, DIM, wordwrap=40)
            self.ui.add_button(f"card{i}-rev", "Read review", (cx - 0.39, 0, cz - 0.066), (0.74, 0.058),
                               None, True, VIOLET, 0.030)
            self.ui.add_button(f"card{i}-buy", "Buy", (cx + 0.39, 0, cz - 0.066), (0.74, 0.058),
                               None, True, GREEN_2, 0.030)

        # ── scroll controls (top-right, beside the cash line) ─────────────────────
        self.ui.add_button("scroll-up", "▲", (right - 0.31, 0, 0.405), (0.11, 0.075),
                           lambda: self._scroll(-COLS), True, PANEL, 0.045)
        self.ui.add_text("scroll-pos", "", (right - 0.18, 0, 0.40), 0.026, DIM, align=CENTER)
        self.ui.add_button("scroll-dn", "▼", (right - 0.06, 0, 0.405), (0.11, 0.075),
                           lambda: self._scroll(COLS), True, PANEL, 0.045)

        # ── divider + pro storefront (shown once verified green) ──────────────────
        self.ui.add_frame("green-divider", frame_size=(left + 0.04, right - 0.04, -0.302, -0.299),
                          color=LINE, border=None)
        self.ui.add_button("sell", "Sell a tune  (+$)", (left + 0.32, 0, -0.45), (0.54, 0.10),
                           self.bind(self._sell_tune), True, GREEN_2, is_visible=False)
        for i, pro in enumerate(game.pros):
            self.ui.add_button(f"pro-{pro.handle}", f"Ask {pro.name}", (left + 0.92 + i * 0.42, 0, -0.45),
                               (0.38, 0.10), self.bind(self._ask_pro, pro.handle), is_visible=False)
        self.ui.add_text("lock1", "PRO STOREFRONT - locked", (left + 0.06, 0, -0.36), 0.036, DIM, is_visible=False)
        self.ui.add_text("lock2", "", (left + 0.06, 0, -0.43), 0.030, DIM, wordwrap=44, is_visible=False)
        self.ui.add_text("lock3", "Earn cred with pops and race wins, then sell tunes & DM the pros here.",
                         (left + 0.06, 0, -0.49), 0.028, DIM, wordwrap=46, is_visible=False)
        self.ui.add_text("green1", "[ GREEN NAME ]  verified pro", (left + 0.06, 0, -0.355), 0.038, GREEN, is_visible=False)
        self.ui.add_text("green2", "", (right - 0.06, 0, -0.355), 0.032, TEXT, RIGHT, is_visible=False)
        self.ui.add_text("green3", "", (left + 0.06, 0, -0.56), 0.028, DIM, wordwrap=52, is_visible=False)

    def bind_keys(self):
        self.accept("wheel_up", lambda: self._scroll(-COLS))
        self.accept("wheel_down", lambda: self._scroll(COLS))
        self.accept("arrow_up", lambda: self._scroll(-COLS))
        self.accept("arrow_down", lambda: self._scroll(COLS))

    def exit(self):
        if getattr(self, "review", None) is not None:
            self.review.destroy()
            self.review = None
        super().exit()

    def update_ui(self, left, right):
        bro = self.game.bro
        cash = self.ui.get("cash")
        cash.text(f"SHOP  -  CASH ${round(bro.cash)}")
        cash.color(RED if bro.is_broke() else BLUE)
        self._refresh_cards()
        self._green_section(left, right)

    # ── cards ──────────────────────────────────────────────────────────────────
    def _refresh_cards(self):
        n = len(self.items)
        ceiling = max(0, n - N_CARDS)
        self.scroll = max(0, min(self.scroll, ceiling))
        for i in range(N_CARDS):
            idx = self.scroll + i
            if idx < n:
                self.items[idx].bind_to_slot(self.ui, i, self.game, self._card_action, self._open_review)
            else:
                for part in ("bg", "thumb", "tag", "name", "own", "desc", "buy", "rev"):
                    self.ui.get(f"card{i}-{part}").is_visible(False)
        self.ui.get("scroll-pos").text(f"{self.scroll + 1}-{min(self.scroll + N_CARDS, n)}/{n}")
        self.ui.get("scroll-up").enabled(self.scroll > 0)
        self.ui.get("scroll-dn").enabled(self.scroll < ceiling)

    def _scroll(self, delta: int):
        self.scroll += delta
        self.dirty = True  # re-bind the window on the next redraw

    def _card_action(self, item):
        """Buy (mods + first turbo purchase) or Equip (switch to an owned turbo, free)."""
        game, car = self.game, self.game.car
        if item.is_owned(car):
            if item.category == "turbo" and not item.is_equipped(car):
                self._log_result(car.equip_turbo(item.key))
                self.dirty = True
            return
        if not game.bro.spend(item.price):
            return
        if item.category == "turbo":
            self._log_result(car.buy_turbo(item.key))
            spec = TURBOS[item.key]
            if spec.get("ed_cut"):
                game.log(f"Ed takes his cut of that {spec['name']} sale. He's delighted. Gross.", "warn")
            else:
                game.log(f"{spec['name']} fitted - not a cent to Ed. The crew approves.", "ok")
        else:
            self._log_result(car.set_mod(item.key))  # fully_built trophy polls car.fully_built
        game.dave("shop")
        self.dirty = True

    def _open_review(self, item, slot: int):
        if self.review is None:
            return
        self.review.open(item, self.ui.get(f"card{slot}-rev").pos())

    # ── pro storefront (unchanged) ─────────────────────────────────────────────
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
