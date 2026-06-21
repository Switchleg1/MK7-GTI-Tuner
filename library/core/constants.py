from __future__ import annotations

from panda3d.core import Vec4

from library.core.utils import rgba


APP_NAME = "MK7 GTI Tuner"
WINDOW_TITLE = "MK7 GTI Tuner - Panda3D"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_ASPECT = 16 / 9
DEFAULT_FOV_DEG = 105

TRACK_M = 402.336  # quarter-mile (m). Per-car gearing/curve/tire now live in CAR_TABLE.

UI_REFRESH_SECONDS = 0.25
MAX_LOG_LINES = 20

BG = rgba("#070a0d")
PANEL = rgba("#11161b", 0.66)        # translucent glass panel (rounded box fill)
PANEL_DARK = rgba("#0c1217", 0.82)   # denser glass for popups / close buttons
SIMON_PANEL = rgba("#111820", 0.98)
LINE = rgba("#22303b")
# Rounded-box styling (the ui_box / ui_ring textures are tinted by these).
BOX_LINE = rgba("#2f7d57", 0.55)     # subtle green ring around glass panels
BTN_LINE = rgba("#357f59", 0.50)     # ring around an enabled button
BTN_DISABLED_FILL = rgba("#0a0f13", 0.55)
BTN_DISABLED_TEXT = rgba("#3a4750")
# Managed buttons (library/stages/button.py): on press a button flashes for
# BUTTON_CLICK_HOLD seconds then reverts. A "box" button (the default) flashes its
# "clicked" colour (auto = normal brightened by BUTTON_CLICK_BRIGHTEN); a "pill" button
# (textured) flashes by colour-scale brighten (BUTTON_FLASH_SCALE).
BUTTON_CLICK_HOLD = 0.18
BUTTON_CLICK_BRIGHTEN = 1.8
BUTTON_FLASH_SCALE = 1.6
# Visual styles: the frame texture, an optional ring texture, whether `color` tints the
# FILL (box) or the TEXT (pill), a text vertical nudge, the click-flash mode, and an
# optional top accent-strip colour (hex) -- the garage task cards' green stripe.
BUTTON_STYLES = {
    "box":    {"texture": "ui_box",       "ring": "ui_ring", "tint": "fill", "text_dy": 0.0,    "flash": "fill"},
    "pill":   {"texture": "simon_button", "ring": None,       "tint": "text", "text_dy": -0.016, "flash": "scale"},
    "garage": {"texture": "ui_box",       "ring": "ui_ring", "tint": "fill", "text_dy": 0.0,    "flash": "fill", "accent": "#36e07a"},
}

# Dedicated cull bin for game-level overlays (Simon/Discord panels, the toast, and
# the notifications), registered in app startup ABOVE Panda's default "fixed" bin so
# they always draw over stage UI. Sorts within it order the overlays among themselves.
OVERLAY_BIN = "a2d-overlay"
OVERLAY_SORT = {"panel": 500, "toast": 900, "notify": 1000}
TEXT = rgba("#cfe3ee")
DIM = rgba("#7d93a3")
MUTED = rgba("#41535f")
GREEN = rgba("#36e07a")
GREEN_2 = rgba("#0f7a3e")
AMBER = rgba("#ffb338")
RED = rgba("#ff4d52")
BLUE = rgba("#4fb6ff")
VIOLET = rgba("#b58bff")
MAGENTA = rgba("#c844fc")
WHITE = rgba("#f2fbff")
BLACK = rgba("#060809", 0.96)
ROAST = rgba("#ffd0a0")
TIP = rgba("#9fe9bf")
SIMON_BUTTON = Vec4(0.15, 0.08, 0.22, 0.96)

TUNE_THRESHOLDS = {
    "kr_bad": 3.0,
    "kr_notice": 0.5,
    "egt_hot": 980,
    "egt_blown": 1085,
    "rel_low": 40,
    "rel_fragile": 32,
    "rel_good": 70,
    "pop_quiet": 30,
    "pop_loud": 70,
    "pop_wild": 90,
    "stock_turbo_boost_limit": 24,
    "stock_turbo_blown_boost": 26.5,
    "hybrid_turbo_boost_limit": 27,
    "hybrid_turbo_blown_boost": 29,
    "lean_lambda": 0.87,
    "safe_lambda": 0.82,
    "cash_low": 150,
    "cash_hoard": 900,
    "karen_hot": 80,
}

FUEL = {
    "91": {"head": 0, "pwr": 0},
    "93": {"head": 2, "pwr": 6},
    "E30": {"head": 5, "pwr": 18},
    "E85": {"head": 8.5, "pwr": 32},
}

DEFAULT_TUNE = {"boost": 20.0, "timing": 12.0, "lambda": 0.83, "fuel": "93", "of": 35.0, "or": 30.0, "th": 25.0, "name": "Your Tune"}

PRESETS = {
    "stock": {
        "boost": 18.0,
        "timing": 10.0,
        "lambda": 0.85,
        "fuel": "91",
        "of": 8.0,
        "or": 6.0,
        "th": 5.0,
        "name": "Stock"
    },
    "stage1": {
        "boost": 22.0,
        "timing": 13.0,
        "lambda": 0.83,
        "fuel": "93",
        "of": 30.0,
        "or": 28.0,
        "th": 25.0,
        "name": "Stage 1"
    },
    "stage2": {
        "boost": 24.5,
        "timing": 14.0,
        "lambda": 0.82,
        "fuel": "E30",
        "of": 45.0,
        "or": 42.0,
        "th": 40.0,
        "name": "Stage 2 E30"
    },
    "crackle": {
        "boost": 23.0,
        "timing": 13.0,
        "lambda": 0.84,
        "fuel": "E30",
        "of": 95.0,
        "or": 92.0,
        "th": 85.0,
        "name": "Crackle Monster"
    },
}

# Community maps unlockable via Discord (selectable in TUNE once unlocked).
COMMUNITY_MAPS = {
    "exley_stage_e": {
        "boost": 21.0,
        "timing": 12.0,
        "lambda": 0.82,
        "fuel": "93",
        "of": 28.0,
        "or": 26.0,
        "th": 22.0,
        "name": "Exley Stage E"
    },
    "zumble_jb4": {
        "boost": 25.5,
        "timing": 11.0,
        "lambda": 0.83,
        "fuel": "93",
        "of": 40.0,
        "or": 38.0,
        "th": 35.0,
        "name": "Zumble JB4 Stack"
    },
    "wunder_remote": {
        "boost": 24.0,
        "timing": 14.0,
        "lambda": 0.81,
        "fuel": "E30",
        "of": 50.0,
        "or": 48.0,
        "th": 44.0,
        "name": "Wunder Remote v3"
    },
    "bri3d_leak": {
        "boost": 26.0,
        "timing": 15.0,
        "lambda": 0.80,
        "fuel": "E85",
        "of": 90.0,
        "or": 88.0,
        "th": 80.0,
        "name": "bri3d leaked E85"
    },
}

