from __future__ import annotations

import os

from panda3d.core import Filename, PNMImage

from library.core.constants import IMAGE_FILES


def _new(w: int, h: int, bg=(0.0, 0.0, 0.0, 0.0)) -> PNMImage:
    img = PNMImage(w, h)
    img.addAlpha()
    img.fill(bg[0], bg[1], bg[2])
    img.alphaFill(bg[3])
    return img


def _px(img: PNMImage, x: int, y: int, r, g, b, a=1.0):
    if 0 <= x < img.getXSize() and 0 <= y < img.getYSize():
        img.setXelA(x, y, r, g, b, a)


def _disc(img, cx, cy, radius, color):
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                _px(img, x, y, *color)


def _thick_line(img, x0, y0, x1, y1, width, color):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        y = round(y0 + (y1 - y0) * i / steps)
        _disc(img, x, y, width, color)


def _rounded_rect(img, x0, y0, x1, y1, radius, color):
    for y in range(y0, y1):
        for x in range(x0, x1):
            cx = min(max(x, x0 + radius), x1 - radius)
            cy = min(max(y, y0 + radius), y1 - radius)
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius or (x0 + radius <= x < x1 - radius) or (y0 + radius <= y < y1 - radius):
                _px(img, x, y, *color)


def _wallpaper(path):
    w, h = 480, 960
    img = _new(w, h, (0.04, 0.07, 0.09, 1))
    for y in range(h):
        t = y / h
        r, g, b = 0.03 + 0.03 * (1 - t), 0.09 + 0.11 * (1 - t), 0.12 + 0.12 * (1 - t)
        for x in range(w):
            img.setXelA(x, y, r, g, b, 1.0)
    for gx in range(0, w, 40):
        for y in range(h):
            _px(img, gx, y, 0.16, 0.30, 0.34, 1.0)
    for gy in range(0, h, 40):
        for x in range(w):
            _px(img, x, gy, 0.16, 0.30, 0.34, 1.0)
    _disc(img, w // 2, 150, 120, (0.10, 0.45, 0.30, 1.0))
    _disc(img, w // 2, 150, 70, (0.14, 0.60, 0.40, 1.0))
    img.write(Filename.fromOsSpecific(path))


def _app_icon(path):
    s = 128
    img = _new(s, s, (0.0, 0.0, 0.0, 0.0))
    _rounded_rect(img, 6, 6, s - 6, s - 6, 24, (0.05, 0.10, 0.13, 1.0))
    bolt = [(78, 16), (44, 70), (66, 70), (50, 112), (96, 54), (70, 54)]
    for i in range(len(bolt) - 1):
        _thick_line(img, bolt[i][0], bolt[i][1], bolt[i + 1][0], bolt[i + 1][1], 3, (0.22, 1.0, 0.48, 1.0))
    img.write(Filename.fromOsSpecific(path))


def _check(path):
    s = 160
    img = _new(s, s, (0.0, 0.0, 0.0, 0.0))
    _disc(img, s // 2, s // 2, 70, (0.10, 0.55, 0.32, 1.0))
    _disc(img, s // 2, s // 2, 58, (0.16, 0.78, 0.44, 1.0))
    _thick_line(img, 52, 84, 74, 106, 6, (0.96, 1.0, 0.98, 1.0))
    _thick_line(img, 74, 106, 112, 56, 6, (0.96, 1.0, 0.98, 1.0))
    img.write(Filename.fromOsSpecific(path))


def _logo(path):
    w, h = 512, 140
    img = _new(w, h, (0.0, 0.0, 0.0, 0.0))
    _rounded_rect(img, 4, 4, w - 4, h - 4, 18, (0.05, 0.08, 0.10, 1.0))
    stripes = [(0.80, 0.10, 0.13, 1.0), (0.05, 0.05, 0.06, 1.0), (0.80, 0.10, 0.13, 1.0)]
    for i, color in enumerate(stripes):
        x = 36 + i * 30
        _thick_line(img, x, 24, x - 26, h - 24, 9, color)
    _thick_line(img, w - 60, 28, w - 60, h - 28, 7, (0.22, 1.0, 0.48, 1.0))
    img.write(Filename.fromOsSpecific(path))


def build(out_dir: str) -> list[str]:
    builders = {
        "wallpaper": _wallpaper,
        "app_icon": _app_icon,
        "check": _check,
        "logo": _logo,
    }
    written = []
    for key, fn in builders.items():
        path = os.path.join(out_dir, IMAGE_FILES[key])
        fn(path)
        written.append(path)
    return written
