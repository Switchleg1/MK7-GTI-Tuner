#!/usr/bin/env python3
"""MK7 GTI Tuner - pygame edition.

The first prototype used tkinter widgets. This version moves the project into
a game-style render/update/input loop so the UI, animation, particles, and
eventually 3D graphics can grow from the same foundation.
"""

from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass

try:
    import pygame
except ModuleNotFoundError as exc:
    print("pygame is required. Run build.bat or install requirements.txt first.")
    raise exc


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pick(items):
    return random.choice(items)


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


BG = rgb("#070a0d")
PANEL = rgb("#11161b")
PANEL_2 = rgb("#161d24")
PANEL_DARK = rgb("#0c1217")
LINE = rgb("#22303b")
LINE_SOFT = rgb("#15202a")
TEXT = rgb("#cfe3ee")
DIM = rgb("#7d93a3")
MUTED = rgb("#41535f")
GREEN = rgb("#36e07a")
GREEN_2 = rgb("#0f7a3e")
AMBER = rgb("#ffb338")
RED = rgb("#ff4d52")
BLUE = rgb("#4fb6ff")
VIOLET = rgb("#b58bff")
BLACK = rgb("#060809")
WHITE = rgb("#f2fbff")

WIDTH = 1280
HEIGHT = 720
TRACK_M = 402.336
GEAR_RATIOS = [3.6, 2.1, 1.43, 1.03, 0.84, 0.69]
FINAL_DRIVE = 3.65
TIRE_CIRC = 1.96


FUEL = {
    "91": {"head": 0, "pwr": 0},
    "93": {"head": 2, "pwr": 6},
    "E30": {"head": 5, "pwr": 18},
    "E85": {"head": 8.5, "pwr": 32},
}

PRESETS = {
    "stock": {"boost": 18.0, "timing": 10.0, "lambda": 0.85, "fuel": "91", "of": 8.0, "or": 6.0, "th": 5.0, "name": "Stock"},
    "stage1": {"boost": 22.0, "timing": 13.0, "lambda": 0.83, "fuel": "93", "of": 30.0, "or": 28.0, "th": 25.0, "name": "Stage 1"},
    "stage2": {"boost": 24.5, "timing": 14.0, "lambda": 0.82, "fuel": "E30", "of": 45.0, "or": 42.0, "th": 40.0, "name": "Stage 2 E30"},
    "crackle": {"boost": 23.0, "timing": 13.0, "lambda": 0.84, "fuel": "E30", "of": 95.0, "or": 92.0, "th": 85.0, "name": "Crackle Monster"},
}

MODS = [
    ("intake", "Cold Air Intake", 120, "+6 whp, quicker spool."),
    ("dp", "Catless Downpipe", 250, "+12 whp and much louder bangs. Cops notice fast."),
    ("fmic", "Front-Mount Intercooler", 300, "Cooler charge: more knock headroom and lower EGT."),
    ("clutch", "Stage 2 Clutch + LSD", 450, "Hooks hard off the line for drag launches."),
    ("wheels", "Lightweight Wheels", 200, "Less rotating weight, quicker everywhere."),
    ("fuel", "Port Injection + LPFP", 700, "Feeds E85 safely at high boost."),
    ("turbo", "Hybrid Turbo IS38+", 900, "Raises the boost ceiling with big top-end."),
]

RIVALS = [
    {"name": "Stock Civic", "whp": 158, "weight": 1280, "grip": 0.90, "awd": False, "purse": 120, "color": rgb("#9fb3c0")},
    {"name": "Civic Si", "whp": 208, "weight": 1300, "grip": 0.92, "awd": False, "purse": 230, "color": rgb("#e6e6e6")},
    {"name": "WRX STI", "whp": 300, "weight": 1520, "grip": 1.18, "awd": True, "purse": 480, "color": rgb("#3a6ad6")},
    {"name": "BMW M2", "whp": 385, "weight": 1560, "grip": 1.00, "awd": False, "purse": 850, "color": rgb("#222222")},
    {"name": "Rival Shop Mk7", "whp": 365, "weight": 1370, "grip": 1.06, "awd": False, "purse": 1600, "color": rgb("#e7232b")},
]

REPS = [(0, "Civic Bait"), (60, "Cars & Coffee Regular"), (160, "Local Legend"), (340, "Wanted by the HOA")]

TABS = [
    ("bench", "STEP 1", "BENCH", "plug"),
    ("maps", "STEP 2", "MAPS", "map"),
    ("dyno", "STEP 3", "DYNO", "chart"),
    ("street", "STEP 4", "STREET", "fire"),
    ("race", "EARN", "RACE", "flag"),
    ("shop", "SPEND", "SHOP", "wrench"),
]


def default_tune() -> dict:
    return {"boost": 20.0, "timing": 12.0, "lambda": 0.83, "fuel": "93", "of": 35.0, "or": 30.0, "th": 25.0, "name": "Your Tune"}


def clone_tune(tune: dict) -> dict:
    return dict(tune)


def pop_score(tune: dict) -> float:
    return clamp(tune["of"] * 0.42 + tune["or"] * 0.42 + tune["th"] * 0.16, 0, 100)


def rep_title(cred: float) -> str:
    title = REPS[0][1]
    for value, name in REPS:
        if cred >= value:
            title = name
    return title


def compute_tune(tune: dict, mods: dict) -> dict:
    fuel = FUEL[tune["fuel"]]
    headroom = fuel["head"] + (2 if mods["fmic"] else 0) + (3 if mods["fuel"] else 0)
    knock_idx = (tune["boost"] - 18) * 0.85 + (tune["timing"] - 9) * 1.25 + (tune["lambda"] - 0.82) * 14 - headroom
    kr = max(0, knock_idx) * 1.1
    effective_timing = max(2, tune["timing"] - kr)
    whp = (
        210
        + (tune["boost"] - 18) * 7.6
        + (effective_timing - 9) * 3.8
        + fuel["pwr"]
        - abs(tune["lambda"] - 0.83) * 40
        + (6 if mods["intake"] else 0)
        + (12 if mods["dp"] else 0)
        + ((tune["boost"] - 18) * 2.5 if mods["turbo"] else 0)
    )
    whp = clamp(whp, 160, 640)
    egt = (
        720
        + (tune["boost"] - 18) * 9
        + kr * 12
        + (tune["lambda"] - 0.82) * 220
        + tune["of"] * 1.4
        + tune["or"] * 1.7
        - (45 if mods["fmic"] else 0)
        - (25 if mods["turbo"] else 0)
    )
    pop = pop_score(tune)
    rel = (
        100
        - max(0, knock_idx) * 6
        - max(0, tune["boost"] - (27 if mods["turbo"] else 24)) * 5
        - max(0, egt - 950) * 0.13
        - max(0, tune["lambda"] - 0.86) * (40 if mods["fuel"] else 140)
        - pop * 0.16
        + (6 if mods["fmic"] else 0)
    )
    rel = clamp(rel, 0, 100)
    blown = (knock_idx > 7 and tune["lambda"] > 0.86 and not mods["fuel"]) or egt > 1085 or (tune["boost"] > (29 if mods["turbo"] else 26.5) and rel < 22)
    return {"whp": whp, "KR": kr, "knockIdx": knock_idx, "egt": egt, "rel": rel, "pop": pop, "blown": blown}


def dyno_curve(peak_whp: float) -> list[dict]:
    points = []
    max_pw = 0
    for rpm in range(2200, 6801, 100):
        spool = clamp((rpm - 2100) / 1300, 0, 1)
        mid = math.exp(-((rpm - 4300) / 2400) ** 2)
        top = clamp(1 - (rpm - 5600) / 3600, 0.55, 1)
        tq = 100 * spool * (0.55 + 0.55 * mid) * top
        pw = tq * rpm / 5252
        points.append({"rpm": rpm, "tq": tq, "pw": pw})
        max_pw = max(max_pw, pw)
    scale = peak_whp / max_pw if max_pw else 1
    for point in points:
        point["tq"] *= scale
        point["pw"] *= scale
    return points


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: callable | None
    enabled: bool = True
    kind: str = "normal"
    icon: str = ""
    sub: str = ""
    hold: str = ""


@dataclass
class Slider:
    rect: pygame.Rect
    key: str
    low: float
    high: float
    step: float