# TUNE-screen UI tables: preset buttons (key, label), the fuel choices, and the
# editable sliders -- (slider attr, tune key, value range, label formatter).
PRESET_BUTTONS = [("stock", "Stock"), ("stage1", "Stage 1"), ("stage2", "Stage 2"), ("crackle", "Crackle")]
FUELS = ["91", "93", "E30", "E85"]
SLIDERS = [
    ("sl_boost", "boost", (16.0, 28.0), lambda v: f"Boost {v:.1f} psi"),
    ("sl_timing", "timing", (6.0, 18.0), lambda v: f"Timing {v:.1f} deg"),
    ("sl_lambda", "lambda", (0.78, 0.90), lambda v: f"Lambda {v:.3f}"),
    ("sl_of", "of", (0.0, 100.0), lambda v: f"Pop fuel {round(v)}"),
    ("sl_or", "or", (0.0, 100.0), lambda v: f"Pop spark {round(v)}"),
    ("sl_th", "th", (0.0, 100.0), lambda v: f"Throttle {round(v)}"),
]

MODS = [
    ("intake", "Cold Air Intake", 120, "+6 whp, quicker spool."),
    ("dp", "Catless Downpipe", 250, "+12 whp and much louder bangs. Cops notice fast."),
    ("fmic", "Front-Mount Intercooler", 300, "More knock headroom and lower EGT."),
    ("clutch", "Stage 2 Clutch + LSD", 450, "Launch grip for the strip."),
    ("wheels", "Lightweight Wheels", 200, "Less rotating weight."),
    ("fuel", "Port Injection + LPFP", 700, "Feeds E85 safely."),
    ("turbo", "Hybrid Turbo IS38+", 900, "Raises boost ceiling."),
]

# --------------------------------------------------------------------------
# Cars + mods (the curve-based performance model). CAR_TABLE is the single source
# of each car's spec; MOD_TABLE carries the effect data behind the MODS bool ids
# (its keys MUST match the ids in MODS). Both the player's Car and rival Cars pull
# from CAR_TABLE and compose their final rpm->whp curve via tuning.build_whp_curve.
# --------------------------------------------------------------------------

# Per-mod effects. `curve` = [(rpm, base_add, scaler)] whp adders interpolated across
# rpm; at each rpm the gain is base_add + scaler * (running total of earlier mods'
# adds), so mods compound. `spool` shifts the boost onset (- earlier, + later),
# `weight` kg +/-, `grip` traction +/-, `max_boost` raises the psi ceiling.
MOD_TABLE = {
    "intake": {"spool": -150, "weight": 0,   "grip": 0.00, "max_boost": 0,
               "curve": [(3000, 3, 0.02), (5000, 6, 0.04), (6700, 6, 0.04)]},
    "dp":     {"spool": -200, "weight": 0,   "grip": 0.00, "max_boost": 1,
               "curve": [(3500, 6, 0.05), (5000, 10, 0.06), (6700, 12, 0.06)]},
    "fmic":   {"spool": 0,    "weight": 5,   "grip": 0.00, "max_boost": 1,
               "curve": [(4500, 4, 0.03), (6700, 8, 0.05)]},
    "clutch": {"spool": 0,    "weight": 0,   "grip": 0.18, "max_boost": 0, "curve": []},
    "wheels": {"spool": 0,    "weight": -50, "grip": 0.02, "max_boost": 0, "curve": []},
    "fuel":   {"spool": 0,    "weight": 0,   "grip": 0.00, "max_boost": 0,
               "curve": [(4000, 8, 0.05), (6000, 14, 0.08), (6700, 14, 0.08)]},
    "turbo":  {"spool": 250,  "weight": 0,   "grip": 0.00, "max_boost": 5,
               "curve": [(3500, -5, 0.0), (4500, 15, 0.10), (5500, 35, 0.15), (6700, 45, 0.15)]},
}

# Each car: real-world-derived stock wheel-power curve [(rpm, whp)] + gearing + tire +
# mass + grip. `power_curve` is the STOCK base; the player's tune scales it and owned
# mods reshape it in build_whp_curve. `model` is the .glb key (see CAR_MODEL_FILES).
CAR_TABLE = {
    "mk7_gti": {
        "name": "MK7 GTI", "model": "mk7_gti", "weight": 1380, "grip": 0.92,
        "gears": [3.76, 2.08, 1.46, 1.08, 0.97, 0.84], "final_drive": 3.65, "tire_circ": 2.00,
        "idle": 900, "redline": 6700, "spool_rpm": 3000, "max_boost": 20, "boost_ceiling": 24,
        "power_curve": [(1000, 30), (2000, 95), (3000, 165), (4000, 200), (4800, 210),
                        (5500, 208), (6200, 195), (6700, 175)],
    },
    "stock_civic": {
        "name": "Civic 1.5T", "model": "stock_civic", "weight": 1250, "grip": 0.90,
        "gears": [3.64, 2.08, 1.36, 1.02, 0.79, 0.64], "final_drive": 4.11, "tire_circ": 2.03,
        "idle": 850, "redline": 6500, "spool_rpm": 2500, "max_boost": 16, "boost_ceiling": 18,
        "power_curve": [(1000, 22), (2000, 70), (3000, 120), (4000, 142), (5000, 150),
                        (5500, 150), (6000, 140), (6500, 125)],
    },
    "civic_type_r": {
        "name": "Civic Type R", "model": "civic_type_r", "weight": 1380, "grip": 1.00,
        "gears": [3.63, 2.12, 1.53, 1.13, 0.91, 0.73], "final_drive": 3.84, "tire_circ": 2.06,
        "idle": 850, "redline": 7000, "spool_rpm": 2800, "max_boost": 22, "boost_ceiling": 26,
        "power_curve": [(1500, 55), (2500, 160), (3500, 235), (4500, 265), (5500, 270),
                        (6500, 265), (7000, 255)],
    },
    "wrx_sti": {
        "name": "WRX STI", "model": "wrx_sti", "weight": 1520, "grip": 1.18,
        "gears": [3.64, 2.24, 1.59, 1.14, 0.97, 0.76], "final_drive": 3.90, "tire_circ": 2.05,
        "idle": 850, "redline": 6700, "spool_rpm": 3200, "max_boost": 18, "boost_ceiling": 22,
        "power_curve": [(2000, 70), (3000, 150), (4000, 220), (5000, 255), (6000, 265),
                        (6500, 255), (6700, 240)],
    },
    "bmw_m2": {
        "name": "BMW M2", "model": "bmw_m2", "weight": 1500, "grip": 1.00,
        "gears": [4.11, 2.32, 1.54, 1.18, 1.00, 0.85], "final_drive": 3.46, "tire_circ": 2.05,
        "idle": 800, "redline": 7000, "spool_rpm": 2200, "max_boost": 17, "boost_ceiling": 21,
        "power_curve": [(1500, 80), (2500, 200), (3500, 290), (4500, 325), (5500, 330),
                        (6500, 330), (7000, 310)],
    },
}

