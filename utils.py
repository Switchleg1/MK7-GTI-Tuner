from __future__ import annotations

import random

from panda3d.core import Vec4


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pick(items):
    return random.choice(items)


def rgba(hex_color: str, alpha: float = 1.0) -> Vec4:
    h = hex_color.lstrip("#")
    return Vec4(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha)
