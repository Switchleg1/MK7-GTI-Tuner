from __future__ import annotations

from library.core.constants import AMBER, BLUE, EQUIP_FAMILIES, GREEN, GREEN_2, PARTS, VIOLET, WHITE


class ShopItem:
    """One shop entry (a bolt-on mod OR an equippable-family part). The shop task holds a
    list of these and a pool of card *slots*; an item paints itself into a slot
    (``bind_to_slot``) and wires that slot's two buttons back to the task's action / review
    callbacks.

    ``category`` is the **equippable-family** id (mutually exclusive, own many / equip one) --
    "turbo" or "ic" today. Bolt-on mods have ``category=None`` (cumulative: once bought they're
    just on). The actual purchase / fitment lives on ``Car`` (see EQUIP_FAMILIES)."""

    def __init__(self, key, name, blurb, review, price, accent, kind, category=None, image=""):
        self.key = key
        self.name = name
        self.blurb = blurb          # one-line card description
        self.review = review        # full review (the animated overlay)
        self.price = price
        self.accent = accent        # placeholder-tile tint (used when there's no image)
        self.kind = kind            # "mod" | "turbo" | "ic"
        self.category = category    # equippable-family id (== kind for turbo/ic), or None for bolt-ons
        self.image = image          # thumbnail: an IMAGE_FILES key, or "" -> accent placeholder tile

    # -- state queries -----------------------------------------------------
    def is_owned(self, car) -> bool:
        if self.category:           # an equippable family: owned = in that family's owned set
            return self.key in getattr(car, EQUIP_FAMILIES[self.category]["owned"])
        return bool(car.mods.get(self.key))

    def is_equipped(self, car) -> bool:
        if self.category:           # equipped = this variant is the fitted one
            return getattr(car, EQUIP_FAMILIES[self.category]["equipped"]) == self.key
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
        # Thumbnail: a real image if this part carries one, else the accent placeholder
        # tile (rounded ui_box) with the item's initials over it -- the current look.
        thumb = ui.get(f"card{slot}-thumb")
        tag = ui.get(f"card{slot}-tag")
        if self.image:
            thumb.texture(self.image)
            thumb.color(WHITE)          # untinted so the artwork shows true
            tag.text("")
            tag.is_visible(False)
        else:
            thumb.texture("ui_box")
            thumb.color(self.accent)
            tag.text(self.tag())
            tag.is_visible(True)
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
        # (the tag's visibility is set above, per image vs placeholder)
        for part in ("bg", "thumb", "name", "desc", "own", "buy", "rev"):
            ui.get(f"card{slot}-{part}").is_visible(True)


def build_catalog() -> list[ShopItem]:
    """The full shop list, straight off the single ``PARTS`` table: every part becomes a
    card in table order (bolt-on mods, then the intercooler + turbo families). Each part
    row carries its name/blurb/review/price/accent/kind/image; ``category`` is the part's
    ``kind`` for the equippable families (turbo/ic), else None for cumulative bolt-ons."""
    return [
        ShopItem(key, p["name"], p["blurb"], p["review"], p["price"],
                 p.get("accent", BLUE), p["kind"],
                 category=(p["kind"] if p["kind"] in EQUIP_FAMILIES else None),
                 image=p.get("image", ""))
        for key, p in PARTS.items()
    ]