class MK7Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SIMOS BENCH - MK7 GTI Tuner")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.mouse = (0, 0)
        self.buttons: list[Button] = []
        self.sliders: list[Slider] = []
        self.drag_slider: str | None = None
        self.holding = ""

        self.fonts = {
            "xs": pygame.font.SysFont("consolas", 14),
            "sm": pygame.font.SysFont("consolas", 17),
            "md": pygame.font.SysFont("consolas", 21, bold=True),
            "lg": pygame.font.SysFont("consolas", 28, bold=True),
            "xl": pygame.font.SysFont("consolas", 42, bold=True),
        }

        self.connected = False
        self.read = False
        self.patched = False
        self.flashed = False
        self.switch_patch = False
        self.dirty = False
        self.tune = default_tune()
        self.flashed_tune = None
        self.slots = [clone_tune(PRESETS["stock"]), None, None, None]
        self.active_slot = 0
        self.cred = 0.0
        self.karen = 0.0
        self.cash = 750
        self.bangs = 0
        self.switches = 0
        self.cops_active = False
        self.throttle_lock = False
        self.mods = {mod[0]: False for mod in MODS}
        self.unlocked_rival = 0
        self.achievements = set()
        self.unlocked_tabs = {"bench"}
        self.tab = "bench"
        self.logs: list[tuple[str, str, str]] = []
        self.simon_tick = 0
        self.simon_open = False
        self.simon_current = None

        self.rpm = 850.0
        self.throttle = 0.0
        self.two_step = False
        self.blip_until = 0.0
        self.particles = []

        self.dyno_points = dyno_curve(210)
        self.dyno_result = None
        self.dyno_start = 0.0
        self.dyno_progress = 1.0
        self.dyno_running = False
        self.grade = ""
        self.results = {"hp": "-", "tq": "-", "kr": "-", "egt": "-", "rel": "-", "pop": "-"}

        self.selected_rival = 0
        self.race = None
        self.race_result = ""
        self.drag_particles = []

        self.log("SimosTools bench - MK7 GTI - Pops & Bangs Edition", "violet")
        self.log("Step 1: connect -> read -> patch. Then build maps & flash.", "info")
        self.log("Then RACE for cash and SPEND it in the shop. Get loud.", "dim")

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def log(self, message: str, kind: str = "dim"):
        self.logs.append((time.strftime("%H:%M:%S"), message, kind))
        self.logs = self.logs[-80:]

    def achievement(self, label: str):
        if label in self.achievements:
            return
        self.achievements.add(label)
        self.log(f"ACHIEVEMENT: {label}", "ok")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((max(1024, event.w), max(640, event.h)), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
                if self.drag_slider:
                    self.set_slider_from_mouse(self.drag_slider, event.pos[0])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse = event.pos
                if self.handle_slider_down(event.pos):
                    continue
                self.handle_button_down(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse = event.pos
                self.drag_slider = None
                if self.holding == "throttle":
                    self.set_throttle(0)
                self.holding = ""
            elif event.type == pygame.KEYDOWN:
                self.handle_key_down(event)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.tab == "street":
                    self.set_throttle(0)

    def handle_key_down(self, event):
        if event.key == pygame.K_ESCAPE:
            self.running = False
        if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]:
            idx = event.key - pygame.K_1
            if idx < len(TABS):
                self.go_tab(TABS[idx][0])
        if event.key == pygame.K_SPACE:
            if self.tab == "street":
                self.set_throttle(1)
            elif self.tab == "race":
                self.race_key()
        if self.tab == "street" and event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
            self.select_slot(event.key - pygame.K_1, True)

    def handle_button_down(self, pos):
        for button in reversed(self.buttons):
            if button.enabled and button.rect.collidepoint(pos):
                if button.hold:
                    self.holding = button.hold
                    if button.hold == "throttle":
                        self.set_throttle(1)
                elif button.action:
                    button.action()
                return True
        return False

    def handle_slider_down(self, pos) -> bool:
        for slider in reversed(self.sliders):
            if slider.rect.inflate(0, 18).collidepoint(pos):
                self.drag_slider = slider.key
                self.set_slider_from_mouse(slider.key, pos[0])
                return True
        return False

    def set_slider_from_mouse(self, key: str, x: int):
        slider = next((item for item in self.sliders if item.key == key), None)
        if not slider:
            return
        ratio = clamp((x - slider.rect.left) / slider.rect.width, 0, 1)
        raw = slider.low + ratio * (slider.high - slider.low)
        value = round(raw / slider.step) * slider.step
        if key in ("of", "or", "th"):
            value = round(value)
        self.tune[key] = value
        self.mark_dirty()

    def update(self, dt: float):
        now = time.perf_counter()
        if self.blip_until and now < self.blip_until:
            self.set_throttle(1, quiet=True)
        elif self.blip_until and now >= self.blip_until:
            self.blip_until = 0
            self.set_throttle(0)

        if self.two_step and self.throttle > 0.5:
            target = 4200 + math.sin(now * 30) * 350
        else:
            target = 850 + self.throttle * (7000 - 850)
        rate = 5.5 if target > self.rpm and self.throttle > 0.4 else 4.3
        self.rpm += (target - self.rpm) * clamp(dt * rate, 0, 1)
        self.rpm = clamp(self.rpm, 700, 7200)

        if self.two_step and self.throttle > 0.5 and random.random() < 0.08:
            self.spawn_flames(self.active_pop(), 1)
        if not self.cops_active and self.throttle < 0.1:
            self.karen = clamp(self.karen - dt * 5, 0, 100)

        for p in list(self.particles):
            p["life"] -= dt
            p["x"] += p["vx"] * dt * 60
            p["y"] += p["vy"] * dt * 60
            p["vy"] += 0.08 * dt * 60
            p["vx"] *= 0.985
            p["size"] *= 0.985
            if p["life"] <= 0:
                self.particles.remove(p)

        if self.dyno_running:
            self.dyno_progress = clamp((now - self.dyno_start) / 2.5, 0, 1)
            self.rpm = 2200 + (6800 - 2200) * self.dyno_progress
            if self.dyno_progress >= 1:
                self.finish_dyno()

        self.update_race(dt)

    def set_throttle(self, value: float, quiet: bool = False):
        if self.throttle_lock:
            value = 0
        old = self.throttle
        self.throttle = value
        if not quiet and old > 0.25 and value == 0 and self.rpm > 3000:
            intensity = clamp(self.active_pop() * (0.6 + self.rpm / 7200 * 0.7), 0, 100)
            count = max(2, round(3 + intensity / 4))
            self.spawn_flames(intensity, count)
            self.log(f"lift-off overrun: {count} pops", "ok" if intensity > 50 else "dim")

    def add_cash(self, amount: float):
        self.cash = max(0, round(self.cash + amount))

    def active_tune(self):
        return self.slots[self.active_slot] or self.flashed_tune or self.tune

    def active_pop(self):
        return pop_score(self.active_tune())

    def pop_mult(self):
        return 1.4 if self.mods["dp"] else 1.0

    def mark_dirty(self):
        if self.flashed:
            self.dirty = True

    def go_tab(self, tab: str):
        if tab in self.unlocked_tabs:
            self.tab = tab

    def draw(self):
        self.buttons = []
        self.sliders = []
        self.draw_background()
        self.draw_header()
        self.draw_tabs()
        content = pygame.Rect(20, 212, self.screen.get_width() - 40, self.screen.get_height() - 240)
        if self.tab == "bench":
            self.draw_bench(content)
        elif self.tab == "maps":
            self.draw_maps(content)
        elif self.tab == "dyno":
            self.draw_dyno(content)
        elif self.tab == "street":
            self.draw_street(content)
        elif self.tab == "race":
            self.draw_race(content)
        elif self.tab == "shop":
            self.draw_shop(content)
        self.draw_footer()
        self.draw_simon_layer()
        pygame.display.flip()

    def draw_background(self):
        w, h = self.screen.get_size()
        self.screen.fill(BG)
        for y in range(0, h, 4):
            col = (9, 16, 20) if (y // 4) % 2 == 0 else (6, 10, 13)
            pygame.draw.line(self.screen, col, (0, y), (w, y))
        for i in range(9):
            radius = 500 - i * 42
            alpha = 14 - i
            surf = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (22, 48, 61, max(0, alpha)), surf.get_rect())
            self.screen.blit(surf, (w * 0.58 - radius, -radius * 0.36))

    def draw_header(self):
        w = self.screen.get_width()
        rect = pygame.Rect(20, 18, w - 40, 90)
        self.round_rect(rect, PANEL, 14, LINE, 2)
        self.text("SIMOS BENCH", (40, 42), GREEN, "xl")
        self.text("MK7 GTI  .  EA888  .  SIMOS18.1  .  POPS & BANGS  .  CAREER", (40, 82), DIM, "sm")
        badges = [
            ("cash", str(self.cash), GREEN),
            ("ECU", "FLASHED" if self.flashed else "UNLOCKED" if self.patched else "LOCKED", GREEN if self.flashed else AMBER if self.patched else TEXT),
            ("MAP", f"{self.active_slot + 1} . {self.active_tune().get('name', 'Stock') if self.active_tune() else '-'}", TEXT),
            ("REP", rep_title(self.cred), TEXT),
            ("sound", "visual", TEXT),
        ]
        x = w - 40
        for label, value, color in reversed(badges):
            width = max(84, self.fonts["sm"].size(f"{label}: {value}")[0] + 28)
            x -= width
            self.draw_badge(pygame.Rect(x, 46, width, 38), label, value, color)
            x -= 10

    def draw_badge(self, rect, label, value, color):
        border = GREEN_2 if label == "cash" else LINE
        self.round_rect(rect, PANEL_DARK, 18, border, 2)
        prefix = "$" if label == "cash" else label.upper() + ":"
        self.text(prefix, (rect.x + 14, rect.y + 10), DIM if label != "cash" else GREEN, "sm")
        self.text(value, (rect.x + 14 + self.fonts["sm"].size(prefix + " ")[0], rect.y + 10), color, "sm", bold=True)

    def draw_tabs(self):
        w = self.screen.get_width()
        margin = 20
        gap = 8
        y = 126
        tile_w = (w - margin * 2 - gap * (len(TABS) - 1)) // len(TABS)
        for i, (key, step, label, icon) in enumerate(TABS):
            rect = pygame.Rect(margin + i * (tile_w + gap), y, tile_w, 70)
            enabled = key in self.unlocked_tabs
            active = key == self.tab
            self.add_button(rect, label, lambda k=key: self.go_tab(k), enabled=enabled, kind="tab_active" if active else "tab", icon=self.icon_text(icon), sub=step)
            self.draw_button(self.buttons[-1], force_active=active)

    def draw_footer(self):
        w, h = self.screen.get_size()
        msg = "Parody bench sim. Real Simos18 flashing can brick an ECU, overrun fueling melts cats & turbos, and street racing is a great way to lose your license."
        self.text_center(msg, (w // 2, h - 28), DIM, "sm")

    def draw_simon_layer(self):
        w, h = self.screen.get_size()
        pill = pygame.Rect(w - 294, h - 78, 268, 58)
        if self.simon_open and self.simon_current:
            popup_w = min(650, w - 44)
            popup_h = 306
            popup = pygame.Rect(w - popup_w - 28, max(116, pill.y - popup_h - 14), popup_w, popup_h)
            self.draw_simon_popup(popup)
            self.buttons.append(Button(popup, "", lambda: None, True, "block"))
            close = pygame.Rect(popup.right - 58, popup.y + 18, 38, 38)
            self.buttons.append(Button(close, "X", self.close_simon, True, "close"))
            self.draw_close_button(close)
        self.buttons.append(Button(pill, "Ask Simon", self.ask_simon, True, "simon"))
        self.draw_simon_button(pill)

    def draw_simon_button(self, rect):
        hovered = rect.collidepoint(self.mouse)
        shadow = pygame.Surface((rect.w + 12, rect.h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 130), shadow.get_rect(), border_radius=32)
        self.screen.blit(shadow, (rect.x - 6, rect.y - 2))
        fill = rgb("#241636") if not hovered else rgb("#332047")
        border = rgb("#d2d0d5") if not hovered else rgb("#ffffff")
        self.round_rect(rect, fill, 29, border, 2)
        self.round_rect(rect.inflate(-5, -5), rgb("#1d102b"), 25, rgb("#6b4fa0"), 1)
        self.draw_simon_face((rect.x + 42, rect.centery), 15)
        self.text("Ask Simon", (rect.x + 78, rect.y + 18), rgb("#d7cde9"), "lg")

    def draw_simon_popup(self, rect):
        shadow = pygame.Surface((rect.w + 18, rect.h + 18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 150), shadow.get_rect(), border_radius=24)
        self.screen.blit(shadow, (rect.x - 8, rect.y + 4))
        self.round_rect(rect, rgb("#111820"), 22, rgb("#8f63d1"), 2)
        self.draw_simon_face((rect.x + 62, rect.y + 62), 30)
        self.text("SIMON", (rect.x + 112, rect.y + 42), VIOLET, "lg", letter_spacing=6)
        self.text("master tuner  .  zero chill", (rect.x + 112, rect.y + 78), DIM, "sm", letter_spacing=4)
        y = rect.y + 124
        y = self.wrap(self.simon_current["roast"], rect.x + 34, y, rect.w - 68, rgb("#ffd0a0"), "md")
        y += 12
        pygame.draw.line(self.screen, LINE, (rect.x + 34, y), (rect.right - 34, y), 2)
        y += 28
        self.draw_tip_bulb(rect.x + 48, y + 8)
        self.wrap(self.simon_current["tip"], rect.x + 78, y, rect.w - 112, rgb("#9fe9bf"), "md")

    def draw_close_button(self, rect):
        hovered = rect.collidepoint(self.mouse)
        self.round_rect(rect, rgb("#0c1217") if not hovered else rgb("#16222b"), 12, LINE if not hovered else rgb("#8f63d1"), 2)
        x0, y0 = rect.x + 11, rect.y + 11
        x1, y1 = rect.right - 11, rect.bottom - 11
        pygame.draw.line(self.screen, TEXT, (x0, y0), (x1, y1), 4)
        pygame.draw.line(self.screen, TEXT, (x1, y0), (x0, y1), 4)

    def draw_tip_bulb(self, x, y):
        pygame.draw.circle(self.screen, rgb("#ffd86b"), (x, y), 9)
        pygame.draw.circle(self.screen, rgb("#fff5b3"), (x - 3, y - 4), 3)
        pygame.draw.rect(self.screen, rgb("#c78b2b"), (x - 5, y + 8, 10, 6), border_radius=2)
        pygame.draw.line(self.screen, rgb("#ffd86b"), (x - 12, y - 2), (x - 18, y - 6), 2)
        pygame.draw.line(self.screen, rgb("#ffd86b"), (x + 12, y - 2), (x + 18, y - 6), 2)

    def draw_simon_face(self, center, radius):
        x, y = center
        pygame.draw.circle(self.screen, rgb("#ffd16a"), center, radius)
        pygame.draw.circle(self.screen, rgb("#ff8f68"), (x, y + radius // 3), radius, 0)
        pygame.draw.circle(self.screen, rgb("#fff7ed"), (x - radius // 3, y - radius // 5), radius // 3)
        pygame.draw.circle(self.screen, rgb("#fff7ed"), (x + radius // 4, y - radius // 5), radius // 3)
        pygame.draw.circle(self.screen, rgb("#1d2430"), (x - radius // 3, y - radius // 5), max(2, radius // 9))
        pygame.draw.circle(self.screen, rgb("#1d2430"), (x + radius // 4, y - radius // 5), max(2, radius // 9))
        pygame.draw.circle(self.screen, rgb("#513d7b"), (x + radius // 4, y - radius // 5), radius // 3 + 3, 3)
        pygame.draw.line(self.screen, rgb("#513d7b"), (x + radius // 2, y - radius // 3), (x + radius - 2, y - radius // 2), 3)
        pygame.draw.arc(self.screen, rgb("#55334e"), (x - radius // 3, y + radius // 5, radius, radius // 2), 0, math.pi, 3)

    def draw_bench(self, content):
        left = pygame.Rect(content.x, content.y, content.w // 2 - 8, content.h)
        right = pygame.Rect(content.centerx + 8, content.y, content.w // 2 - 8, content.h)
        self.panel(left, "SIMOSTOOLS - FLASH SEQUENCE")
        x = left.x + 28
        y = left.y + 72
        self.wrap("Plug into OBD, slurp the cal, unlock writing with the ECM3 boot patch, then flash. Flip the switch patch on for 4 stalk-selectable maps.", x, y, left.w - 56, TEXT)
        y += 96
        self.add_button(pygame.Rect(x, y, 150, 46), "Connect OBD", self.connect_obd, enabled=not self.connected, kind="primary", icon="1")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(x + 165, y, 145, 46), "Read ECU", self.read_ecu, enabled=self.connected and not self.read, kind="normal", icon="2")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(x + 325, y, 150, 46), "Boot Patch", self.patch_ecu, enabled=self.read and not self.patched, kind="normal", icon="3")
        self.draw_button(self.buttons[-1])
        y += 72
        self.add_button(pygame.Rect(x, y, 190, 46), f"switch patch: {'ON' if self.switch_patch else 'OFF'}", self.toggle_switch, enabled=self.patched, kind="normal")
        self.draw_button(self.buttons[-1])
        self.text("4 stalk maps", (x + 205, y + 14), DIM if not self.switch_patch else GREEN, "sm")
        y += 70
        self.add_button(pygame.Rect(x, y, left.w - 56, 54), "FLASH ECU", self.flash_ecu, enabled=self.patched, kind="primary", icon="4")
        self.draw_button(self.buttons[-1])
        if self.dirty:
            self.text("Flash required for changed tune.", (x, y + 72), AMBER, "sm")

        self.panel(right, "BENCH LOG")
        log_rect = pygame.Rect(right.x + 24, right.y + 62, right.w - 48, right.h - 94)
        self.round_rect(log_rect, BLACK, 10, LINE, 2)
        y = log_rect.y + 20
        for stamp, msg, kind in self.logs[-13:]:
            self.text(stamp, (log_rect.x + 18, y), MUTED, "sm")
            self.text(msg, (log_rect.x + 105, y), self.kind_color(kind), "sm")
            y += 26

    def draw_maps(self, content):
        left = pygame.Rect(content.x, content.y, content.w // 2 - 8, content.h)
        right = pygame.Rect(content.centerx + 8, content.y, content.w // 2 - 8, content.h)
        self.panel(left, "CALIBRATION")
        y = left.y + 62
        y = self.slider(left.x + 28, y, left.w - 56, "Boost", "boost", 14, 31, 0.5, lambda v: f"{v:.1f} psi")
        y = self.slider(left.x + 28, y, left.w - 56, "Peak timing", "timing", 6, 20, 0.5, lambda v: f"{v:.1f} deg")
        y = self.slider(left.x + 28, y, left.w - 56, "Lambda target", "lambda", 0.78, 0.92, 0.005, lambda v: f"{v:.3f}")
        self.text("Fuel", (left.x + 28, y + 4), TEXT, "md")
        fx = left.x + 110
        for fuel in ["91", "93", "E30", "E85"]:
            rect = pygame.Rect(fx, y, 76, 38)
            self.add_button(rect, fuel, lambda f=fuel: self.set_fuel(f), kind="seg_active" if self.tune["fuel"] == fuel else "seg")
            self.draw_button(self.buttons[-1])
            fx += 84
        y += 58
        self.text("Presets", (left.x + 28, y), BLUE, "md")
        y += 36
        x = left.x + 28
        for key, label in [("stock", "Stock"), ("stage1", "Stage 1"), ("stage2", "Stage 2 E30"), ("crackle", "Crackle Monster")]:
            rect = pygame.Rect(x, y, 160, 42)
            self.add_button(rect, label, lambda k=key: self.apply_preset(k), kind="normal")
            self.draw_button(self.buttons[-1])
            x += 172
            if x + 160 > left.right - 20:
                x = left.x + 28
                y += 52

        self.panel(right, "POPS, BANGS & SLOTS")
        y = right.y + 62
        y = self.slider(right.x + 28, y, right.w - 56, "Overrun fueling", "of", 0, 100, 1, lambda v: f"{round(v)}%")
        y = self.slider(right.x + 28, y, right.w - 56, "Overrun spark cut", "or", 0, 100, 1, lambda v: f"{round(v)}%")
        y = self.slider(right.x + 28, y, right.w - 56, "Throttle crackle", "th", 0, 100, 1, lambda v: f"{round(v)}%")
        score = pop_score(self.tune)
        self.text("BURBLE INDEX", (right.x + 28, y + 4), DIM, "xs")
        self.text(str(round(score)), (right.x + 28, y + 24), AMBER, "xl")
        bar = pygame.Rect(right.x + 130, y + 33, right.w - 180, 12)
        self.round_rect(bar, rgb("#1c2730"), 6)
        self.round_rect(pygame.Rect(bar.x, bar.y, int(bar.w * score / 100), bar.h), AMBER, 6)
        y += 76
        self.add_button(pygame.Rect(right.x + 28, y, 180, 42), "Preview Overrun", lambda: self.spawn_flames(score, max(2, round(2 + score / 10))), kind="normal")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(right.x + 220, y, 250, 42), "Assign Tune To Active Slot", self.assign_slot, enabled=self.flashed, kind="normal")
        self.draw_button(self.buttons[-1])
        y += 62
        self.draw_slots(right.x + 28, y, right.w - 56)

    def draw_dyno(self, content):
        top = pygame.Rect(content.x, content.y, content.w, int(content.h * 0.66))
        bottom = pygame.Rect(content.x, top.bottom + 12, content.w, content.bottom - top.bottom - 12)
        self.panel(top, "DYNO CELL")
        self.add_button(pygame.Rect(top.x + 28, top.y + 54, 160, 42), "Run Dyno Pull", self.run_dyno, enabled=self.flashed and not self.dyno_running, kind="primary")
        self.draw_button(self.buttons[-1])
        state = "pulling..." if self.dyno_running else "Loaded. Send it." if self.flashed else "Flash a tune first."
        self.text(state, (top.x + 205, top.y + 64), DIM if not self.dyno_running else AMBER, "sm")
        chart = pygame.Rect(top.x + 28, top.y + 112, top.w - 56, top.h - 142)
        self.draw_dyno_chart(chart)
        self.panel(bottom, "PULL RESULTS")
        names = [("hp", "WHP"), ("tq", "TQ"), ("kr", "KR"), ("egt", "EGT"), ("rel", "REL"), ("pop", "POP")]
        gap = 10
        box_w = (bottom.w - 56 - gap * (len(names) - 1)) // len(names)
        x = bottom.x + 28
        for key, label in names:
            rect = pygame.Rect(x, bottom.y + 54, box_w, 78)
            self.round_rect(rect, PANEL_DARK, 8, LINE, 1)
            self.text_center(label, (rect.centerx, rect.y + 20), DIM, "xs")
            self.text_center(self.results[key], (rect.centerx, rect.y + 50), TEXT, "lg")
            x += box_w + gap
        if self.grade:
            self.text_center(self.grade, (bottom.centerx, bottom.bottom - 26), GREEN if "S" in self.grade or "A" in self.grade else AMBER if "B" in self.grade or "C" in self.grade else RED, "sm")

    def draw_street(self, content):
        self.panel(content, "STREET MODE")
        scene = pygame.Rect(content.x + 28, content.y + 58, content.w - 56, content.h - 164)
        self.draw_street_scene(scene)
        y = scene.bottom + 18
        self.add_button(pygame.Rect(content.x + 28, y, 160, 46), "Hold Throttle", None, enabled=self.flashed, kind="primary", hold="throttle")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(content.x + 202, y, 90, 46), "Blip", self.blip, enabled=self.flashed, kind="normal")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(content.x + 306, y, 150, 46), f"2-Step: {'ON' if self.two_step else 'OFF'}", self.toggle_twostep, enabled=self.flashed, kind="normal")
        self.draw_button(self.buttons[-1])
        self.draw_meter(pygame.Rect(content.x + 480, y, 230, 18), "Cred", self.cred, 400, GREEN)
        self.draw_meter(pygame.Rect(content.x + 730, y, 230, 18), "Karen", self.karen, 100, RED if self.karen > 80 else AMBER)
        self.draw_slots(content.x + 980, y - 8, max(240, content.right - 1008), compact=True)

    def draw_race(self, content):
        left = pygame.Rect(content.x, content.y, int(content.w * 0.62), content.h)
        right = pygame.Rect(left.right + 16, content.y, content.right - left.right - 16, content.h)
        self.panel(left, "QUARTER MILE")
        track = pygame.Rect(left.x + 28, left.y + 62, left.w - 56, 245)
        self.draw_drag_track(track)
        y = track.bottom + 18
        self.add_button(pygame.Rect(left.x + 28, y, 150, 44), "Stage & Race", self.start_race, enabled=self.flashed and not self.race_active(), kind="primary")
        self.draw_button(self.buttons[-1])
        self.add_button(pygame.Rect(left.x + 192, y, 150, 44), "Launch / Shift", self.race_key, enabled=self.race_active(), kind="normal")
        self.draw_button(self.buttons[-1])
        self.wrap(self.race_result or "Launch on green. Shift near redline. Spacebar works too.", left.x + 28, y + 66, left.w - 56, TEXT if self.race_result else DIM)
        self.panel(right, "STREET LADDER")
        y = right.y + 56
        for idx, rival in enumerate(RIVALS):
            locked = idx > self.unlocked_rival
            rect = pygame.Rect(right.x + 24, y, right.w - 48, 44)
            text = f"{rival['name']}  {rival['whp']} whp  ${rival['purse']}"
            self.add_button(rect, text, lambda i=idx: self.select_rival(i), enabled=not locked, kind="seg_active" if idx == self.selected_rival else "seg")
            self.draw_button(self.buttons[-1])
            y += 52
        y += 8
        perf = self.car_perf()
        mods = ", ".join(k for k, v in self.mods.items() if v) or "none"
        self.wrap(f"Your car: {round(perf['whp'])} whp, {round(perf['weight'])} kg, grip {perf['grip']:.2f}, reliability {round(perf['rel'])}%. Mods: {mods}.", right.x + 28, y, right.w - 56, TEXT)

    def draw_shop(self, content):
        self.panel(content, "SHOP")
        self.text(f"Cash: ${self.cash}", (content.x + 28, content.y + 56), GREEN, "lg")
        cols = 2
        card_w = (content.w - 72) // cols
        card_h = 92
        x0 = content.x + 28
        y0 = content.y + 100
        for idx, (mod_id, name, cost, desc) in enumerate(MODS):
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(x0 + col * (card_w + 16), y0 + row * (card_h + 14), card_w, card_h)
            owned = self.mods[mod_id]
            self.round_rect(rect, rgb("#0e1a14") if owned else PANEL_DARK, 8, GREEN_2 if owned else LINE, 1)
            self.text(name, (rect.x + 14, rect.y + 12), GREEN if owned else TEXT, "md")
            self.wrap(desc, rect.x + 14, rect.y + 40, rect.w - 160, DIM, font_key="xs")
            label = "Installed" if owned else f"${cost}"
            enabled = not owned and self.cash >= cost
            self.add_button(pygame.Rect(rect.right - 130, rect.y + 24, 110, 42), label, lambda m=mod_id: self.buy_mod(m), enabled=enabled, kind="primary" if enabled else "normal")
            self.draw_button(self.buttons[-1])

    def round_rect(self, rect, fill, radius=10, border=None, width=1):
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        if border and width:
            pygame.draw.rect(self.screen, border, rect, width, border_radius=radius)

    def panel(self, rect, title):
        self.round_rect(rect, PANEL, 14, LINE, 2)
        self.text(title, (rect.x + 28, rect.y + 28), BLUE, "md", letter_spacing=4)

    def add_button(self, rect, label, action, enabled=True, kind="normal", icon="", sub="", hold=""):
        self.buttons.append(Button(rect, label, action, enabled, kind, icon, sub, hold))

    def draw_button(self, button: Button, force_active=False):
        hovered = button.rect.collidepoint(self.mouse) and button.enabled
        active = force_active or button.kind in ("primary", "tab_active", "seg_active")
        if button.kind.startswith("tab"):
            fill = rgb("#0e1a14") if active else PANEL_DARK
            border = GREEN_2 if active else LINE
            fg = GREEN if active else DIM
            if not button.enabled:
                fill = rgb("#0a0f13")
                border = rgb("#14212a")
                fg = rgb("#32414b")
            self.round_rect(button.rect, fill, 12, border if not hovered else GREEN, 2)
            self.text_center(button.sub, (button.rect.centerx, button.rect.y + 20), MUTED if button.enabled else rgb("#26323a"), "xs")
            self.text_center(f"{button.icon}  {button.label}", (button.rect.centerx, button.rect.y + 45), fg, "md")
            return

        if button.kind == "primary":
            fill = rgb("#149849") if button.enabled else rgb("#0e3824")
            border = rgb("#13b55a") if button.enabled else rgb("#17402a")
            fg = WHITE if button.enabled else rgb("#708176")
        elif button.kind == "seg_active":
            fill = rgb("#0e1a14")
            border = GREEN_2
            fg = GREEN
        else:
            fill = rgb("#16222b") if button.enabled else rgb("#10171d")
            border = LINE if not hovered else GREEN_2
            fg = TEXT if button.enabled else rgb("#52616b")
        self.round_rect(button.rect, fill, 9, border, 2)
        label = f"{button.icon} {button.label}" if button.icon else button.label
        self.text_center(label, button.rect.center, fg, "md")

    def slider(self, x, y, w, label, key, low, high, step, fmt):
        value = self.tune[key]
        self.text(label, (x, y), TEXT, "md")
        self.text(fmt(value), (x + w - 120, y), AMBER, "md")
        rect = pygame.Rect(x, y + 38, w, 8)
        self.round_rect(rect, rgb("#1c2730"), 5)
        ratio = (value - low) / (high - low)
        fill_rect = pygame.Rect(rect.x, rect.y, int(rect.w * ratio), rect.h)
        self.round_rect(fill_rect, GREEN, 5)
        knob_x = rect.x + int(rect.w * ratio)
        pygame.draw.circle(self.screen, GREEN, (knob_x, rect.centery), 10)
        pygame.draw.circle(self.screen, BG, (knob_x, rect.centery), 10, 2)
        self.sliders.append(Slider(rect, key, low, high, step))
        return y + 72

    def draw_meter(self, rect, label, value, max_value, color):
        self.text(f"{label}: {round(value)}", (rect.x, rect.y - 24), color, "sm")
        self.round_rect(rect, rgb("#1c2730"), 5)
        self.round_rect(pygame.Rect(rect.x, rect.y, int(rect.w * clamp(value / max_value, 0, 1)), rect.h), color, 5)

    def draw_slots(self, x, y, w, compact=False):
        count = 4 if self.switch_patch else 1
        h = 40 if compact else 48
        gap = 8
        if compact:
            slot_w = w
            for i in range(count):
                self.slot_button(pygame.Rect(x, y + i * (h + 6), slot_w, h), i, compact)
        else:
            slot_w = (w - gap * (count - 1)) // count
            for i in range(count):
                self.slot_button(pygame.Rect(x + i * (slot_w + gap), y, slot_w, h), i, compact)

    def slot_button(self, rect, idx, compact):
        tune = self.slots[idx]
        name = tune.get("name", f"Map {idx + 1}") if tune else "empty"
        txt = f"{idx + 1}. {name}" if compact else f"SLOT {idx + 1}: {name}"
        self.add_button(rect, txt, lambda i=idx: self.select_slot(i, True), enabled=bool(tune), kind="seg_active" if idx == self.active_slot else "seg")
        self.draw_button(self.buttons[-1])

    def text(self, text, pos, color, font_key="sm", bold=False, letter_spacing=0):
        font = self.fonts["md"] if bold else self.fonts[font_key]
        if not letter_spacing:
            surf = font.render(str(text), True, color)
            self.screen.blit(surf, pos)
            return surf.get_rect(topleft=pos)
        x, y = pos
        for ch in str(text):
            surf = font.render(ch, True, color)
            self.screen.blit(surf, (x, y))
            x += surf.get_width() + letter_spacing
        return pygame.Rect(pos[0], pos[1], x - pos[0], font.get_height())

    def text_center(self, text, center, color, font_key="sm"):
        surf = self.fonts[font_key].render(str(text), True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    def wrap(self, text, x, y, w, color, font_key="sm"):
        font = self.fonts[font_key]
        words = str(text).split()
        line = ""
        for word in words:
            test = word if not line else line + " " + word
            if font.size(test)[0] <= w:
                line = test
            else:
                self.screen.blit(font.render(line, True, color), (x, y))
                y += font.get_height() + 6
                line = word
        if line:
            self.screen.blit(font.render(line, True, color), (x, y))
            y += font.get_height() + 6
        return y

    def kind_color(self, kind):
        return {"ok": GREEN, "info": BLUE, "warn": AMBER, "err": RED, "violet": VIOLET}.get(kind, DIM)

    def icon_text(self, icon):
        return {"plug": "+", "map": "[]", "chart": "/", "fire": "^", "flag": "#", "wrench": "*"}.get(icon, "")

    def ask_simon(self):
        insights = self.simon_insights()
        self.simon_current = insights[self.simon_tick % len(insights)]
        self.simon_tick += 1
        self.simon_open = True

    def close_simon(self):
        self.simon_open = False

    def simon_insights(self):
        tune = self.flashed_tune if self.flashed and self.flashed_tune else self.tune
        result = compute_tune(tune, self.mods)
        n_mods = sum(1 for owned in self.mods.values() if owned)
        items = []

        def add(severity, roasts, tips):
            items.append({"sev": severity, "roast": pick(roasts), "tip": pick(tips)})

        if not self.connected:
            add(
                10,
                [
                    "You have not even plugged the cable in. Bold of you to ask me anything.",
                    "Step one says Connect OBD. You are at step zero. Inspiring.",
                    "I cannot roast a car that is not talking to the laptop. Plug in, genius.",
                ],
                [
                    "Bench tab: Connect OBD, Read ECU, Boot Patch, then Flash. Revolutionary.",
                    "Follow the little numbers: Connect, Read, Patch, Flash.",
                ],
            )
        elif not self.flashed:
            add(
                9,
                [
                    "All that handshaking and not one byte written. Commitment issues?",
                    "You are unlocked and bone stock. That is a gym membership you never use.",
                    "Read the ECU and then chickened out. A flash has never bricked a car out of fear.",
                ],
                [
                    "Build a map on Maps, then smash Flash ECU. The ECU will not tune itself.",
                    "Finish the sequence: Read, Boot Patch, Flash. Or stay slow. Your call.",
                ],
            )
        if result["blown"]:
            add(
                10,
                [
                    "You turned a perfectly good GTI into modern art. The medium is shrapnel.",
                    "That is not a tune, it is a crime scene with a voided warranty.",
                    "I have seen E85 do many things. Becoming a flare is new. Congrats.",
                ],
                [
                    "Richen lambda toward 0.80, pull boost and timing, then fit the Intercooler plus Port Injection.",
                    "Drop timing 2-3 deg, add ethanol, buy the FMIC. Then it might survive a Tuesday.",
                ],
            )
        if result["KR"] > 3:
            add(
                8,
                [
                    f"{result['KR']:.1f} deg of KR. The engine is literally flinching.",
                    f"{result['KR']:.1f} deg of KR means it makes power in spite of you, not because of you.",
                ],
                [
                    "Drop peak timing 2 deg, or step up fuel (93->E30->E85) for headroom. The FMIC helps too.",
                    "Less timing or more corn. Pick one before the pistons pick for you.",
                ],
            )
        if tune["lambda"] > 0.87 and not self.mods["fuel"]:
            add(
                9,
                [
                    f"Lambda {tune['lambda']:.2f} on stock fueling is how you turn a turbo into a kebab.",
                    "That mixture is leaner than my patience right now.",
                ],
                [
                    "Richen to about 0.82, or buy Port Injection + LPFP in the Shop to run it lean safely.",
                    "Fatten the lambda or fund the fuel system. Lean plus boost equals the bad kind of bang.",
                ],
            )
        if result["egt"] > 980:
            add(
                7,
                [
                    f"{round(result['egt'])} C pre-turbo. Your downpipe glows like a mood ring.",
                    "You could forge steel in that exhaust manifold.",
                ],
                [
                    "Ease the overrun sliders, richen up, or fit the Intercooler. Heat is the enemy.",
                    "Trim the pops and bangs a touch and add the FMIC. Cats prefer not being lava.",
                ],
            )
        if result["rel"] < 40 and not result["blown"]:
            add(
                7,
                [
                    f"Reliability {round(result['rel'])}%. One cold morning from a tow truck.",
                    "That build has the lifespan of a bargain-bin project car.",
                ],
                [
                    "Cool it: FMIC, a little less boost, richer lambda. Engines that finish win races.",
                    "Buy the Intercooler and ease the boost. A running engine beats a fast paperweight.",
                ],
            )
        if result["pop"] < 30:
            add(
                6,
                [
                    f"Burble index {round(result['pop'])}? That is not a GTI, it is a polite cough.",
                    "Where are the bangs? I came for fireworks and got a library voice.",
                    "Your exhaust is quieter than a dealership service advisor.",
                ],
                [
                    "Maps tab: crank Overrun Fueling and Overrun Spark Cut. Bolt on the Catless Downpipe to wake it up.",
                    "Load Crackle Monster, push the bang sliders, then add the downpipe.",
                ],
            )
        if tune["boost"] > 24 and not self.mods["turbo"]:
            add(
                5,
                [
                    f"{tune['boost']:.1f} psi out of the stock turbo. You can hear it sweating.",
                    "You are asking the little turbo for big-turbo numbers. It is wheezing.",
                ],
                [
                    "Buy the Hybrid Turbo IS38+. It lifts the whole boost ceiling and adds top-end.",
                    "Past about 24 psi the stock turbo is done. Hybrid turbo first, then chase boost.",
                ],
            )
        if self.cash < 150:
            add(
                5,
                [
                    f"${self.cash} to your name. Cannot afford an air freshener, let alone a turbo.",
                    "You are broker than a half-finished marketplace build.",
                ],
                [
                    "Race tab: beat the Civic for the purse. Even your tune can take a Civic.",
                    "Win a quarter mile: launch on green, shift at redline, collect.",
                ],
            )
        if self.cash > 900 and n_mods < 2:
            add(
                4,
                [
                    f"${self.cash} banked and a near-stock car. Saving for retirement?",
                    "Hoarding cash like it makes horsepower. It does not. Parts do.",
                ],
                [
                    "Shop tab. Downpipe for noise, Intercooler for safety, Hybrid Turbo for power. Spend it.",
                    "Stop counting money. The Catless Downpipe alone is worth the trip.",
                ],
            )
        if self.karen > 80:
            add(
                4,
                [
                    "The whole street has your plate memorized. The Karen meter is basically a countdown.",
                    "You are three bangs from a citation and a starring role on somebody's doorbell cam.",
                ],
                [
                    "Assign a quiet Valet map to a slot and switch to it before the cops roll up.",
                    "Let the Karen meter cool, or swap to a tame map. Or do not. Cred is cred.",
                ],
            )
        if self.flashed and not self.switch_patch:
            add(
                3,
                [
                    "Running one map like it is 2009. Live a little.",
                    "No switch patch means no instant valet map when things get spicy. Brave.",
                ],
                [
                    "Re-flash with Switch Patch ON for four stalk maps: valet, daily, and full Crackle Monster.",
                    "Flip the switch patch on so you can swap to a quiet map on demand.",
                ],
            )
        if result["rel"] > 70 and result["pop"] > 60 and result["whp"] > 320 and result["KR"] < 1:
            add(
                2,
                [
                    f"Fine. {round(result['whp'])} whp, {round(result['rel'])}% reliable, and it bangs. I hate that it is good.",
                    "Annoyingly competent. I was hoping to roast harder.",
                ],
                [
                    "Now go take the Rival Shop Mk7's lunch money on the strip.",
                    "Sneak a touch more timing if knock allows, then win the top bracket.",
                ],
            )
        if not items:
            add(
                1,
                [
                    "Nothing is actively on fire. Low bar, but you cleared it.",
                    "It is a car. It moves. Thrilling.",
                    "I have seen worse. I have also seen much, much better.",
                ],
                [
                    "Chase power on the dyno, bangs in the maps, cash on the strip. In that order.",
                    "Re-flash, run the dyno, tune for an S grade, then make it loud.",
                ],
            )
        items.sort(key=lambda item: item["sev"], reverse=True)
        return items

    def connect_obd(self):
        self.connected = True
        self.log("macchina A0 detected on COM5", "info")
        self.log("handshake - UDS 0x10 0x03", "dim")
        self.log("VIN WVWZZZAUZHW... - 138k mi", "ok")
        self.log("SA2 seed/key - access granted", "ok")

    def read_ecu(self):
        self.read = True
        self.log("reading ASW + CAL (0x80800000)...", "info")
        self.log("calibration dumped - 4.0 MB - CRC ok", "ok")
        self.log("stock map archived. you will never open it again.", "dim")

    def patch_ecu(self):
        self.patched = True
        self.unlocked_tabs.add("maps")
        self.log("applying ECM3 boot patch (cboot)...", "violet")
        self.log("disabling sample monitoring...", "warn")
        self.log("write access UNLOCKED. with great power...", "ok")
        self.log("Maps tab unlocked - go build something stupid.", "info")
        self.achievement("Boot Patched, Baby")

    def toggle_switch(self):
        if not self.patched:
            return
        self.switch_patch = not self.switch_patch
        self.log("switch patch " + ("ENABLED - cruise stalk picks maps 1-4" if self.switch_patch else "disabled"), "ok" if self.switch_patch else "dim")

    def flash_ecu(self):
        if not self.patched:
            return
        first = not self.flashed
        self.log("---------------- FLASH START ----------------", "violet")
        for msg, kind in [
            ("DO NOT yank the cable, do NOT sneeze", "warn"),
            ("erasing ASW...", "dim"),
            ("writing ASW - 0x36", "dim"),
            ("erasing CAL...", "dim"),
            ("writing CAL (your masterpiece) - 0x36", "info"),
            ("injecting switch-patch table (4 slots)..." if self.switch_patch else "single-map calibration...", "violet" if self.switch_patch else "dim"),
            ("recalculating ECM3 checksum...", "dim"),
            ("verify 0x37 - CRC match", "ok"),
            ("reset ECU - 0x11", "dim"),
        ]:
            self.log(msg, kind)
        self.log("---------------- FLASH OK - ECU lives ----------------", "ok")
        self.flashed = True
        self.dirty = False
        self.flashed_tune = clone_tune(self.tune)
        if self.switch_patch:
            if self.slots[1] is None:
                self.slots = [clone_tune(PRESETS["stock"]), clone_tune(self.tune), clone_tune(PRESETS["stage2"]), clone_tune(PRESETS["crackle"])]
                self.slots[0]["name"] = "Valet"
                self.slots[1]["name"] = "Your Tune"
                self.active_slot = 1
        else:
            self.slots = [clone_tune(self.tune), None, None, None]
            self.slots[0]["name"] = "Your Tune"
            self.active_slot = 0
        self.unlocked_tabs.update(["dyno", "street", "race", "shop"])
        if self.tune["fuel"] == "E30" and self.tune["boost"] >= 24:
            self.achievement("It's Not Stage 2, It's a Lifestyle")
        if first:
            self.log("Dyno, Street, Race & Shop unlocked. Go be a menace.", "info")

    def set_fuel(self, fuel):
        self.tune["fuel"] = fuel
        self.mark_dirty()

    def apply_preset(self, key):
        self.tune = clone_tune(PRESETS[key])
        self.log(f"preset loaded: {self.tune['name']}", "info")
        self.mark_dirty()

    def assign_slot(self):
        if not self.flashed:
            return
        self.slots[self.active_slot] = clone_tune(self.tune)
        self.slots[self.active_slot]["name"] = "Your Tune"
        self.log(f"current tune dropped into slot {self.active_slot + 1}", "info")

    def select_slot(self, idx, human=False):
        if idx >= len(self.slots) or not self.slots[idx]:
            return
        if not self.switch_patch and idx != 0:
            return
        self.active_slot = idx
        if human:
            self.switches += 1
            self.log(f"stalk - map {idx + 1} ({self.slots[idx].get('name', '')})", "ok")
            if self.switches >= 10:
                self.achievement("Stalk Wizard")

    def run_dyno(self):
        if not self.flashed:
            return
        tune = self.flashed_tune or self.tune
        self.dyno_result = compute_tune(tune, self.mods)
        self.dyno_points = dyno_curve(self.dyno_result["whp"])
        self.dyno_running = True
        self.dyno_start = time.perf_counter()
        self.dyno_progress = 0
        self.grade = ""

    def finish_dyno(self):
        self.dyno_running = False
        result = self.dyno_result
        points = self.dyno_points
        peak_hp = max(points, key=lambda p: p["pw"])
        peak_tq = max(points, key=lambda p: p["tq"])
        hp = peak_hp["pw"] * (0.3 if result["blown"] else 1)
        tq = peak_tq["tq"] * (0.3 if result["blown"] else 1)
        self.results = {
            "hp": str(round(hp)),
            "tq": str(round(tq)),
            "kr": f"{result['KR']:.1f}",
            "egt": str(round(result["egt"])),
            "rel": f"{round(result['rel'])}%",
            "pop": str(round(result["pop"])),
        }
        power_score = clamp((result["whp"] - 210) / (420 - 210) * 100, 0, 100)
        overall = 6 if result["blown"] else 0.40 * power_score + 0.35 * result["pop"] + 0.25 * result["rel"]
        if result["blown"]:
            self.grade = "ENGINE FAILURE - richen lambda, pull boost/timing, add cooling."
            self.achievement("Money Shift")
        elif overall >= 85:
            self.grade = f"Grade S - {round(overall)} pts - tuner of the year."
            self.achievement("Tuner of the Year")
        elif overall >= 72:
            self.grade = f"Grade A - {round(overall)} pts - fast, loud, barely legal."
        elif overall >= 58:
            self.grade = f"Grade B - {round(overall)} pts - solid, more in it."
        elif overall >= 42:
            self.grade = f"Grade C - {round(overall)} pts - it runs."
        else:
            self.grade = f"Grade D - {round(overall)} pts - rethink the map."
        if result["pop"] > 90:
            self.achievement("Cat Delete Speedrun")

    def draw_dyno_chart(self, rect):
        self.round_rect(rect, BLACK, 8, LINE, 2)
        points = self.dyno_points
        progress = self.dyno_progress
        x0, y0 = rect.x + 48, rect.bottom - 34
        x1, y1 = rect.right - 28, rect.y + 20
        rmin, rmax = 2200, 6800
        max_hp = max(max(p["pw"] for p in points), 300) * 1.08
        max_tq = max(max(p["tq"] for p in points), 300) * 1.08

        def x(rpm):
            return x0 + (rpm - rmin) / (rmax - rmin) * (x1 - x0)

        def yh(hp):
            return y0 - (hp / max_hp) * (y0 - y1)

        def yt(tq):
            return y0 - (tq / max_tq) * (y0 - y1)

        for rpm in range(2000, 7000, 1000):
            xx = x(rpm)
            pygame.draw.line(self.screen, LINE_SOFT, (xx, y0), (xx, y1))
            self.text(str(rpm), (xx - 15, y0 + 10), MUTED, "xs")
        if self.dyno_result and self.dyno_result["KR"] > 0.3:
            kr_rect = pygame.Rect(x(5200), y1, x1 - x(5200), y0 - y1)
            pygame.draw.rect(self.screen, rgb("#2a1114"), kr_rect)
            self.text(f"KR {self.dyno_result['KR']:.1f}", (x(5400), y1 + 12), RED, "xs")
        cut = max(2, int(len(points) * progress))
        tq_line = [(x(p["rpm"]), yt(p["tq"])) for p in points[:cut]]
        hp_line = [(x(p["rpm"]), yh(p["pw"])) for p in points[:cut]]
        if len(tq_line) > 1:
            pygame.draw.lines(self.screen, GREEN, False, tq_line, 3)
        if len(hp_line) > 1:
            pygame.draw.lines(self.screen, AMBER, False, hp_line, 3)
        if progress < 1:
            p = points[min(cut, len(points) - 1)]
            pygame.draw.line(self.screen, WHITE, (x(p["rpm"]), y0), (x(p["rpm"]), y1), 1)
        self.text("power (whp)", (x1 - 130, y1 + 12), AMBER, "xs")
        self.text("torque", (x1 - 130, y1 + 30), GREEN, "xs")

    def draw_street_scene(self, rect):
        self.round_rect(rect, BLACK, 10, LINE, 2)
        pygame.draw.rect(self.screen, rgb("#081014"), rect.inflate(-4, -4), border_radius=8)
        for i in range(28):
            x = rect.x + (i * 89 + 31) % rect.w
            y = rect.y + 22 + (i * 53) % int(rect.h * 0.38)
            pygame.draw.circle(self.screen, rgb("#56708a"), (x, y), 1)
        road_y = rect.y + int(rect.h * 0.62)
        pygame.draw.rect(self.screen, rgb("#10171d"), (rect.x + 2, road_y, rect.w - 4, rect.bottom - road_y - 2), border_radius=7)
        pygame.draw.line(self.screen, rgb("#2a3a45"), (rect.x + 20, road_y + 60), (rect.right - 20, road_y + 60), 2)
        for x in range(rect.x - 80, rect.right, 130):
            pygame.draw.line(self.screen, MUTED, (x, road_y + 60), (x + 55, road_y + 60), 3)
        car_x = rect.x + int(rect.w * 0.36)
        car_y = road_y + 65
        self.draw_car(car_x, car_y, rgb("#e7232b"), 1.65)
        ex_x = car_x - 88
        ex_y = car_y + 19
        for p in self.particles:
            px = ex_x + (p["x"] - 238)
            py = ex_y + (p["y"] - 226)
            f = clamp(p["life"] / p["max"], 0, 1)
            color = rgb("#fff6c8") if f > 0.75 else rgb("#ffd23f") if f > 0.5 else rgb("#ff7a18") if f > 0.28 else rgb("#d62828")
            pygame.draw.circle(self.screen, color, (int(px), int(py)), max(1, int(p["size"])))
        if self.cops_active:
            pygame.draw.rect(self.screen, RED, rect, 6, border_radius=10)
            self.text_center("KAREN CALLED THE COPS", (rect.centerx, rect.y + 38), RED, "lg")
        gear = "N" if self.rpm < 1200 else ["1", "2", "2", "3", "3", "4"][min(5, int(self.rpm / 1300))]
        self.text(f"{round(self.rpm)} RPM", (rect.x + 22, rect.y + 18), TEXT, "xl")
        self.text("2-STEP" if self.two_step and self.throttle > 0.5 else f"GEAR {gear}", (rect.x + 24, rect.y + 62), AMBER, "md")
        bar = pygame.Rect(rect.x + 24, rect.y + 94, 210, 10)
        self.round_rect(bar, rgb("#1c2730"), 5)
        self.round_rect(pygame.Rect(bar.x, bar.y, int(bar.w * self.rpm / 7200), bar.h), GREEN if self.rpm < 5600 else AMBER if self.rpm < 6800 else RED, 5)

    def draw_car(self, x, y, color, scale=1.0):
        s = scale
        pts = [(x - 52 * s, y + 14 * s), (x - 48 * s, y - 8 * s), (x - 25 * s, y - 27 * s), (x + 8 * s, y - 30 * s), (x + 34 * s, y - 11 * s), (x + 58 * s, y - 5 * s), (x + 61 * s, y + 14 * s)]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, rgb("#0c161c"), [(x - 22 * s, y - 8 * s), (x - 8 * s, y - 23 * s), (x + 10 * s, y - 24 * s), (x + 26 * s, y - 7 * s)])
        for wx in (-31, 35):
            pygame.draw.circle(self.screen, rgb("#111111"), (int(x + wx * s), int(y + 14 * s)), int(11 * s))
            pygame.draw.circle(self.screen, rgb("#9aa6ae"), (int(x + wx * s), int(y + 14 * s)), int(5 * s))

    def spawn_flames(self, intensity, count=None):
        strength = clamp(intensity / 100, 0.15, 1.8) * self.pop_mult()
        count = count or round(4 + strength * 18)
        for _ in range(count):
            is_bang = random.random() < strength * 0.45
            for _i in range(random.randint(14, 24) if is_bang else random.randint(4, 8)):
                ang = math.pi + random.uniform(-0.5, 0.5)
                speed = random.uniform(2, 7) * (1.6 if is_bang else 1) * strength
                self.particles.append({"x": 238 + random.uniform(-4, 4), "y": 226 + random.uniform(-4, 4), "vx": math.cos(ang) * speed, "vy": math.sin(ang) * speed - random.uniform(0.2, 1.4), "life": random.uniform(0.35, 0.75), "max": 0.8, "size": random.uniform(4, 12) * (1.4 if is_bang else 1)})
            self.bang_score(is_bang)

    def bang_score(self, is_bang):
        gain = (4 if is_bang else 1.4) * self.pop_mult()
        self.cred += gain
        self.karen = clamp(self.karen + (4 if is_bang else 1.5) * self.pop_mult(), 0, 100)
        self.add_cash(random.uniform(1, 3) if is_bang else random.uniform(0, 1))
        if is_bang:
            self.bangs += 1
        if self.bangs >= 50:
            self.achievement("Burble Brain")
        if self.cred >= 340:
            self.achievement("Wanted by the HOA")
        if self.karen >= 100 and not self.cops_active:
            self.cops()

    def cops(self):
        self.cops_active = True
        self.throttle_lock = True
        self.karen = 100
        fine = 150 + (100 if self.mods["dp"] else 0)
        self.add_cash(-fine)
        self.log(f"noise complaint - citation: -${fine}", "err")
        self.cop_clear_at = time.perf_counter() + 3.8

    def blip(self):
        self.blip_until = time.perf_counter() + 0.42

    def toggle_twostep(self):
        self.two_step = not self.two_step
        self.log("2-step armed. Hold throttle and let it scream." if self.two_step else "2-step off.", "info")

    def car_perf(self):
        result = compute_tune(self.flashed_tune or self.tune, self.mods)
        return {"whp": result["whp"], "weight": 1400 * (0.965 if self.mods["wheels"] else 1), "grip": 0.92 + (0.18 if self.mods["clutch"] else 0), "rel": result["rel"], "blown": result["blown"]}

    def select_rival(self, idx):
        if idx <= self.unlocked_rival:
            self.selected_rival = idx

    def race_active(self):
        return bool(self.race and self.race["active"])

    def start_race(self):
        if not self.flashed:
            return
        perf = self.car_perf()
        if perf["blown"]:
            self.race_result = "Your tune is a grenade. Fix it on the dyno first."
            return
        now = time.perf_counter()
        self.race = {
            "active": True,
            "phase": "tree",
            "tree_start": now,
            "green_at": now + 1.9,
            "rival_launch": now + 1.9 + random.uniform(0.12, 0.34),
            "rival": self.selected_rival,
            "p": {"d": 0.0, "v": 0.0, "gear": 1, "rpm": 850.0, "launched": False, "foul": False, "done": False, "et": 0.0, "trap": 0.0, "pen_until": 0.0, "pen_val": 1.0, "blown": False},
            "r": {"d": 0.0, "v": 0.0, "done": False, "et": 0.0, "trap": 0.0},
        }
        self.race_result = "Stage... watch the tree."
        self.drag_particles = []

    def race_key(self):
        if not self.race_active():
            return
        p = self.race["p"]
        now = time.perf_counter()
        if not p["launched"]:
            p["launched"] = True
            if now < self.race["green_at"]:
                p["foul"] = True
                self.race_result = "RED LIGHT. Finish the pass, but it is an auto-loss."
            else:
                self.race_result = "Green. Shift at redline."
            return
        if self.race["phase"] == "run":
            self.drag_shift()

    def drag_shift(self):
        p = self.race["p"]
        if p["done"] or p["gear"] >= 6:
            return
        rpm = p["rpm"]
        p["gear"] += 1
        if 6300 <= rpm <= 7050:
            quality = "perfect"
        elif rpm >= 5500:
            quality = "good"
            p["pen_until"] = time.perf_counter() + 0.30
            p["pen_val"] = 0.92
        else:
            quality = "early"
            p["pen_until"] = time.perf_counter() + 0.40
            p["pen_val"] = 0.78
        self.drag_pop(True)
        perf = self.car_perf()
        if quality == "perfect" and perf["rel"] < 32 and random.random() < 0.18:
            p["blown"] = True
            p["done"] = True
            self.race_result = "You money-shifted a fragile motor."
            self.achievement("Money Shift")

    def update_race(self, dt):
        if hasattr(self, "cop_clear_at") and self.cops_active and time.perf_counter() >= self.cop_clear_at:
            self.cops_active = False
            self.throttle_lock = False
            self.karen = 42
            self.cred += 40
            self.achievement("Neighborhood Menace")
        if not self.race_active():
            return
        now = time.perf_counter()
        race = self.race
        p, r = race["p"], race["r"]
        rival = RIVALS[race["rival"]]
        if race["phase"] == "tree" and now >= race["green_at"]:
            race["phase"] = "run"
        if race["phase"] != "run":
            return
        if p["launched"] and not p["done"]:
            perf = self.car_perf()
            eff = (p["pen_val"] if now < p["pen_until"] else 1) * (0.4 if p["rpm"] >= 7050 and p["gear"] < 6 else 1)
            self.step_car(p, perf["whp"], perf["weight"], perf["grip"], dt, eff)
            p["rpm"] = clamp(p["v"] / TIRE_CIRC * GEAR_RATIOS[p["gear"] - 1] * FINAL_DRIVE * 60, 850, 7300)
            if p["d"] >= TRACK_M:
                p["done"] = True
                p["et"] = now - race["green_at"]
                p["trap"] = p["v"] * 2.237
        if now >= race["rival_launch"] and not r["done"]:
            self.step_car(r, rival["whp"], rival["weight"], rival["grip"], dt, 1)
            if r["d"] >= TRACK_M:
                r["done"] = True
                r["et"] = now - race["green_at"]
                r["trap"] = r["v"] * 2.237
        for q in list(self.drag_particles):
            q["life"] -= dt
            q["x"] += q["vx"] * dt * 60
            q["y"] += q["vy"] * dt * 60
            q["vy"] += 0.05 * dt * 60
            if q["life"] <= 0:
                self.drag_particles.remove(q)
        if (p["done"] or p["blown"]) and r["done"]:
            self.resolve_race()

    def step_car(self, car, whp, weight, grip, dt, eff):
        power = whp * 745.7
        traction = weight * 9.81 * grip
        force = min(traction, power / max(car["v"], 2))
        drag = 0.5 * 1.2 * 0.62 * car["v"] * car["v"]
        accel = (force - drag) / weight * eff
        car["v"] = max(0, car["v"] + accel * dt)
        car["d"] += car["v"] * dt

    def drag_pop(self, is_bang):
        car_x = self.car_screen_x(self.race["p"]["d"])
        for _ in range(10 if is_bang else 4):
            ang = math.pi + random.uniform(-0.5, 0.5)
            speed = random.uniform(2, 6)
            self.drag_particles.append({"x": car_x - 14, "y": 196, "vx": math.cos(ang) * speed - 2, "vy": math.sin(ang) * speed - random.uniform(0.2, 1), "life": random.uniform(0.3, 0.55)})

    def resolve_race(self):
        race = self.race
        race["active"] = False
        p, r = race["p"], race["r"]
        rival = RIVALS[race["rival"]]
        if p["foul"]:
            won = False
            head = "RED LIGHT - DISQUALIFIED"
        elif p["blown"]:
            won = False
            head = "ENGINE LET GO"
        elif p["et"] and (not r["et"] or p["et"] < r["et"]):
            won = True
            head = f"WIN! {p['et']:.2f}s @ {round(p['trap'])} mph"
        else:
            won = False
            head = f"LOSS - {p['et']:.2f}s" if p["et"] else "LOSS - DNF"
        if won:
            purse = rival["purse"]
            self.add_cash(purse)
            self.cred += round(purse / 5)
            if race["rival"] == self.unlocked_rival and self.unlocked_rival < len(RIVALS) - 1:
                self.unlocked_rival += 1
                self.achievement("Climbing the Ladder")
            if race["rival"] == len(RIVALS) - 1:
                self.achievement("King of the Streets")
            self.achievement("Won Some Cash")
        you = f"You: {p['et']:.2f}s @ {round(p['trap'])} mph" if p["et"] else "You: DNF"
        them = f"{rival['name']}: {r['et']:.2f}s @ {round(r['trap'])} mph" if r["et"] else f"{rival['name']}: DNF"
        self.race_result = f"{head} | {you} | {them}" + (f" | +${rival['purse']}" if won else "")

    def car_screen_x(self, distance):
        return 46 + (distance / TRACK_M) * (760 - 92)

    def draw_drag_track(self, rect):
        self.round_rect(rect, BLACK, 8, LINE, 2)
        inner = rect.inflate(-20, -28)
        pygame.draw.rect(self.screen, rgb("#10171d"), inner, border_radius=6)
        mid = inner.y + inner.h // 2
        pygame.draw.line(self.screen, rgb("#2a3a45"), (inner.x, mid), (inner.right, mid), 2)
        fx = inner.right - 14
        for i in range(10):
            y0 = int(inner.y + i * inner.h / 10)
            y1 = int(inner.y + (i + 1) * inner.h / 10)
            pygame.draw.rect(self.screen, WHITE if i % 2 == 0 else BLACK, (fx, y0, 10, y1 - y0))
        race = self.race or {"phase": "idle", "tree_start": time.perf_counter(), "p": {"d": 0, "v": 0, "gear": 1, "rpm": 850}, "r": {"d": 0, "v": 0}, "rival": self.selected_rival}
        elapsed = time.perf_counter() - race["tree_start"]
        lamps = [(0.0, rgb("#ffd23f")), (0.4, AMBER), (0.9, AMBER), (1.4, AMBER), (1.9, GREEN)]
        for i, (t, col) in enumerate(lamps):
            on = race["phase"] not in ("tree", "idle") and i == 4 or elapsed > t
            pygame.draw.circle(self.screen, col if on else rgb("#1a2228"), (inner.x + 18, rect.y + 26 + i * 20), 6)
        sx = inner.w / (760 - 92)
        rival = RIVALS[race["rival"]]
        self.draw_car(inner.x + (self.car_screen_x(race["r"]["d"]) - 46) * sx, inner.y + 55, rival["color"], 0.55)
        self.draw_car(inner.x + (self.car_screen_x(race["p"]["d"]) - 46) * sx, inner.y + 150, rgb("#e7232b"), 0.55)
        for q in self.drag_particles:
            pygame.draw.circle(self.screen, rgb("#ff7a18"), (int(inner.x + (q["x"] - 46) * sx), int(inner.y + q["y"] - 60)), 4)
        p, r = race["p"], race["r"]
        self.text(f"YOU  G{p['gear']}  {int(p['v'] * 2.237)} mph", (inner.x + 18, inner.bottom + 5), TEXT, "sm")
        self.text(f"{rival['name']}  {int(r['v'] * 2.237)} mph", (inner.x + 18, inner.y - 24), TEXT, "sm")
        bar = pygame.Rect(inner.right - 220, inner.bottom + 8, 190, 10)
        self.round_rect(bar, rgb("#1c2730"), 5)
        frac = clamp((p["rpm"] - 850) / (7050 - 850), 0, 1)
        self.round_rect(pygame.Rect(bar.x, bar.y, int(bar.w * frac), bar.h), RED if frac > 0.9 else AMBER if frac > 0.75 else GREEN, 5)

    def buy_mod(self, mod_id):
        mod = next(item for item in MODS if item[0] == mod_id)
        if self.mods[mod_id] or self.cash < mod[2]:
            return
        self.cash -= mod[2]
        self.mods[mod_id] = True
        self.log(f"installed {mod[1]} (-${mod[2]})", "ok")
        if all(self.mods.values()):
            self.achievement("Fully Built (Wallet Empty)")


if __name__ == "__main__":
    try:
        MK7Game().run()
    except KeyboardInterrupt:
        sys.exit(0)