# The street ladder: encounter metadata + the car_id each rival drives (its physics
# come from CAR_TABLE). Ladder progression will later be tuned by giving rivals mods.
RIVALS = [
    {
        "name":         "Stock Civic",
        "car_id":       "stock_civic",
        "purse":        120,
        "color":        rgba("#9fb3c0"),
        "mods":         [],
        "tune":         DEFAULT_TUNE,
        "video_loss":   ["loss/ed_dis.mp4"],
        "video_win":    []
    },
    {
        "name":         "Civic R",
        "car_id":       "civic_type_r",
        "purse":        230,
        "color":        rgba("#e6e6e6"),
        "mods":         [],
        "tune":         DEFAULT_TUNE,
        "video_loss":   ["loss/ed_dis.mp4"],
        "video_win":    []
    },
    {
        "name":         "WRX STI",
        "car_id":       "wrx_sti",
        "purse":        480,
        "color":        rgba("#3a6ad6"),
        "mods":         ["intake", "dp", "fmic", "turbo"],
        "tune":         DEFAULT_TUNE,
        "video_loss":   ["loss/ed_dis.mp4"],
        "video_win":    []
    },
    {
        "name":         "BMW M2", "car_id": "bmw_m2",
        "purse":        850,
        "color":        rgba("#222222"),
        "mods":         ["intake", "dp", "fmic"],
        "tune":         DEFAULT_TUNE,
        "video_loss":   ["loss/ed_dis.mp4"],
        "video_win":    []
    },
    {
        "name":         "Rival Shop Mk7",
        "car_id":       "mk7_gti",
        "purse":        1600,
        "color":        rgba("#e7232b"),
        "mods":         ["intake", "dp", "fmic", "clutch", "fuel", "turbo"],
        "tune":         PRESETS["stage2"],
        "video_loss":   ["loss/ed_dis.mp4"],
        "video_win":    []
    },
]

REPS = [(0, "Civic Bait"), (60, "Cars & Coffee Regular"), (160, "Local Legend"), (340, "Wanted by the HOA")]

# Dyno grade bands: (minimum score, grade letter, flavour note). Iterated high->low.
GRADE_TABLE = [
    (95, "F", "you know what this means"),
    (85, "S", "tuner of the year"),
    (72, "A", "fast, loud, barely legal"),
    (58, "B", "solid, more in it"),
    (42, "C", "it runs"),
    (0, "D", "rethink the map"),
]

# Garage hub + task cameras (glb car faces +Y, ~4 m long, driver side -X).
GARAGE_CAMERA = {"pos": (5.6, -7.6, 3.0), "look_at": (-0.2, 0.4, 0.7), "fov": 42}
TASK_CAMERAS = {
    "street": {"pos": (-6.2, -5.6, 2.2), "look_at": (-0.4, 1.2, 0.7), "fov": 50},
    "race": {"pos": (0.0, -9.5, 3.4), "look_at": (0.0, 7.0, 0.6), "fov": 55},
    "dyno": {"pos": (6.6, -3.2, 1.9), "look_at": (0.0, 0.2, 0.7), "fov": 45},
}

# Race chase camera, framed BETWEEN the two lanes so BOTH cars stay visible. A
# cockpit-only POV can't see the rival at the line (they sit ~4m to the side,
# outside any sane FOV). The cars stay fixed and the world scrolls past, keeping
# the "world moves around you" feel from a follow-camera vantage.
CHASE_CAM_POS = (0.0, -8.0, 2.6)
CHASE_CAM_LOOK = (0.0, 14.0, 0.5)
CHASE_FOV = 55

# Wheel spinning (car.glb). Body parts are prefixed "vw:", wheel parts "w:"; the
# wheel parts are flat siblings whose transforms pivot at the model origin, so
# TaskBase.prepare_wheels regroups the spinnable ones into 4 corner pivots and spins
# those about the axle (X). Calipers must stay put (don't rotate with the wheel).
WHEEL_PREFIX = "w:"
WHEEL_STATIC = ("calliper", "caliper")  # name substrings of wheel parts that don't spin

# --------------------------------------------------------------------------
# Dyno (SimosTools-style gauge cluster + live graph)
# --------------------------------------------------------------------------
DYNO_PULL_SECONDS = 4.0  # the pull sweeps the car's own idle->redline (from CAR_TABLE)

# Gauge tiles: (label, value-key, lo, hi, danger_above, unit, decimals)
DYNO_GAUGES = [
    ("BOOST", "boost", 0, 30, 26, "psi", 1),
    ("ENGINE SPEED", "rpm", 0, 7000, 6800, "rpm", 0),
    ("KNOCK", "kr", 0, 6, 3, "deg", 1),
    ("LAMBDA", "lambda", 0.70, 1.00, 0.90, "L", 2),
    ("EGT", "egt", 600, 1100, 980, "C", 0),
    ("POWER", "whp", 0, 600, 9999, "whp", 0),
]
DYNO_ZONE_GREEN = rgba("#0e5a31")   # in-spec band
DYNO_ZONE_RED = rgba("#5e1410")     # danger band
DYNO_TILE = rgba("#0a0f13", 1.0)
DYNO_TRACE = rgba("#4fe0ff")        # power (whp) trace (cyan)
DYNO_TRACE_TQ = rgba("#ffb454")     # torque (lb-ft) trace (amber)
DYNO_GRID = rgba("#1c2630")

# --------------------------------------------------------------------------
# Assets (standard formats for now: .glb models, .png images under data/)
# --------------------------------------------------------------------------
DATA_DIR = "data"
MODELS_DIR = "data/models"
IMAGES_DIR = "data/images"
AUDIO_DIR = "data/audio"
VIDEOS_DIR = "data/videos"

CAR_MODEL_DIRECTORY = "cars"
CAR_MODEL_FILES = {
    "mk7_gti":          "mk7_gti.glb",
    "stock_civic":      "stock_civic.glb",
    "civic_type_r":     "civic_type_r.glb",
    "wrx_sti":          "wrx_sti.glb",
    "bmw_m2":           "bmw_m2.glb"
}

CHARACTER_MODEL_DIRECTORY = "characters"
CHARACTER_MODEL_FILES = {
    "character": "character.glb",
}

GEOMETRY_MODEL_DIRECTORY = "geometry"
GEOMETRY_MODEL_FILES = {
    "ground": "ground.glb",
}

MISC_MODEL_DIRECTORY = "misc"
MISC_MODEL_FILES = {
    "phone": "phone.glb",
    "obd": "obd.glb",
}

