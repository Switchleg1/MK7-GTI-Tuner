from __future__ import annotations

from panda3d.core import Vec4

from library.core.utils import rgba


APP_NAME = "MK7 GTI Tuner"
WINDOW_TITLE = "MK7 GTI Tuner - Panda3D"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_ASPECT = 16 / 9
DEFAULT_FOV_DEG = 105

TRACK_M = 402.336
GEAR_RATIOS = [3.6, 2.1, 1.43, 1.03, 0.84, 0.69]
FINAL_DRIVE = 3.65
TIRE_CIRC = 1.96

UI_REFRESH_SECONDS = 0.25
MAX_LOG_LINES = 20

BG = rgba("#070a0d")
PANEL = rgba("#11161b", 0.94)
PANEL_DARK = rgba("#0c1217", 0.96)
SIMON_PANEL = rgba("#111820", 0.98)
LINE = rgba("#22303b")
TEXT = rgba("#cfe3ee")
DIM = rgba("#7d93a3")
MUTED = rgba("#41535f")
GREEN = rgba("#36e07a")
GREEN_2 = rgba("#0f7a3e")
AMBER = rgba("#ffb338")
RED = rgba("#ff4d52")
BLUE = rgba("#4fb6ff")
VIOLET = rgba("#b58bff")
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
    "stock": {"boost": 18.0, "timing": 10.0, "lambda": 0.85, "fuel": "91", "of": 8.0, "or": 6.0, "th": 5.0, "name": "Stock"},
    "stage1": {"boost": 22.0, "timing": 13.0, "lambda": 0.83, "fuel": "93", "of": 30.0, "or": 28.0, "th": 25.0, "name": "Stage 1"},
    "stage2": {"boost": 24.5, "timing": 14.0, "lambda": 0.82, "fuel": "E30", "of": 45.0, "or": 42.0, "th": 40.0, "name": "Stage 2 E30"},
    "crackle": {"boost": 23.0, "timing": 13.0, "lambda": 0.84, "fuel": "E30", "of": 95.0, "or": 92.0, "th": 85.0, "name": "Crackle Monster"},
}

MODS = [
    ("intake", "Cold Air Intake", 120, "+6 whp, quicker spool."),
    ("dp", "Catless Downpipe", 250, "+12 whp and much louder bangs. Cops notice fast."),
    ("fmic", "Front-Mount Intercooler", 300, "More knock headroom and lower EGT."),
    ("clutch", "Stage 2 Clutch + LSD", 450, "Launch grip for the strip."),
    ("wheels", "Lightweight Wheels", 200, "Less rotating weight."),
    ("fuel", "Port Injection + LPFP", 700, "Feeds E85 safely."),
    ("turbo", "Hybrid Turbo IS38+", 900, "Raises boost ceiling."),
]

RIVALS = [
    {"name": "Stock Civic", "whp": 158, "weight": 1280, "grip": 0.90, "purse": 120, "color": rgba("#9fb3c0")},
    {"name": "Civic Si", "whp": 208, "weight": 1300, "grip": 0.92, "purse": 230, "color": rgba("#e6e6e6")},
    {"name": "WRX STI", "whp": 300, "weight": 1520, "grip": 1.18, "purse": 480, "color": rgba("#3a6ad6")},
    {"name": "BMW M2", "whp": 385, "weight": 1560, "grip": 1.00, "purse": 850, "color": rgba("#222222")},
    {"name": "Rival Shop Mk7", "whp": 365, "weight": 1370, "grip": 1.06, "purse": 1600, "color": rgba("#e7232b")},
]

REPS = [(0, "Civic Bait"), (60, "Cars & Coffee Regular"), (160, "Local Legend"), (340, "Wanted by the HOA")]
TABS = [("bench", "BENCH"), ("maps", "MAPS"), ("dyno", "DYNO"), ("street", "STREET"), ("race", "RACE"), ("shop", "SHOP")]

CAMERA_BY_TAB = {
    "default": {"pos": (0, -16, 5.8), "look_at": (0, 0, 1.0)},
    "street": {"pos": (0, -18, 4.3), "look_at": (0, 4, 0.7)},
    "race": {"pos": (0, -20, 7), "look_at": (0, 5, 0.5)},
    "shop": {"pos": (5, -13, 5), "look_at": (0, 0, 0.7)},
}

# --------------------------------------------------------------------------
# Assets (standard formats for now: .glb models, .png images under data/)
# --------------------------------------------------------------------------
DATA_DIR = "data"
MODELS_DIR = "data/models"
IMAGES_DIR = "data/images"

MODEL_FILES = {
    "ground": "ground.glb",
    "car": "car.glb",
    "character": "character.glb",
    "phone": "phone.glb",
    "obd": "obd.glb",
}
IMAGE_FILES = {
    "wallpaper": "phone_wallpaper.png",
    "app_icon": "simostools_icon.png",
    "check": "flash_complete.png",
    "logo": "logo.png",
}

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
    ("street", "STREET", "Bangs, pops & cred"),
    ("race", "RACE", "Quarter-mile street ladder"),
    ("shop", "SHOP", "Spend winnings on mods"),
    ("bench", "BENCH", "Re-flash new staged maps"),
]
