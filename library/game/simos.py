from __future__ import annotations

from library.core.constants import TUNE_THRESHOLDS
from library.game.tuning import compute_tune
from library.core.utils import pick


def build_context(game, tab: str = "") -> dict:
    car, bro = game.car, game.bro
    tune = car.flashed_tune if car.flashed and car.flashed_tune else car.tune
    result = compute_tune(tune, car.mods)
    owned_mods = [name for name, owned in car.mods.items() if owned]
    return {
        "connected": car.connected,
        "read": car.read,
        "patched": car.patched,
        "flashed": car.flashed,
        "switch_patch": car.switch_patch,
        "dirty": car.dirty,
        "tab": tab,
        "tune": tune,
        "result": result,
        "cash": bro.cash,
        "mods": car.mods,
        "owned_mods": owned_mods,
        "mod_count": len(owned_mods),
        "karen": bro.karen,
        "cred": bro.cred,
        "selected_rival": bro.selected_rival,
        "unlocked_rival": bro.unlocked_rival,
        "race_active": game.race_active(),
        "grade": car.grade,
        "active_slot": car.active_slot,
    }


RULES = [
    {
        "id": "not_connected",
        "priority": 100,
        "when": lambda c: not c["connected"],
        "roasts": [
            "You haven't even plugged the cable in. Bold of you to ask me anything.",
            "Step one says Connect OBD. You are at step zero. Inspiring.",
            "I cannot roast a car that is not talking to the laptop. Plug in, genius.",
            "The ECU is over there, untouched, living in peace. Ruin that peace.",
        ],
        "tips": [
            "Bench tab -> 1 Connect OBD. The cable goes in the car. Revolutionary.",
            "Start with the bench flow: connect, read, patch, flash.",
            "No data, no tune. Connect first, then I can be useful and mean.",
        ],
    },
    {
        "id": "connected_not_read",
        "priority": 92,
        "when": lambda c: c["connected"] and not c["read"],
        "roasts": [
            "You shook hands with the ECU and then stared at it. Beautiful use of technology.",
            "The cable works. The laptop works. The missing piece is courage.",
            "Connected but not read. That is like opening the fridge and refusing to look inside.",
        ],
        "tips": [
            "Click Read ECU. We need the calibration before we can commit crimes against drivability.",
            "Bench tab -> 2 Read ECU. Archive stock before making it spicy.",
        ],
    },
    {
        "id": "read_not_patched",
        "priority": 90,
        "when": lambda c: c["read"] and not c["patched"],
        "roasts": [
            "You read the ECU and then got shy. The boot patch is waiting.",
            "Stock file archived. Now quit admiring the backup and unlock writing.",
        ],
        "tips": [
            "Bench tab -> 3 Boot Patch. Unlock writing, then the fun starts.",
            "Patch first, tune second, flash third. Try not to invent a fourth step called panic.",
        ],
    },
    {
        "id": "patched_not_flashed",
        "priority": 88,
        "when": lambda c: c["patched"] and not c["flashed"],
        "roasts": [
            "Unlocked and bone stock. That is a gym membership you never use.",
            "All that handshaking and not one byte written. Commitment issues?",
            "You opened the door and then refused to walk through it. Very dramatic.",
        ],
        "tips": [
            "Build a map, then Flash ECU. The car will not tune itself.",
            "Flash once to unlock dyno, skreets, race, and shop progression.",
        ],
    },
    {
        "id": "dirty_tune",
        "priority": 84,
        "when": lambda c: c["dirty"],
        "roasts": [
            "Nice changes. Shame the ECU has not seen them.",
            "You tuned the laptop, not the car. Flash it.",
            "Those sliders are decorative until you write the file.",
        ],
        "tips": [
            "Bench tab -> Flash ECU again after map changes.",
            "If you want the new map in a slot, assign it after flashing or reflash with switch patch on.",
        ],
    },
    {
        "id": "engine_blown",
        "priority": 120,
        "when": lambda c: c["result"]["blown"],
        "roasts": [
            "That is not a tune, it is a crime scene with a voided warranty.",
            "You turned a perfectly good GTI into modern art. The medium is shrapnel.",
            "I have seen E85 do many things. Becoming a flare is new. Congrats.",
            "The rods just filed a workplace complaint.",
        ],
        "tips": [
            "Richen lambda toward 0.80, pull boost and timing, then fit FMIC plus Port Injection.",
            "Drop timing 2-3 deg, add ethanol, buy the FMIC, and stop bullying the turbo.",
        ],
    },
    {
        "id": "high_kr",
        "priority": 96,
        "when": lambda c: c["result"]["KR"] > TUNE_THRESHOLDS["kr_bad"],
        "roasts": [
            "{KR:.1f} deg of KR - it makes power in spite of you, not because of you.",
            "The engine is flinching. Listen to it.",
            "{KR:.1f} deg knock retard. That is not feedback, that is a distress signal.",
            "Timing so spicy the ECU is actively undoing your personality.",
        ],
        "tips": [
            "Drop peak timing 2 deg, step up fuel, or buy the FMIC.",
            "Less timing or more octane. Pick one before the pistons pick for you.",
            "E30 or E85 gives headroom; FMIC helps keep the ECU from yanking timing.",
        ],
    },
    {
        "id": "lean_stock_fuel",
        "priority": 94,
        "when": lambda c: c["tune"]["lambda"] > TUNE_THRESHOLDS["lean_lambda"] and not c["mods"]["fuel"],
        "roasts": [
            "Lambda {lambda:.2f} on stock fueling. That is how you make expensive confetti.",
            "That mixture is leaner than my patience.",
            "Lean plus boost equals the bad kind of bang.",
        ],
        "tips": [
            "Richen lambda toward 0.82 or buy Port Injection + LPFP.",
            "Fuel system first if you insist on lean high-boost heroics.",
        ],
    },
    {
        "id": "hot_egt",
        "priority": 82,
        "when": lambda c: c["result"]["egt"] > TUNE_THRESHOLDS["egt_hot"],
        "roasts": [
            "{egt:.0f} C pre-turbo. Spicy.",
            "You could forge steel in that manifold.",
            "Your downpipe is not glowing from happiness.",
            "The exhaust side is applying for lava status.",
        ],
        "tips": [
            "Trim overrun, richen lambda, or add the Intercooler.",
            "Pops are fun. Molten hardware is paperwork. Back the sliders down.",
        ],
    },
    {
        "id": "low_reliability",
        "priority": 78,
        "when": lambda c: c["result"]["rel"] < TUNE_THRESHOLDS["rel_low"] and not c["result"]["blown"],
        "roasts": [
            "Reliability {rel:.0f}%. One cold morning from a tow truck.",
            "That build has the lifespan of a marketplace promise.",
            "Fast once is not a build strategy.",
        ],
        "tips": [
            "Cool it with FMIC, a little less boost, and richer lambda.",
            "A running engine beats a fast paperweight.",
        ],
    },
    {
        "id": "quiet_pop",
        "priority": 62,
        "when": lambda c: c["result"]["pop"] < TUNE_THRESHOLDS["pop_quiet"],
        "roasts": [
            "That burble index is a polite cough.",
            "Where are the bangs? I came for fireworks.",
            "Your exhaust is quieter than a dealership waiting room.",
        ],
        "tips": [
            "Crank Overrun Fueling and Spark Cut, then add the downpipe.",
            "Load Crackle Monster if you want the neighborhood group chat awake.",
        ],
    },
    {
        "id": "wild_pop",
        "priority": 56,
        "when": lambda c: c["result"]["pop"] > TUNE_THRESHOLDS["pop_wild"],
        "roasts": [
            "That burble index is basically a noise complaint generator.",
            "You built a rolling doorbell-camera incident.",
            "The cats are not deleted, they are preparing a resignation letter.",
        ],
        "tips": [
            "Keep a quiet switch slot ready before the Karen meter goes nuclear.",
            "Downpipe makes it louder; FMIC keeps the rest from cooking itself.",
        ],
    },
    {
        "id": "stock_turbo_overworked",
        "priority": 60,
        "when": lambda c: c["tune"]["boost"] > TUNE_THRESHOLDS["stock_turbo_boost_limit"] and not c["mods"]["turbo"],
        "roasts": [
            "{boost:.1f} psi out of the stock turbo. You can hear it sweating.",
            "You are asking the little turbo for big-turbo numbers. It is wheezing.",
        ],
        "tips": [
            "Buy the Hybrid Turbo IS38+ before chasing more boost.",
            "Past about 24 psi the stock turbo is mostly making heat and excuses.",
        ],
    },
    {
        "id": "cash_low",
        "priority": 50,
        "when": lambda c: c["cash"] < TUNE_THRESHOLDS["cash_low"],
        "roasts": [
            "${cash} to your name. Cannot afford an air freshener, let alone a turbo.",
            "You are broker than a half-finished marketplace build.",
        ],
        "tips": [
            "Race the Civic for the purse. Even this thing can take a Civic.",
            "Launch on green, shift at redline, collect money, buy parts.",
        ],
    },
    {
        "id": "cash_hoard",
        "priority": 48,
        "when": lambda c: c["cash"] > TUNE_THRESHOLDS["cash_hoard"] and c["mod_count"] < 2,
        "roasts": [
            "${cash} banked and a near-stock car. Saving for retirement?",
            "Hoarding cash like it makes horsepower. It does not.",
            "Your wallet is faster than the car.",
        ],
        "tips": [
            "Shop tab. Downpipe for noise, FMIC for safety, Hybrid Turbo for power.",
            "Stop counting money and convert it into questionable hardware.",
        ],
    },
    {
        "id": "karen_hot",
        "priority": 70,
        "when": lambda c: c["karen"] > TUNE_THRESHOLDS["karen_hot"],
        "roasts": [
            "The whole skreets has your plate memorized.",
            "You are three bangs from a citation and a doorbell-camera compilation.",
        ],
        "tips": [
            "Assign a quiet Valet map and switch before things get expensive.",
            "Let the Karen meter cool or swap to a tame slot.",
        ],
    },
    {
        "id": "no_switch_patch",
        "priority": 42,
        "when": lambda c: c["flashed"] and not c["switch_patch"],
        "roasts": [
            "Running one map like it is 2009. Live a little.",
            "No switch patch means no instant valet map when things get spicy.",
        ],
        "tips": [
            "Reflash with Switch Patch ON for valet, daily, and full menace slots.",
            "Four maps means one can be fast, one loud, one safe, and one for pretending you are responsible.",
        ],
    },
    {
        "id": "good_build",
        "priority": 30,
        "when": lambda c: c["result"]["rel"] > TUNE_THRESHOLDS["rel_good"] and c["result"]["pop"] > 60 and c["result"]["whp"] > 320 and c["result"]["KR"] < 1,
        "roasts": [
            "Annoyingly competent. I wanted to roast harder.",
            "{whp:.0f} whp, decent reliability, and it bangs. Fine. It is good.",
        ],
        "tips": [
            "Now go take the Rival Shop Mk7's lunch money.",
            "Sneak a touch more timing only if knock stays quiet.",
        ],
    },
    {
        "id": "bench_tab_hint",
        "priority": 20,
        "when": lambda c: c["tab"] == "bench" and c["flashed"],
        "roasts": [
            "Back at the bench like the car asked for a performance review.",
            "The laptop is not a dyno. Helpful, but not a dyno.",
        ],
        "tips": [
            "After flashing, use Dyno to grade it or Skreets to make irresponsible noises.",
            "Switch Patch ON before flashing if you want four selectable personalities.",
        ],
    },
    {
        "id": "street_tab_hint",
        "priority": 20,
        "when": lambda c: c["tab"] == "street" and c["flashed"],
        "roasts": [
            "You came here for the bangs. I respect the honesty.",
            "This is where subtlety goes to die.",
        ],
        "tips": [
            "Use Preview Pops to build cred, but watch the Karen meter.",
            "A quieter slot is not cowardice. It is tactical plausible deniability.",
        ],
    },
    {
        "id": "race_tab_hint",
        "priority": 20,
        "when": lambda c: c["tab"] == "race" and c["flashed"],
        "roasts": [
            "Remember: red lights are for people who want to lose with confidence.",
            "Horsepower is cute. Traction is what cashes checks.",
        ],
        "tips": [
            "Launch on green and shift with Space. Buy clutch and wheels if it feels lazy.",
            "Beat the current rival to unlock the next purse.",
        ],
    },
    {
        "id": "fallback",
        "priority": 1,
        "when": lambda c: True,
        "roasts": [
            "Nothing is actively on fire. Low bar, cleared.",
            "I have seen worse. I have also seen much, much better.",
            "It moves. Thrilling.",
        ],
        "tips": [
            "Dyno it, race it, spend the money, repeat.",
            "Chase power on the dyno, bangs in the maps, cash on the strip.",
        ],
    },
]


def select_insight(context: dict, tick: int = 0) -> dict:
    eligible = [rule for rule in RULES if rule["when"](context)]
    eligible.sort(key=lambda rule: rule["priority"], reverse=True)
    rule = eligible[tick % max(1, min(4, len(eligible)))]
    data = {
        "KR": context["result"]["KR"],
        "egt": context["result"]["egt"],
        "rel": context["result"]["rel"],
        "pop": context["result"]["pop"],
        "whp": context["result"]["whp"],
        "boost": context["tune"]["boost"],
        "lambda": context["tune"]["lambda"],
        "cash": context["cash"],
    }
    return {"id": rule["id"], "roast": pick(rule["roasts"]).format(**data), "tip": pick(rule["tips"]).format(**data)}