IMAGE_FILES = {
    "wallpaper": "phone_wallpaper.png",
    "app_icon": "simostools_icon.png",
    "check": "flash_complete.png",
    "logo": "logo.png",
    "simon": "simon.png",
    "simon_panel": "simon_panel.png",
    "simon_button": "simon_button.png",
    "tip_bulb": "tip_bulb.png",
    "emoji_cred": "emoji_cred.png",
    "emoji_karen": "emoji_karen.png",
    "emoji_pops": "emoji_pops.png",
    "emoji_fire": "emoji_fire.png",
    "emoji_cash": "emoji_cash.png",
    # UI chrome (tinted at runtime via frameColor / colorScale).
    "ui_box": "ui_box.png",      # solid rounded rectangle -> glass panel / button fill
    "ui_ring": "ui_ring.png",    # rounded-rectangle outline -> panel / button border
    "knob": "knob.png",          # round slider thumb (placeholder; edit freely)
    "avatar": "avatar.png",      # default round discord avatar, tinted per user
}

# --------------------------------------------------------------------------
# Audio (procedural .wav synthesized offline by assetgen/asset_audio.py).
# The engine loop is rendered at engine_base_rpm and pitched in-game with
# setPlayRate; pops/bangs are one-shots played from a pool so bursts overlap.
# --------------------------------------------------------------------------
SOUND_FILES = {
    "engine": "engine_loop.wav",
    "intake": "intake_loop.wav",
    "turbo": "turbo_loop.wav",
    "pop_1": "pop_1.wav",
    "pop_2": "pop_2.wav",
    "pop_3": "pop_3.wav",
    "bang_1": "bang_1.wav",
    "bang_2": "bang_2.wav",
    "bang_3": "bang_3.wav",
    "bov": "bov.wav",
}

AUDIO = {
    "engine_base_rpm": 3000.0,   # rpm the engine_loop.wav is rendered at (rate 1.0)
    "engine_volume": 0.55,       # master gain for the engine note at full load
    "intake_volume": 0.35,       # induction roar, scaled by load^2
    "turbo_volume": 0.22,        # spool whistle, scaled by spool*load
    "pop_volume": 0.30,          # base one-shot gain for a pop
    "bang_volume": 0.52,         # base one-shot gain for a bang
    "bov_volume": 0.40,          # blow-off "pshhh"
    "idle_load": 0.12,           # engine load floor when idling
    "pull_load": 0.95,           # engine load on a WOT dyno pull / launch
    "pool_size": 4,              # overlapping instances loaded per one-shot file
    "concurrent_limit": 32,      # max simultaneous sounds (pops stack up)
    "rate_min": 0.35,            # clamp for engine playRate (idle)
    "rate_max": 3.2,             # clamp for engine playRate (redline)
    "overrun_min_rpm": 3000,     # below this a throttle lift won't crackle
    "overrun_count": 24,         # max pops/bangs in a full-intensity burst
}

# --------------------------------------------------------------------------
# Music: per-stage background tracks in data/music/<key>/. A random song plays;
# when it finishes another random one from the same folder starts. Drop .ogg/.mp3/
# .wav files in the folder named for each stage key (the task keys, plus "garage"
# for the hub and "unlock" for the cinematic). Missing/empty folder -> silence.
# --------------------------------------------------------------------------
MUSIC_DIR = "data/music"
MUSIC_EXTS = (".ogg", ".mp3", ".wav")
MUSIC_VOLUME = 0.2   # default background-music level (0..1), overridden by options.cfg
FX_VOLUME = 0.8      # default sound-effects level (engine/pops/bangs), 0..1

# "Now playing" toast: a game-level overlay (above every stage) shown for
# TOAST_SECONDS when a song starts, then it fades out over TOAST_FADE.
TOAST_SECONDS = 5.0
TOAST_FADE = 0.6
TOAST_W = 0.98
TOAST_H = 0.135
TOAST_Z = -0.85

# --------------------------------------------------------------------------
# Save games + options. Both live under the user's app-data folder (APP_NAME);
# options.cfg persists between runs and loads at startup, savegame.json holds a
# career snapshot (bro / car+mods / discord + progress). The rival ladder is NOT
# saved -- it's static reference data from RIVALS (v1 saved it and froze stale
# specs). SAVE_VERSION lets a future load reject or migrate an old layout.
# --------------------------------------------------------------------------
SAVE_VERSION = 3  # v3: Car carries car_id (curve-based model); old saves load as mk7_gti
CONFIG_FILE = "options.cfg"
SAVE_FILE = "savegame.json"

# --------------------------------------------------------------------------
# Main / pause menu. One MenuStage walks these pages (root / options / graphics);
# the app supplies the actions. Root rows: (action key, label, visibility) where
# visibility is "all" (always), "pause" (only with a game in progress), or
# "main" (only on the title screen). "load" is auto-disabled with no save file.
# --------------------------------------------------------------------------
MENU_MUSIC_KEY = "garage"  # title + pause menu share the hub track (continuous)
MENU_ITEMS = [
    ("resume", "Resume", "pause"),
    ("new", "New Game", "all"),
    ("load", "Load Game", "all"),
    ("save", "Save Game", "pause"),
    ("options", "Options", "all"),
    ("quit", "Quit", "all"),
]
MENU_PANEL = (-0.66, 0.66, -0.66, 0.66)  # centred glass card (l, r, b, t)
MENU_BTN = (1.04, 0.12)                  # menu button size (w, h)
MENU_BTN_GAP = 0.155                     # vertical spacing between menu buttons
MENU_VOL_RANGE = (0.0, 1.0)              # music / fx volume slider range

# --------------------------------------------------------------------------
# Unlock cinematic (driver-side: LHD car faces +Y, driver seat/door on -X,
# OBD2 port under the steering wheel on the driver side)
# --------------------------------------------------------------------------
UNLOCK_CAMERA = {"pos": (-5.6, -5.4, 1.7), "look_at": (-1.4, 0.2, 0.7)}
UNLOCK_FOV = 45  # narrower than the garage's 105 deg for a cinematic framing

# Scene placement (world coords; car sits at origin facing +Y, driver side -X).
CHARACTER_POS = (-1.2, 0.0, 0.0)
OBD_PORT_POS = (-0.92, 0.95, 0.50)
# Adapter offsets are LOCAL to the port node: starts out by his hand, then plugs in.
OBD_ADAPTER_REST = (-0.30, -0.62, -0.18)
OBD_ADAPTER_PLUGGED = (0.0, -0.09, 0.0)
# Phone offset local to the right hand when held up.
PHONE_IN_HAND = (0.02, -0.12, -0.14)

