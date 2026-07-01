from __future__ import annotations

from library.core.constants import (
    BASE_EFFECTS, DEFAULT_TUNE, FUEL, GRADE_TABLE,
    REPS, TUNE_THRESHOLDS
)
from library.core.utils import clamp


def default_tune() -> dict:
    return dict(DEFAULT_TUNE)


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


def compute_tune(tune: dict, mods: dict, turbo: dict | None = None, ic: dict | None = None,
                 flow: float = 1.0) -> dict:
    """The calibration sim: turns the tune (boost/timing/lambda/fuel) into a tune-driven
    peak ``whp`` plus the safety diagnostics (knock/EGT/reliability/pop/blown). Power
    from *hardware* (intake/dp/turbo/...) is NOT here -- it flows through the curve in
    ``build_whp_curve``; mods still factor into headroom/EGT/reliability/boost ceiling.

    ``turbo`` is the selected turbo's spec (a ``PARTS`` turbo entry) and supplies the boost
    ceiling + blow-up threshold (so a CTS grenades sooner than an Arashi). ``ic`` is the
    selected intercooler's spec and supplies the knock ``headroom`` / ``egt_relief`` /
    ``rel_bonus`` (so a bigger IC lets you lean on it harder). Either omitted falls back to
    the baseline variant keyed off its ``mods`` bool anchor, so bare callers (e.g. simos)
    are unaffected. ``flow`` (>= 1.0) is the equipped parts' airflow multiplier on the boost
    term -- higher-flowing hardware makes each psi worth more whp (see Car._boost_flow)."""
    fuel = FUEL[tune["fuel"]]
    ic = ic if ic is not None else (BASE_EFFECTS["ic"] if mods.get("ic") else None)
    headroom = fuel["head"] + (ic["headroom"] if ic else 0) + (3 if mods["fuel"] else 0)
    knock_idx = (tune["boost"] - 18) * 0.85 + (tune["timing"] - 9) * 1.25 + (tune["lambda"] - 0.82) * 14 - headroom
    kr = max(0, knock_idx) * 1.1
    effective_timing = max(2, tune["timing"] - kr)
    whp = (
        210
        + (tune["boost"] - 18) * TUNE_THRESHOLDS["boost_hp_per_psi"] * flow
        + (effective_timing - 9) * 3.8
        + fuel["pwr"]
        - abs(tune["lambda"] - 0.83) * 40
    )
    # A bigger turbo (any aftermarket unit) relieves EGT; a specific turbo sets the
    # boost ceiling + blow-up threshold (else fall back to the hybrid/stock bool limits).
    has_turbo = turbo is not None or mods["turbo"]
    egt = (
        720
        + (tune["boost"] - 18) * 9
        + kr * 12
        + (tune["lambda"] - 0.82) * 220
        + tune["of"] * 1.4
        + tune["or"] * 1.7
        - (ic["egt_relief"] if ic else 0)
        - (25 if has_turbo else 0)
    )
    pop = pop_score(tune)
    if turbo is not None:
        boost_limit, blown_limit = turbo["boost_limit"], turbo["blown_boost"]
    elif mods["turbo"]:
        boost_limit = TUNE_THRESHOLDS["hybrid_turbo_boost_limit"]
        blown_limit = TUNE_THRESHOLDS["hybrid_turbo_blown_boost"]
    else:
        boost_limit = TUNE_THRESHOLDS["stock_turbo_boost_limit"]
        blown_limit = TUNE_THRESHOLDS["stock_turbo_blown_boost"]
    rel = (
        100
        - max(0, knock_idx) * 6
        - max(0, tune["boost"] - boost_limit) * 5
        - max(0, egt - 950) * 0.13
        - max(0, tune["lambda"] - 0.86) * (40 if mods["fuel"] else 140)
        - pop * 0.16
        + (ic["rel_bonus"] if ic else 0)
    )
    rel = clamp(rel, 0, 100)
    blown = (knock_idx > 7 and tune["lambda"] > 0.86 and not mods["fuel"]) or egt > TUNE_THRESHOLDS["egt_blown"] or (tune["boost"] > blown_limit and rel < 22)
    return {"whp": clamp(whp, 160, 640), "KR": kr, "knockIdx": knock_idx, "egt": egt, "rel": rel, "pop": pop, "blown": blown}


def whp_at(curve: list, rpm: float) -> float:
    """Linear-interpolate whp at ``rpm`` on a sorted ``[(rpm, whp), ...]`` curve
    (flat-held outside the curve's range)."""
    if not curve:
        return 0.0
    if rpm <= curve[0][0]:
        return curve[0][1]
    if rpm >= curve[-1][0]:
        return curve[-1][1]
    for i in range(1, len(curve)):
        r0, w0 = curve[i - 1]
        r1, w1 = curve[i]
        if rpm <= r1:
            t = (rpm - r0) / (r1 - r0) if r1 > r0 else 0.0
            return w0 + t * (w1 - w0)
    return curve[-1][1]


