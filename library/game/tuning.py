from __future__ import annotations

import math

from library.core.constants import DEFAULT_TUNE, FUEL, GRADE_TABLE, REPS, TUNE_THRESHOLDS
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
    boost_limit = TUNE_THRESHOLDS["hybrid_turbo_boost_limit"] if mods["turbo"] else TUNE_THRESHOLDS["stock_turbo_boost_limit"]
    blown_limit = TUNE_THRESHOLDS["hybrid_turbo_blown_boost"] if mods["turbo"] else TUNE_THRESHOLDS["stock_turbo_blown_boost"]
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


def grade_for_result(result: dict) -> str:
    if result["blown"]:
        return "ENGINE FAILURE - pull timing/boost and richen lambda."
    power_score = clamp((result["whp"] - 210) / (420 - 210) * 100, 0, 100)
    overall = 0.40 * power_score + 0.35 * result["pop"] + 0.25 * result["rel"]
    for minimum, grade, note in GRADE_TABLE:
        if overall >= minimum:
            return f"Grade {grade} - {round(overall)} pts - {note}"
    return "Grade D - rethink the map"