# Character joint poses (HPR degrees per named joint node). Lerped between at
# runtime to act out the cinematic; only listed joints move for a given pose.
CHARACTER_POSES = {
    "rest": {"rShoulder": (0, 4, 6), "rElbow": (0, -12, 0), "lShoulder": (0, 4, -6), "lElbow": (0, -12, 0), "torso": (0, 0, 0)},
    "reach": {"rShoulder": (0, -42, 4), "rElbow": (0, -38, 0), "torso": (0, -18, 0)},
    "hold_phone": {"rShoulder": (0, -56, 30), "rElbow": (0, -88, 0), "torso": (0, -6, 0)},
    "cheer": {"rShoulder": (0, -160, -18), "rElbow": (0, -18, 0), "lShoulder": (0, -160, 18), "lElbow": (0, -18, 0), "torso": (0, 0, 0)},
}

UNLOCK_PROMPTS = {
    "plug": "Click the OBD2 port under the dash",
    "plugging": "Plugging in the adapter...",
    "phone": "Tap your phone",
    "raising": "Opening SimosTools...",
    "flash": "Hit FLASH on the phone",
    "flashing": "Flashing - do not unplug",
    "done": "ECU unlocked. Continue to pick a mode.",
}

# Pulsing colors for the clickable hotspots.
HOTSPOT_HI = rgba("#ffd166")
HOTSPOT_LO = rgba("#7a5a16")

# Limb posing happens at runtime; these are the cinematic beat lengths (seconds).
PLUG_IN_SECONDS = 1.6
RAISE_PHONE_SECONDS = 1.1
CELEBRATE_SECONDS = 1.8

# Short "link" progress shown right after plugging in (label, seconds).
LINK_STEPS = [
    ("Powering up K-line / CAN...", 0.7),
    ("ECU responding on 500 kbps...", 0.7),
]

# Main flash sequence: (phone log label, seconds, cumulative progress 0..1).
UNLOCK_FLASH_STEPS = [
    ("Handshake with ECU (UDS 0x10)...", 0.8, 0.06),
    ("Security access - seed/key (SA2)...", 1.1, 0.16),
    ("Reading calibration block...", 1.3, 0.34),
    ("Verifying checksums (CRC32)...", 0.9, 0.46),
    ("Unlocking write access (ECM3 boot patch)...", 1.4, 0.64),
    ("Erasing flash sectors...", 0.9, 0.74),
    ("Writing tuned calibration...", 1.6, 0.92),
    ("Verifying flash and resetting ECU...", 1.0, 1.0),
]

# Identity lines that stream onto the phone as the read progresses.
ECU_READOUT = [
    ("VIN", "WVWZZZAUZJW360###"),
    ("ECU", "Continental Simos 18.1"),
    ("HW", "5G0 906 259 G"),
    ("SW", "06K 906 026 ER"),
    ("Calibration", "8V0 906 264 K"),
    ("Flash size", "4.00 MB"),
    ("Base map", "IS38 / Stock"),
]

# --------------------------------------------------------------------------
# Phone UI overlay
# --------------------------------------------------------------------------
PHONE_FRAME = rgba("#04070a", 0.99)
PHONE_BEZEL = rgba("#10161c", 1.0)
PHONE_SCREEN = rgba("#0a1014", 1.0)
PHONE_LOG_LINES = 9
PHONE_UI_LEFT = 0.62          # left edge of the phone overlay in aspect2d units
PHONE_UI_HALF_W = 0.34        # half width of the phone body
PHONE_UI_HALF_H = 0.72        # half height of the phone body

# --------------------------------------------------------------------------
# Mode select screen: (garage tab key, title, blurb)
# --------------------------------------------------------------------------
MODES = [
    ("maps", "TUNE", "Boost, timing, fuel & pops"),
    ("dyno", "DYNO", "Pull it and grade the map"),
    ("street", "SKREETS", "Bangs, pops & cred"),
    ("race", "RACE", "Quarter-mile skreets ladder"),
    ("shop", "SHOP", "Spend winnings on mods"),
    ("bench", "BENCH", "Re-flash new staged maps"),
]

# --------------------------------------------------------------------------
# Arcade scoreboard. A single running score on the bro (TunerBro.score), fed by
# races, pops & bangs, achievements, and the Bench Wizard's Trial. The SCORE task
# shows it on an 80s arcade hall-of-fame board against made-up handles whose fixed
# scores span a full playthrough, so the player climbs the board as they progress.
# --------------------------------------------------------------------------
SCOREBOARD_NAMES = [
    ("ED",      7500),
    ("DAVE",    6200),
    ("SIMON",   4400),
    ("DAMON",   2100),
    ("EDDY",    1050),
    ("1LOW",    480),
    ("TACOS",   210),
    ("BURN",    90),
    ("N00B",    30),
]

# Arcade neon palette for the SCORE board.
ARCADE_BG = rgba("#05060a", 1.0)
ARCADE_SCANLINE = rgba("#0c1830", 0.5)

# --------------------------------------------------------------------------
# Discord ("MQB Vibe Coders") -- the chat window + community roster.
# Roster rows feed DiscordUser subclasses (role -> Admin/GreenName/NormalUser);
# "persona" drives chatter flavour and the help-request outcome lean. Only a
# fraction roll online at a time (per-row ``online`` chance). No emoji in lines
# (the mono UI font can't render them).
# --------------------------------------------------------------------------
DISCORD_SERVER = "MQB Vibe Coders"
DISCORD_CHANNEL_GROUP = "MQB Tuning"
DISCORD_ACTIVE_CHANNEL = "ecu-tuning"
DISCORD_CHANNELS = [
    "welcome", "docs", "car-setups", "custom-features", "donglez",
    "dsg-tuning", "ecu-tuning", "flashing-tools", "haldex-springs",
]