def _mod_curve_value(nodes: list, rpm: float):
    """Interpolate a mod's ``[(rpm, base_add, scaler), ...]`` nodes at ``rpm`` -> (base,
    scaler). Zero below the first node (the mod isn't in its band yet), held above the
    last."""
    if not nodes or rpm <= nodes[0][0]:
        return (0.0, 0.0)
    if rpm >= nodes[-1][0]:
        return (nodes[-1][1], nodes[-1][2])
    for i in range(1, len(nodes)):
        r0, b0, s0 = nodes[i - 1]
        r1, b1, s1 = nodes[i]
        if rpm <= r1:
            t = (rpm - r0) / (r1 - r0) if r1 > r0 else 0.0
            return (b0 + t * (b1 - b0), s0 + t * (s1 - s0))
    return (nodes[-1][1], nodes[-1][2])


def build_whp_curve(base_curve: list, owned_mods: list, tune_factor: float = 1.0,
                    idle: int = 900, redline: int = 6700, step: int = 100,
                    effects: dict | None = None, spool_rpm: int = 3000) -> list:
    """Compose a car's final rpm->whp curve from its stock ``base_curve`` + owned mods
    (+ tune). Returns ``[(rpm, whp), ...]`` from idle to redline.

    The model is NA-floor + boost ramp: the engine always makes an off-boost floor
    (``na_power_frac`` of the full curve), and boost ramps IN over an effective width,
    reaching full at the spool ONSET (``spool_rpm`` + the parts' ``spool`` delta). So each
    rpm's power = ``base(rpm) * tune_factor * (na_frac + (1-na_frac) * spool_frac)`` plus the
    mods' top-end ``curve`` adders. At full spool this equals ``base * tune_factor`` (peak +
    grades unchanged); below onset it tapers to the NA floor so low-rpm power -- and the
    dyno's ``whp*5252/rpm`` torque -- rise realistically instead of flat-holding/spiking.

    - ``tune_factor`` scales the whole base curve (this tune's power vs stock, car-agnostic).
    - Each owned mod's ``spool`` slides the boost ONSET (- earlier / + later; a bigger turbo
      spools later) and its ``spool_width`` widens/narrows the ramp (+ turbos = laggier,
      - flow mods = quicker); the effective width = ``spool_width`` base + the parts' deltas,
      floored at ``spool_width_min``. Its ``curve`` nodes add whp on top, compounding.
    - ``effects`` is the spool/curve lookup (defaults to ``BASE_EFFECTS``); a car passes its
      own table so ``"turbo"``/``"ic"`` resolve to the SELECTED variant. ``spool_rpm`` is the
      car's base spool point (CAR_TABLE)."""
    effects = effects or BASE_EFFECTS
    factor = tune_factor
    lo_rpm = base_curve[0][0]
    na_frac = TUNE_THRESHOLDS["na_power_frac"]
    onset = spool_rpm + sum(effects[m]["spool"] for m in owned_mods)  # rpm where boost is fully in
    # Ramp width: stock base widened by turbos (laggier) / narrowed by flow mods (dp/IC/intake).
    width = max(TUNE_THRESHOLDS["spool_width_min"],
                TUNE_THRESHOLDS["spool_width"] + sum(effects[m].get("spool_width", 0) for m in owned_mods))
    grid = []
    rpm = idle
    while rpm <= redline + 1:
        # Boost ramps in over `width` rpm, full AT the onset; below that it's the NA floor.
        spool_frac = clamp((rpm - (onset - width)) / width, 0.0, 1.0)
        whp = whp_at(base_curve, rpm) * factor * (na_frac + (1.0 - na_frac) * spool_frac)
        # Keep the very bottom (below the base curve's first rpm, which flat-holds) low but
        # NEVER zero -- races launch off this floor -- while still climbing so the dyno torque
        # trace doesn't hook at idle: taper from half the floor at idle up to full at lo_rpm.
        if rpm < lo_rpm and lo_rpm > idle:
            whp *= 0.5 + 0.5 * clamp((rpm - idle) / (lo_rpm - idle), 0.0, 1.0)
        accumulated = 0.0
        for mod_id in owned_mods:
            base, scaler = _mod_curve_value(effects[mod_id]["curve"], rpm)
            add = base + scaler * accumulated
            whp += add
            accumulated += add
        grid.append((rpm, max(0.0, whp)))
        rpm += step
    return grid


def grade_for_result(result: dict) -> str:
    if result["blown"]:
        return "ENGINE FAILURE - pull timing/boost and richen lambda."
    power_score = clamp((result["whp"] - 210) / (420 - 210) * 100, 0, 100)
    overall = 0.40 * power_score + 0.35 * result["pop"] + 0.25 * result["rel"]
    for minimum, grade, note in GRADE_TABLE:
        if overall >= minimum:
            return f"Grade {grade} - {round(overall)} pts - {note}"
    return "Grade D - rethink the map"
