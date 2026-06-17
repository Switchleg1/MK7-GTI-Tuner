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


def _radial_disc(img, cx, cy, radius, inner, outer):
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= radius:
                t = d / radius
                _px(img, x, y, inner[0] * (1 - t) + outer[0] * t, inner[1] * (1 - t) + outer[1] * t, inner[2] * (1 - t) + outer[2] * t, 1.0)


def _ellipse(img, cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                _px(img, x, y, *color)


def _downscale(big, size):
    out = PNMImage(size, size)
    out.addAlpha()
    out.quickFilterFrom(big)
    return out


def _simon(path):
    """Skeptical 'clippy'-style face: round orange head, one raised eyebrow."""
    size, scale = 256, 3
    s = size * scale
    big = _new(s, s, (0, 0, 0, 0))
    cx, cy, radius = s // 2, int(s * 0.52), int(s * 0.44)
    _radial_disc(big, cx, cy, radius, (1.0, 0.84, 0.34), (0.92, 0.55, 0.07))
    eye_dx, eye_y = int(s * 0.155), cy - int(s * 0.02)
    brow = (0.42, 0.26, 0.05, 1.0)
    for sign, squint in ((-1, 1.0), (1, 0.78)):
        ex = cx + sign * eye_dx
        _ellipse(big, ex, eye_y, int(s * 0.092), int(s * 0.108 * squint), (1, 1, 1, 1))
        _disc(big, ex + int(s * 0.012), eye_y + int(s * 0.012), int(s * 0.05), (0.10, 0.10, 0.13, 1))
        _disc(big, ex - int(s * 0.012), eye_y - int(s * 0.018), int(s * 0.018), (1, 1, 1, 0.85))
    # left brow: flat; right brow: raised + arched
    _thick_line(big, cx - eye_dx - int(s * 0.085), eye_y - int(s * 0.10), cx - eye_dx + int(s * 0.07), eye_y - int(s * 0.115), int(s * 0.016), brow)
    _thick_line(big, cx + eye_dx - int(s * 0.075), eye_y - int(s * 0.17), cx + eye_dx + int(s * 0.085), eye_y - int(s * 0.205), int(s * 0.016), brow)
    # skeptical mouth: mostly flat with a slight dip on one side
    my = cy + int(s * 0.21)
    _thick_line(big, cx - int(s * 0.11), my - int(s * 0.01), cx + int(s * 0.02), my, int(s * 0.015), (0.45, 0.25, 0.05, 1))
    _thick_line(big, cx + int(s * 0.02), my, cx + int(s * 0.12), my + int(s * 0.03), int(s * 0.015), (0.45, 0.25, 0.05, 1))
    _downscale(big, size).write(Filename.fromOsSpecific(path))


def _panel(path, w, h, radius, border, fill):
    img = _new(w, h, (0, 0, 0, 0))
    _rounded_rect(img, 1, 1, w - 1, h - 1, radius, border)
    _rounded_rect(img, 5, 5, w - 5, h - 5, max(2, radius - 4), fill)
    img.write(Filename.fromOsSpecific(path))


def _simon_panel(path):
    _panel(path, 540, 430, 30, (0.55, 0.40, 0.96, 1.0), (0.055, 0.072, 0.10, 0.985))


def _simon_button(path):
    _panel(path, 380, 104, 50, (0.55, 0.40, 0.96, 1.0), (0.10, 0.07, 0.15, 0.99))


def _tip_bulb(path):
    s, scale = 64, 3
    big = _new(s * scale, s * scale, (0, 0, 0, 0))
    sc = scale
    _disc(big, 32 * sc, 26 * sc, 17 * sc, (1.0, 0.86, 0.30, 1.0))
    _disc(big, 32 * sc, 26 * sc, 11 * sc, (1.0, 0.95, 0.55, 1.0))
    for bx in (27, 32, 37):
        _thick_line(big, bx * sc, 40 * sc, bx * sc, 48 * sc, 2 * sc, (0.62, 0.64, 0.66, 1.0))
    _thick_line(big, 27 * sc, 50 * sc, 37 * sc, 50 * sc, 2 * sc, (0.50, 0.52, 0.54, 1.0))
    _downscale(big, s).write(Filename.fromOsSpecific(path))


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
        "simon": _simon,
        "simon_panel": _simon_panel,
        "simon_button": _simon_button,
        "tip_bulb": _tip_bulb,
    }
    written = []
    for key, fn in builders.items():
        path = os.path.join(out_dir, IMAGE_FILES[key])
        fn(path)
        written.append(path)
    return written