# (handle, display, role, persona, online_chance, color, status, [chatter lines])
DISCORD_ROSTER = [
    ("simos", "Simon", "admin", "pro_tuner", 0.80, VIOLET, "0 chill",
     ["post a log or stop talking", "that map is a crime scene", "skill issue, respectfully",
      "i read your longview - it's knocking", "back off two clicks and re-log"]),
    ("aaronc7", "Aaronc7", "admin", "good idea fairy", 0.80, MAGENTA, "good idea fairy",
     ["I found a bug.", "lets flash that map for UNLIMITED POWAH", "to the FR!",
      "simon i have a request...", "back off two clicks and re-log"]),
    ("cp4334", "CP4334", "admin", "boost", 0.78, AMBER, "Playing TunerPro",
     ["more boost fixes most things", "rods are merely suggestions", "send it to 26 and find out",
      "bent another one, worth it", "boost is a personality trait"]),
    ("mike", "Mike", "admin", "disaster", 0.70, RED, "buying a turbo",
     ["just bought another turbo", "who wants to street race tonight", "third IS38 this month",
      "my problem is boost and i refuse to fix it", "raced a cop, lost the cop",
      "She fucks", "get me a corona", "flops for life"]),
    ("jc", "JC", "admin", "hates_2x4", 0.68, BLUE, None,
     ["take the 2x4 off the car", "a 2x4 is not a mod", "if i see one more 2x4 i'm leaving",
      "lower it AND remove the 2x4", "your wing is a 2x4 with extra steps"]),
    ("exley", "Exley", "admin", "helper", 0.86, GREEN, None,
     ["happy to help, post your file", "try pulling 2 deg of timing", "send the longview and i'll look",
      "you got this, just log it first", "nice numbers, clean it up and reflash"]),
    ("zumble", "ZuMBLe", "admin", "jb4", 0.74, rgba("#5ad1c9"), None,
     ["just stack a jb4 on it", "jb4 fixes that, piggyback it", "tune plus jb4 is the move",
      "why flash when you can jb4", "jb4 map 5 and call it a day"]),
    ("bri3d", "bri3d", "admin", "hacker", 0.22, rgba("#9fb3c0"), None,
     ["...", "check the bootloader region", "it's in the ASW, not the DS",
      "i wouldn't post that publicly", "already patched, stay underground"]),
    ("brimstone", "Brimstone", "user", "needy", 0.66, rgba("#ff8a3c"), None,
     ["my car broke again guys", "why is it knocking so bad", "is 30 psi too much on stock",
      "help i think it's blown", "ran out of talent in 3rd gear"]),
    ("tacos", "Tacos", "user", "troll", 0.62, rgba("#ff5d8f"), None,
     ["just delete the cats AND the o2s", "run 40 psi, trust me bro", "lean it out for more power",
      "crank timing to 25, you'll be fine", "warranty is for cowards"]),
    ("gary", "Gary", "greenname", "money", 0.55, rgba("#36e07a"), None,
     ["i'll tune it for $300", "greennames gotta eat too", "custom fee applies",
      "cashapp and i'll send the map", "support your local tuner (me)"]),
    ("wunder", "Wunder", "greenname", "pro", 0.58, rgba("#54d98a"), None,
     ["i do remote tunes, dm me", "datalog and i'll revise it", "greenname pro tuner here",
      "my maps slap, references available", "send the stock file first"]),
    ("diggs", "Diggs", "admin", "crusty", 0.72, rgba("#9fe8c4"), "probably an alien",
     ["back in my day we didn't datalog", "i've seen faster, kid", "the skreetz remember everything",
      "your 1/4 is embarrassing", "earthlings can't tune", "humans, always rushing the tune"]),
    ("kumar", "Kumar", "greenname", "broke", 0.60, rgba("#7ec98f"), "tunes 4 food",
     ["i'll tune it for a sandwich", "blew another motor, third one today", "rods are temporary, hunger is forever",
      "pay me in tacos", "it ran when i sent it i swear", "warranty? i can't afford lunch"]),
    ("sleepy", "Sleepy", "greenname", "gatekeeper", 0.45, rgba("#4cc9a0"), "gapping plugs",
     ["fresh plugs fix everything", "you'll never beat my 1/4", "what heat range you running",
      "gapped my plugs again, feels good", "post the timeslip or it didn't happen", "ngk one step colder, trust me"]),
    ("onelow", "OneLow", "user", "pops_scholar", 0.60, rgba("#ffe066"), "PhD in crackle",
     ["overrun fueling is an art form", "more spark cut, less shame", "i've studied every bang",
      "your pops are weak, add throttle", "the crackle map is poetry", "antilag is just pops with commitment"]),
    ("eric_s", "Eric S", "user", "flipper", 0.55, rgba("#d4a96a"), "buying another car",
     ["just bought another one", "selling the gti, buying an m2 monday", "everything i own is for sale",
      "had one of those, sold it", "i flip cars not tunes", "title in hand, who wants it"]),
    ("dyno_dan", "Dyno Dan", "greenname", "dyno", 0.60, rgba("#7cc4ff"), "strapped down",
     ["what'd it make on the dyno?", "numbers or it didn't happen", "that's a $75 pull",
      "tuned by feel? in this economy?", "stp corrected or bro-rrected?", "my dyno doesn't lie"]),
    ("karen_nd", "Karen_NextDoor", "user", "karen", 0.50, rgba("#ff9ec4"), "calling the HOA",
     ["i've already reported three of you", "those bangs woke my children", "i have your plate number",
      "the police are aware of this group", "this is a residential area", "i pay taxes here you know"]),
    ("vince_vortex", "Vince", "user", "boomer", 0.50, rgba("#a8b0bf"), "typing an essay",
     ["back in 2009 we did it differently", "the search function exists for a reason", "*posts six paragraphs*",
      "i covered this in my 2011 thread", "kids these days don't read the pinned", "i've been here since vortex"]),
    ("cornelius", "Cornelius", "greenname", "corn", 0.60, rgba("#e8c84a"), "blending E60",
     ["just add more corn", "what's your ethanol content?", "E85 fixes that",
      "pump gas is for cowards", "i haven't smelled gasoline in years", "blend it and re-log"]),
    ("slammed_seb", "Slammed Seb", "user", "stance", 0.55, rgba("#9b6bff"), "scraping frame",
     ["does it come lower?", "who cares about whp, is it slammed?", "scraped the oil pan again",
      "stance over horsepower, always", "fitment is everything", "can't clear my own driveway lol"]),
    ("gremlin", "BoostGremlin", "user", "gremlin", 0.60, rgba("#9ae66e"), "sending it",
     ["SEND IT", "more boost, what's the worst that happens", "delete the cat while you're in there",
      "pull the o2s, trust me", "live a little, lean it out", "we ball til it blows"]),
    ("mk5_marcus", "Marcus", "user", "hater", 0.50, rgba("#7f9ac0"), "coping in a mk5",
     ["mk5 was peak golf", "you kids and your IS38s", "my pd150 has more soul",
      "overrated chassis honestly", "back when tuning meant something", "the mk7 is a corolla with a badge"]),
    ("rhonda", "Rhonda", "greenname", "supercharger", 0.55, rgba("#46d6b8"), "boosting linearly",
     ["just supercharge it", "turbo lag is a choice", "linear power beats turbo any day",
      "i have a kit for that, dm me", "instant boost, no waiting", "the whine is the best part"]),
    ("flashfella", "FlashFella", "greenname", "remote", 0.50, rgba("#6ee0a0"), "revising your map",
     ["revision's almost ready", "send me a fresh log", "i'll have it tonight (he won't)",
      "fifty bucks a revision", "you're in my queue, relax", "did you not get my email?"]),
    ("noobnathan", "NoobNathan", "user", "noob", 0.70, rgba("#a0d8ff"), "reading the manual",
     ["where's the dipstick?", "is stage 1 safe on stock?", "what's a longview?",
      "do i need a tune to add a sticker", "just got my gti yesterday!", "how do i open the hood"]),
]

