from __future__ import annotations

from library.core.constants import (
    AMBER, BLUE, GREEN, GREEN_2, MOD_REVIEWS, MODS, RED, TURBOS, VIOLET,
)

# Accent colour per turbo (the others fall back to BLUE for bolt-on mods).
_TURBO_ACCENT = {"is38": BLUE, "cts_jb600": RED, "vortex": VIOLET, "arashi_3076": GREEN}


class ShopItem:
    """One shop entry (a bolt-on mod OR a turbo variant). The shop task holds a list of
    these and a pool of card *slots*; an item paints itself into a slot (``bind_to_slot``)
    and wires that slot's two buttons back to the task's action / review callbacks.

    ``category`` marks an **equippable family** (mutually exclusive, own many / equip one) --
    "turbo" today, "intercooler" next. Bolt-on mods have ``category=None`` (cumulative: once
    bought they're just on). The actual purchase / fitment lives on ``Car``."""

    def __init__(self, key, name, blurb, review, price, accent, kind, category=None, image=None):
        self.key = key
        self.name = name
        self.blurb = blurb          # one-line card description
        self.review = review        # full review (the animated overlay)
        self.price = price
        self.accent = accent        # thumbnail tint
        self.kind = kind            # "mod" | "turbo"
        self.category = category    # equippable-family id, or None for cumulative bolt-ons
        self.image = image          # optional IMAGE_FILES key; None -> placeholder tile

    # -- state queries -----------------------------------------------------
    def is_owned(self, car) -> bool:
        if self.category == "turbo":
            return self.key in car.owned_turbos
        return bool(car.mods.get(self.key))

    def is_equipped(self, car) -> bool:
        if self.category == "turbo":
            return car.turbo == self.key
        return self.is_owned(car)   # cumulative mods are always "on" once owned

    def tag(self) -> str:
        """Short placeholder-thumbnail label until real art is dropped in."""
        return self.name.split()[0].upper()[:4]

    def owned_label(self, car):
        """(text, colour) for the corner tag: equipped / owned / nothing."""
        if not self.is_owned(car):
            return "", AMBER
        if self.category and self.is_equipped(car):
            return "[EQUIPPED]", GREEN
        if self.category:
            return "[OWNED]", AMBER
        return "[OWNED]", GREEN

    def action(self, car, bro):
        """(label, enabled, colour, mode) for the Buy/Equip button. mode is "buy" |
        "equip" | "none" (owned + already equipped / non-equippable)."""
        if not self.is_owned(car):
            return f"Buy  ${self.price}", bro.cash >= self.price, GREEN_2, "buy"
        if self.category and not self.is_equipped(car):
            return "Equip", True, VIOLET, "equip"
        if self.category:
            return "Equipped", False, GREEN_2, "none"
        return "Owned", False, GREEN_2, "none"

    # -- paint into a card slot --------------------------------------------
    def bind_to_slot(self, ui, slot: int, game, on_action, on_review):
        """Fill card *slot*'s widgets with this item and point its action / Read-review
        buttons at the task callbacks. Card widgets are keyed ``card{slot}-*`` (built once
        by the task)."""
        car, bro = game.car, game.bro
        ui.get(f"card{slot}-name").text(self.name)
        ui.get(f"card{slot}-desc").text(self.blurb)
        ui.get(f"card{slot}-thumb").color(self.accent)
        ui.get(f"card{slot}-tag").text(self.tag())
        own_text, own_color = self.owned_label(car)
        own = ui.get(f"card{slot}-own")
        own.text(own_text)
        own.color(own_color)
        label, enabled, color, _mode = self.action(car, bro)
        buy = ui.get(f"card{slot}-buy")
        buy.text(label)
        buy.enabled(enabled)
        buy.color(color)
        buy.command_fn(lambda: on_action(self))
        ui.get(f"card{slot}-rev").command_fn(lambda: on_review(self, slot))
        for part in ("bg", "thumb", "tag", "name", "desc", "own", "buy", "rev"):
            ui.get(f"card{slot}-{part}").is_visible(True)


def build_catalog() -> list[ShopItem]:
    """The full shop list: the bolt-on mods (the ``MODS`` rows, minus the ``turbo`` bool
    anchor) then the turbo family (``TURBOS``). Reviews come from ``MOD_REVIEWS`` /
    each turbo's ``review``."""
    items: list[ShopItem] = []
    for mod_id, name, cost, blurb in MODS:
        if mod_id == "turbo":
            continue  # the turbo *family* is the TURBOS entries below, not this bool anchor
        items.append(ShopItem(mod_id, name, blurb, MOD_REVIEWS.get(mod_id, ""), cost, BLUE, "mod"))
    for turbo_id, spec in TURBOS.items():
        items.append(ShopItem(turbo_id, spec["name"], spec["blurb"], spec["review"], spec["price"],
                              _TURBO_ACCENT.get(turbo_id, BLUE), "turbo", category="turbo"))
    return items
