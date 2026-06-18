from __future__ import annotations

from panda3d.core import loadPrcFileData

loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")

from library.core.panda_config import configure_panda3d

configure_panda3d()

from direct.showbase.ShowBase import ShowBase

from library.core.assets import assets
from library.core.constants import WHEEL_PREFIX, WHEEL_STATIC

app = ShowBase()


def probe(key):
    car = assets.load_model(assets.ModelType.CAR, key)
    print(f"\n=== {key}  (WHEEL_PREFIX={WHEEL_PREFIX!r}, WHEEL_STATIC={WHEEL_STATIC}) ===")
    matched = list(car.findAllMatches("**/" + WHEEL_PREFIX + "*"))
    print(f"nodes matching '{WHEEL_PREFIX}*': {len(matched)}")
    # Exactly what prepare_wheels keeps:
    parts = [n for n in matched
             if not n.getParent().getName().startswith(WHEEL_PREFIX)
             and not any(s in n.getName().lower() for s in WHEEL_STATIC)]
    print(f"prepare_wheels would keep: {len(parts)} parts")
    corners = {}
    for part in parts:
        b = part.getTightBounds(car)
        if not b:
            continue
        c = (b[0] + b[1]) * 0.5
        corners.setdefault((c.x >= 0, c.y >= 0), []).append(part)
    print(f"corner clusters: {len(corners)}  sizes={[len(v) for v in corners.values()]}")

    # Show the top-level w: nodes (parent != w:) with parent + center.
    print("top-level '" + WHEEL_PREFIX + "' nodes (name | parent | car-space center | #geom desc):")
    shown = 0
    for n in matched:
        if n.getParent().getName().startswith(WHEEL_PREFIX):
            continue
        b = n.getTightBounds(car)
        c = (b[0] + b[1]) * 0.5 if b else None
        cs = f"({c.x:+.2f},{c.y:+.2f},{c.z:+.2f})" if c else "noBounds"
        ng = len(n.findAllMatches("**/+GeomNode"))
        print(f"   {n.getName()[:34]:34s} | {n.getParent().getName()[:22]:22s} | {cs:22s} | g={ng}")
        shown += 1
        if shown >= 40:
            print("   ...(truncated)")
            break

    # Any caliper-ish nodes anywhere?
    cal = [n.getName() for n in car.findAllMatches("**/*")
           if any(s in n.getName().lower() for s in WHEEL_STATIC)]
    print(f"caliper-ish node names ({len(cal)}): {cal[:8]}")


for k in ("mk7_gti", "civic_type_r"):
    probe(k)

print("\nDONE")