# Help-request outcome pools. Each: (effect, (lo, hi), template). ``{user}`` is the
# online member it's attributed to; ``{amt}`` the rolled magnitude. Effects:
#   cash (+$)  cred (+clout)  map (unlock a community tune)
#   part (-$, broken hardware)  clients (-clout, lost customers)
DISCORD_GOOD = [
    ("cash", (60, 220), "{user} threw you a paid flash job. +${amt}"),
    ("cash", (50, 160), "someone copied your base map and tipped you. +${amt}"),
    ("cred", (4, 13), "{user} vouched for your tune in #ecu-tuning. +{amt} clout"),
    ("cred", (3, 9), "your longview got pinned as a good example. +{amt} clout"),
    ("map", (0, 0), "{user} DM'd you a community map. Loaded into TUNE."),
    ("map", (0, 0), "{user} dropped a leaked calibration. It's in your maps now."),
]
DISCORD_BAD = [
    ("part", (120, 360), "you took {user}'s advice and bent a rod. -${amt} in parts"),
    ("part", (90, 300), "ran the lean tune {user} swore by - melted a piston. -${amt}"),
    ("clients", (4, 11), "{user} clowned your tune publicly. Lost clients, -{amt} clout"),
    ("clients", (3, 8), "a client saw the thread and bailed. -{amt} clout"),
]

# Persona outcome lean: (good_weight, bad_weight, money_pull). Subclasses nudge
# these by role (Admin trusts good, GreenName pulls money). Higher good/bad shifts
# the odds; money_pull biases a good result toward cash/maps over pure clout.
PERSONA_LEAN = {
    "pro_tuner": (1.4, 0.6, 0.1),
    "helper": (1.9, 0.3, 0.0),
    "boost": (1.0, 1.3, 0.1),
    "disaster": (0.7, 1.7, 0.0),
    "hates_2x4": (1.1, 0.7, 0.0),
    "jb4": (1.3, 0.6, 0.3),
    "hacker": (1.3, 0.4, 0.2),
    "needy": (0.6, 1.3, 0.0),
    "troll": (0.2, 2.3, 0.0),
    "money": (1.0, 0.8, 1.0),
    "pro": (1.5, 0.5, 0.6),
    "good idea fairy": (1.1, 1.0, 0.1),  # enthusiastic ideas, mixed results
    "crusty": (1.3, 0.7, 0.0),           # dry old street king, knows his stuff
    "broke": (0.9, 1.4, 1.0),            # tunes for food (money), blows motors (risk)
    "gatekeeper": (0.7, 1.1, 0.2),       # guards his 1/4 time, won't really help
    "pops_scholar": (1.4, 0.6, 0.0),     # genuinely knows pops & bangs
    "flipper": (1.0, 0.9, 0.7),          # always buying/selling, deals not tunes
    "dyno": (1.2, 0.7, 0.8),             # numbers guy, charges per pull
    "karen": (0.3, 1.8, 0.0),            # not a tuner, files complaints
    "boomer": (1.0, 0.9, 0.0),           # forum essays, sometimes dated
    "corn": (1.3, 0.7, 0.4),             # E85 evangelist
    "stance": (0.7, 1.0, 0.0),           # looks over power
    "gremlin": (0.5, 1.6, 0.0),          # eggs you on to send it
    "hater": (0.7, 1.1, 0.0),            # contrarian old-gen owner
    "supercharger": (1.2, 0.7, 0.9),     # sells SC kits
    "remote": (1.0, 1.0, 0.8),           # promises revisions, may ghost
    "noob": (0.8, 0.8, 0.0),             # clueless but harmless
}

# Someone always tells you to post a log when you ask without one.
DISCORD_NOLOG = ["post a log first", "no log, no help", "did you even search?",
                 "read the pinned before posting", "we're not mind readers, log it"]

# Keywords that make a help request look legit (better odds). A datalog word is
# weighted heavily -- the channel demands a log before anyone actually helps.
DISCORD_LOG_WORDS = ["log", "datalog", "longview", "data log"]
DISCORD_GOOD_WORDS = ["boost", "knock", "kr", "lambda", "timing", "egt", "e85", "e30",
                      "fmic", "intercooler", "downpipe", "fuel", "3rd gear", "wot", "afr", "octane"]

# Discord window layout (aspect2d units).
DISCORD_WIN = {"half_w": 1.46, "half_h": 0.80, "center_z": 0.02}
DISCORD_RAIL_W = 0.14      # server icon rail
DISCORD_CHAN_W = 0.50      # channel list column
DISCORD_MEMBER_W = 0.56    # member list column
DISCORD_MSG_LINES = 7      # messages shown in the scrollback
# Member-list caps so a big roster doesn't overflow the window (rest -> "+N more").
DISCORD_ONLINE_MAX = 8
DISCORD_OFFLINE_MAX = 5


# --------------------------------------------------------------------------
# The Bench Wizard (secret endgame): once a pro builds enough cred, a mystery
# tuner DMs a three-part Trial. Pass it -> god status + a giant one-time payout.
# Pure arcade flavour.
# --------------------------------------------------------------------------
WIZARD_CRED = 10000         # cred needed before the Wizard's DM arrives
GOD_PAYOUT  = 1_000_000     # one-time reward for passing the Trial

# --------------------------------------------------------------------------
# Amount of credit earned when completing certain things
# --------------------------------------------------------------------------
DEFAULT_UNLOCK_CRED     = 200
ECU_UNLOCK_CRED         = 100
GOD_UNLOCK_CRED         = 500       # passing the Bench Wizard's Trial (god status)

# --------------------------------------------------------------------------
# Green Name path: cross the cred bar to go verified, then sell tunes for cash
# and DM the pros (Ed / Dave) for pro-only map stages -- while the Discord stops
# spoon-feeding you in #help. EDIT FREELY (handles, lines, maps).
# --------------------------------------------------------------------------
GREEN_NAME_CRED = 200       # cred needed before the community hands you the green name

#-------------------------------------------------------------------------------
# Minimum amount allowed in the bro's bank account when braking parts or getting 
# fines
#-------------------------------------------------------------------------------
MINIMUM_BRO_BANK_VALUE = -10000

# base payout + per-whp bonus, cred gained per clean sale, chance of a bad review.
TUNE_SALE = {"base": 50, "per_whp": 0.7, "cred": 2.5, "bad_chance": 0.16}

SALE_BAD = [
    "customer flashed it in the rain, bricked it, blamed you. -4 cred",
    "bad review: 'tune felt lazy'. -4 cred",
    "buyer ran 87 octane and grenaded it. guess whose fault. -4 cred",
]

# Pro-only map stages a pro can hand a verified tuner (same shape as a tune).
PRO_MAPS = {
    "ed_stage3": {"boost": 25.0, "timing": 14.0, "lambda": 0.82, "fuel": "E30", "of": 55.0, "or": 52.0, "th": 48.0, "name": "Ed Stage 3"},
    "dave_e85": {"boost": 27.0, "timing": 15.5, "lambda": 0.79, "fuel": "E85", "of": 95.0, "or": 92.0, "th": 88.0, "name": "Dave's E85 Special"},
}

