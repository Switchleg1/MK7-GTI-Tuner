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
PANEL = rgba("#11161b", 0.66)        # translucent glass panel (rounded box fill)
PANEL_DARK = rgba("#0c1217", 0.82)   # denser glass for popups / close buttons
SIMON_PANEL = rgba("#111820", 0.98)
LINE = rgba("#22303b")
# Rounded-box styling (the ui_box / ui_ring textures are tinted by these).
BOX_LINE = rgba("#2f7d57", 0.55)     # subtle green ring around glass panels
BTN_LINE = rgba("#357f59", 0.50)     # ring around an enabled button
BTN_DISABLED_FILL = rgba("#0a0f13", 0.55)
BTN_DISABLED_TEXT = rgba("#3a4750")
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

# Garage hub + task cameras (glb car faces +Y, ~4 m long, driver side -X).
GARAGE_CAMERA = {"pos": (5.6, -7.6, 3.0), "look_at": (-0.2, 0.4, 0.7), "fov": 42}
TASK_CAMERAS = {
    "street": {"pos": (-6.2, -5.6, 2.2), "look_at": (-0.4, 1.2, 0.7), "fov": 50},
    "race": {"pos": (0.0, -9.5, 3.4), "look_at": (0.0, 7.0, 0.6), "fov": 55},
    "dyno": {"pos": (6.6, -3.2, 1.9), "look_at": (0.0, 0.2, 0.7), "fov": 45},
}

# --------------------------------------------------------------------------
# Dyno (SimosTools-style gauge cluster + live graph)
# --------------------------------------------------------------------------
DYNO_PULL_SECONDS = 4.0
DYNO_RPM_RANGE = (2200, 6800)  # sweep range (matches tuning.dyno_curve)

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
DYNO_TRACE = rgba("#4fe0ff")        # power trace (cyan)
DYNO_GRID = rgba("#1c2630")

# --------------------------------------------------------------------------
# Assets (standard formats for now: .glb models, .png images under data/)
# --------------------------------------------------------------------------
DATA_DIR = "data"
MODELS_DIR = "data/models"
IMAGES_DIR = "data/images"
AUDIO_DIR = "data/audio"

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
    ("cp4334", "CP4334", "admin", "boost", 0.78, AMBER, "Playing TunerPro",
     ["more boost fixes most things", "rods are merely suggestions", "send it to 26 and find out",
      "bent another one, worth it", "boost is a personality trait"]),
    ("mike", "Mike", "admin", "disaster", 0.70, RED, "buying a turbo",
     ["just bought another turbo", "who wants to street race tonight", "third IS38 this month",
      "my problem is boost and i refuse to fix it", "raced a cop, lost the cop"]),
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
}

# Someone always tells you to post a log when you ask without one.
DISCORD_NOLOG = ["post a log first", "no log, no help", "did you even search?",
                 "read the pinned before posting", "we're not mind readers, log it"]

# Keywords that make a help request look legit (better odds). A datalog word is
# weighted heavily -- the channel demands a log before anyone actually helps.
DISCORD_LOG_WORDS = ["log", "datalog", "longview", "data log"]
DISCORD_GOOD_WORDS = ["boost", "knock", "kr", "lambda", "timing", "egt", "e85", "e30",
                      "fmic", "intercooler", "downpipe", "fuel", "3rd gear", "wot", "afr", "octane"]

# Community maps unlockable via Discord (selectable in TUNE once unlocked).
COMMUNITY_MAPS = {
    "exley_safe": {"boost": 21.0, "timing": 12.0, "lambda": 0.82, "fuel": "93", "of": 28.0, "or": 26.0, "th": 22.0, "name": "Exley Safe 93"},
    "zumble_jb4": {"boost": 25.5, "timing": 11.0, "lambda": 0.83, "fuel": "93", "of": 40.0, "or": 38.0, "th": 35.0, "name": "Zumble JB4 Stack"},
    "wunder_remote": {"boost": 24.0, "timing": 14.0, "lambda": 0.81, "fuel": "E30", "of": 50.0, "or": 48.0, "th": 44.0, "name": "Wunder Remote v3"},
    "bri3d_leak": {"boost": 26.0, "timing": 15.0, "lambda": 0.80, "fuel": "E85", "of": 90.0, "or": 88.0, "th": 80.0, "name": "bri3d leaked E85"},
}

# Discord window layout (aspect2d units).
DISCORD_WIN = {"half_w": 1.46, "half_h": 0.80, "center_z": 0.02}
DISCORD_RAIL_W = 0.14      # server icon rail
DISCORD_CHAN_W = 0.50      # channel list column
DISCORD_MEMBER_W = 0.56    # member list column
DISCORD_MSG_LINES = 7      # messages shown in the scrollback
