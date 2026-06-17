from __future__ import annotations

from library.core.constants import BLUE, MODS
from library.stages.task_base import TaskBase


class ShopTask(TaskBase):
    """Spend race winnings on mods that change power, grip, weight and noise."""

    title = "SHOP"
    key = "shop"

    def build_ui(self, left, right):
        game = self.game
        self.frame((left, right, -0.62, 0.48), border=None)
        self.image("emoji_cash", (left + 0.10, 0, 0.405), 0.045)
        self.label(f"SHOP  -  CASH ${round(game.bro.cash)}", (left + 0.18, 0, 0.40), 0.044, BLUE)
        for index, (mod_id, name, cost, _desc) in enumerate(MODS):
            row, col = divmod(index, 2)
            x = left + 0.28 + col * 0.82
            y = 0.25 - row * 0.12
            label = f"{name} - {'owned' if game.car.mods[mod_id] else '$' + str(cost)}"
            self.button(label, (x, 0, y), (0.72, 0.08), self.bind(game.buy_mod, mod_id), not game.car.mods[mod_id] and game.bro.cash >= cost)