# Pros you can DM once green: (handle, name, granted map key, tunes you must have
# sold first, chatter lines). Modular -- add more pros here.
PRO_TUNERS = [
    ("ed",   "Ed",   "ed_stage3", 2, ["send a log and some $, I'll sort you", "stage 3 isn't for tourists", "you're green now, act like it"]),
    ("dave", "Dave", "dave_e85",  5, ["E85 or go home", "I only tune for people who tune", "earn it first"]),
]

# What #help says when a green name still crawls in asking for help.
DISCORD_GREEN_BRUSHOFF = [
    "you're a green name, why are you asking us lol",
    "thought you went pro? figure it out",
    "ask Ed, that's above our pay grade",
    "green name in #help, couldn't be me",
    "we don't spoon-feed green names",
]

# Trial board data. Phase 1: power the rig by clicking these in order. Phase 2:
# land the probes on the live pads, avoid the decoys. Plus board geometry (world
# units in the stage's 3D scene) and the pad color-scales.
RIG_ORDER = ["POWER", "GROUND", "DATA", "CLOCK", "ENABLE"]
PADS_LIVE = ["V+", "DATA", "CLK", "GND"]
PADS_DECOY = ["12V", "FAN", "HORN", "A/C", "CAN"]
PAD_TOP_Z = 0.28                 # z where the pogo tip contacts a pad
PIN_TOP_Z = 2.6                  # pogo pin start/return height
PAD_GOLD = rgba("#c9a227")
PAD_GREEN = (0.4, 1.6, 0.7, 1)   # color scale for a probed live pad
PAD_RED = (1.9, 0.35, 0.35, 1)   # color scale for a decoy flash

# Every map that can land in bro.unlocked_maps (Discord community + pro-granted),
# resolved by apply + the TUNE selector. (Discord's random pool stays COMMUNITY_MAPS.)
UNLOCKABLE_MAPS = {**COMMUNITY_MAPS, **PRO_MAPS}

# Karen meter: cools down whenever you're not making noise; if it tops out the
# cops roll up and write a citation. Repeatable -- every cap-out is a new bust.
KAREN_COOLDOWN_PER_SEC = 3.0   # 100% -> 0 in ~17 s of silence
KAREN_HEAT_CONST = 5.0
POP_CRED_CONST = 18.0
BUST_FINE = 250                # base citation; scaled by your cred / rep
KAREN_AFTER_BUST = 30.0        # they don't forget instantly

POP_UNLOCKS = {
    50: ("burble_brain", "Burble Brain", 150),
    90: ("cat_delete", "Cat Delete Speedrun", 300),
    150: ("onelow", "Onelow status", 600),
}

BUST_UNLOCKS = {
    1: ("menace", "Neighborhood Menace", 150),
    2: ("karen_killer", "Karen Killer", 300),
    2: ("on_parol", "Out On Parole", 600),
}

# --------------------------------------------------------------------------
# Emotional Damage (0..100): getting clowned -- a bad Discord outcome, a blown
# motor, a cop bust, a bad tune review, a lost race -- piles on. High ED gives
# the bro the shakes: he loses power and launch grip on the strip. Wins heal it.
# --------------------------------------------------------------------------
ED_RACE_WHP_PENALTY = 0.18     # fraction of whp lost at 100% ED
ED_RACE_GRIP_PENALTY = 0.22    # fraction of launch grip lost at 100% ED
ED_HEAL_ON_WIN = 30.0
ED_LOSS = 8.0                  # losing a race stings
ED_DISCORD_BAD = 12.0          # got bad advice / clowned in #help
ED_DISCORD_GOOD_HEAL = 4.0     # a good outcome cheers you up a little
ED_BLOWN = 15.0                # grenading an engine hurts
ED_BAD_REVIEW = 8.0            # a bricked customer
ED_BUST = 10.0                 # the cops, humiliating
ED_TAUNT_THRESHOLD = 50        # at/above this, the crew piles on

# When ED is high the crew piles on -- one of these is logged as a chat-style ping.
ED_TAUNTS = [
    "tacos: ratio. + post a log. + cope.",
    "cp4334: bent another one? rods are merely suggestions.",
    "Simon: this is why we tell you to post a log.",
    "tacos: skill issue (affectionate)",
    "Mike: more boost would've fixed that. (it would not have)",
    "JC: that's a 2x4 problem. it's always a 2x4 problem.",
    "the FB group screenshotted your build. brutal.",
]

# --------------------------------------------------------------------------
# Dyno Dave: reactive one-liners keyed by event pool. ``game.dave(pool)`` picks
# one and the Notifications overlay drains it into his bubble. EDIT FREELY.
# --------------------------------------------------------------------------
DAVE_LINES = {
    "flash": ["Aight, she's flashed. Try not to grenade it.", "New map's in - let's make some noise.", "Flashed clean. Go cause problems."],
    "mapswitch": ["Stalk magic. Civilized.", "Map swap on the fly, you animal.", "Cops around? Slap it to valet."],
    "bigbang": ["That one set off car alarms. Beautiful.", "Somewhere a Prius is crying.", "I felt that in my fillings.", "Cats? We don't do cats here."],
    "cops": ["The whole street knows your plate now. Worth it.", "Noise complaint AND legend status. Balanced."],
    "dyno": ["Numbers don't lie. The dyno might, but not today.", "That'll do. Send it again.", "Decent pull - chase a little more."],
    "sgrade": ["S-grade?! Tuner of the year, baby.", "Now THAT is a tune. Frame it."],
    "blown": ["...we don't talk about that one.", "That's a rebuild. GoFundMe time.", "Money shift. Classic. Painful."],
    "win": ["GET THAT MONEY. Easy work.", "He never stood a chance.", "Cash money - go buy a turbo."],
    "lose": ["Oof. Hit the shop and run it back.", "He spanked you. Tune up.", "Slower car, faster wallet... oh wait."],
    "shop": ["Bolted on - she's meaner now.", "Good buy. Now go use it.", "Money well spent, for once."],
    "green": ["You went GREEN, baby. Verified and everything.", "Green name. Now the noobs DM you.", "You're official. Don't let it go to your head."],
    "sell": ["Sold a tune to some poor soul. Cha-ching.", "Another satisfied (?) customer.", "You're a tune mill now."],
    "pro": ["Talking to the pros now, huh.", "Networking. Gross. Profitable.", "Big leagues."],
    "wizard": ["The Wizard wants a word. Don't keep him waiting.", "A secret tuner trial just dropped. Go.", "Some hooded guy DM'd you. Spooky. Click it."],
    "god": ["GOD STATUS. Nobody can tell you anything now.", "You passed the Trial. Unreal.", "Infinite-ish money. Go nuts."],
}
