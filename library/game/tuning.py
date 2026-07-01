from __future__ import annotations

from library.core.constants import BASE_EFFECTS, DEFAULT_TUNE, FUEL, GRADE_TABLE, REPS, TUNE_THRESHOLDS
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


def compute_tune(tune: dict, mods: dict, turbo: dict | None = None) -> dict:
    """The calibration sim: turns the tune (boost/timing/lambda/fuel) into a tune-driven
    peak ``whp`` plus the safety diagnostics (knock/EGT/reliability/pop/blown). Power
    from *hardware* (intake/dp/turbo/...) is NOT here -- it flows through the curve in
    ``build_whp_curve``; mods still factor into headroom/EGT/reliability/boost ceiling.

    ``turbo`` is the selected turbo's spec (a ``PARTS`` turbo entry) and supplies the boost
    ceiling + blow-up threshold (so a CTS grenades sooner than an Arashi). When omitted,
    it falls back to the old behaviour keyed off the ``mods["turbo"]`` bool (hybrid vs
    stock limits) so bare callers (e.g. simos) are unaffected."""
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
        - (45 if mods["fmic"] else 0)
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
        + (6 if mods["fmic"] else 0)
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
                    effects: dict | None = None) -> list:
    """Compose a car's final rpm->whp curve from its stock ``base_curve`` + owned mods
    (+ tune). Returns ``[(rpm, whp), ...]`` from idle to redline.

    - ``tune_factor`` scales the whole base curve. It is a *relative* multiplier (this
      tune's power vs the stock tune, per ``compute_tune``), so it is car-agnostic -- a
      hot tune lifts any car's stock curve by the same percentage (1.0 = stock tune).
    - Each owned mod's ``spool`` shifts the sub-peak onset (- earlier / + later) and its
      ``curve`` nodes add whp, compounding (``base + scaler * running_total``). Mods are
      applied in the given order.
    - ``effects`` is the spool/curve lookup (defaults to ``BASE_EFFECTS``); a car passes its
      own table so the ``"turbo"`` entry resolves to the SELECTED turbo variant's spec."""
    effects = effects or BASE_EFFECTS
    factor = tune_factor
    peak_rpm = max(base_curve, key=lambda p: p[1])[0]
    lo_rpm, hi_rpm = base_curve[0][0], base_curve[-1][0]
    spool_delta = sum(effects[m]["spool"] for m in owned_mods)
    grid = []
    rpm = idle
    while rpm <= redline + 1:
        # Spool only reshapes the rising (sub-peak) side so a bigger turbo doesn't lose
        # top-end; above the peak the base is untouched and mods add the top-end gains.
        look = rpm - spool_delta if rpm <= peak_rpm else rpm
        look = clamp(look, lo_rpm, hi_rpm)
        whp = whp_at(base_curve, look) * factor
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
