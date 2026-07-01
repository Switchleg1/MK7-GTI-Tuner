# MK7 GTI Tuner (3D) — quick context for Claude

A 3D Panda3D remake of the *MK7 GTI Tuner* parody game: build a Mk7 GTI, flash maps,
chase dyno numbers, race the street ladder, sell sketchy tunes, dodge Karen, climb an
arcade scoreboard, and beat the Bench Wizard's endgame. Player-facing overview is
`README.md`. **The deep per-file map + subsystem guide + the full gotcha list live in
`architecture.md` — read it before any non-trivial change.**

- **Stack:** Python 3.x, Panda3D 1.10.x. `panda3d-gltf` loads the `.glb` models at runtime;
  `pygltflib` *generates* them (asset rebuild only). No other runtime deps.
- **Entry point:** `mk7_gti_tuner.py` → `configure_panda3d()` → `library.game.app.MK7Tuner3D`.
- **Run:** `python mk7_gti_tuner.py`.  **Package:** `build.bat` (PyInstaller `--onefile
  --windowed`; **must** bundle `data/` — assets resolve from `sys._MEIPASS` when frozen,
  project root from source).
- **Rebuild generated assets:** `python -m library.assetgen.generate_assets` (offline; NOT
  shipped). **Do NOT** regen over the hand-made detailed car `.glb`s (`mk7_gti` / `civic_type_r`
  / `wrx_sti` — they're hand-inserted, not produced by `asset_car.py`).

## Verifying a change — the standard pattern (no GUI automation here)
There's no full GUI test harness; verify **offscreen** by constructing the app headless,
driving it, then screenshotting and reading the PNG back:
```python
from panda3d.core import loadPrcFileData, Filename
loadPrcFileData("", "window-type offscreen"); loadPrcFileData("", "audio-library-name null")
from library.core.panda_config import configure_panda3d; configure_panda3d()
from library.game.app import MK7Tuner3D
app = MK7Tuner3D()
for _ in range(3): app.taskMgr.step()
app.on_unlocked(); app.open_task("shop")          # reach the hub + open a task
for _ in range(3): app.taskMgr.step()
app.win.saveScreenshot(Filename.fromOsSpecific("_x.png"))
```
Also run `python -m compileall -q library`. Put scratch scripts/PNGs in the repo root and
**delete them when done**. Commit/push ONLY when the user asks.

## Layout (one class per file; absolute imports `from library.<sub>.<mod>`)
Only `mk7_gti_tuner.py` is at root. `library/core` (constants, utils, panda_config, assets/,
audio, music, config, storage, **ui/** — the managed-widget toolkit), `library/game` (app,
game, tuner_bro, car, car_library, rival_green_name, discord*, tuning, simos, scoreboard,
geometry), `library/stages` (hud, task_base, the stages incl. `shop_item`/`review_overlay`
+ `tasks/`), `library/assetgen` (offline, not bundled). `data/` stays at root. See `architecture.md` for the
per-file map.

## Conventions & gotchas (load-bearing; the rest are in architecture.md)
- **`constants.py` is the single source of every tunable** — numbers, colours, asset paths,
  poses, and the data tables (`CAR_TABLE`, `PARTS`, `ACHIEVEMENTS`, `RIVALS`, `DAVE_LINES`, …).
  Prefer one more table row over an `if/elif` staircase. One class per file.
- **`PARTS` is the ONE catalog** of everything buyable — each row holds its shop copy
  (name/price/blurb/review/accent/`image`) AND its curve effect (spool/weight/grip/max_boost/
  curve). `kind` is one of: `"mod"` (cumulative bolt-on), `"turbo"` (adds `boost_limit`/
  `blown_boost`/`dave_on_blow`/`ed_cut`), `"ic"` (intercooler; adds `headroom`/`egt_relief`/
  `rel_bonus`). Derived indices (`MOD_IDS`/`TURBO_IDS`/`IC_IDS`/`MOD_KEYS`/`BASE_EFFECTS`) are
  views into it — add a part = add one `PARTS` row. `image` is the card thumbnail: an
  `IMAGE_FILES` key, or `""` for the accent-coloured placeholder tile.
- **Equippable families** (own many, equip one) are declared in `constants.EQUIP_FAMILIES`:
  `kind → {equipped, owned, anchor, default}` naming the `Car` attrs (`turbo`/`owned_turbos`,
  `ic`/`owned_ic`) + the `Car.mods` bool anchor. `Car.buy_mod`/`equip_mod` and
  `ShopItem.is_owned`/`is_equipped` are **generic over this table** — adding a family (e.g.
  exhaust) is one `EQUIP_FAMILIES` row + `kind` on the parts, no new methods. `compute_tune`
  takes the fitted `turbo`/`ic` specs (caps + headroom) plus a `flow` multiplier
  (`Car._boost_flow` = 1 + every equipped part's `flow`) so each psi of boost is worth more
  whp on higher-flowing hardware; the base rate is `TUNE_THRESHOLDS["boost_hp_per_psi"]`. The boost
  slider's ceiling is `Car.boost_slider_max()` (stock `max_boost`, or the fitted turbo's
  `blown_boost`).
- **Geometry is authored Z-up** and loaded with `gltf.load_model(path,
  GltfSettings(skip_axis_conversion=True))` (car faces **+Y**, driver side **−X**). Use
  `render.setShaderAuto()` + `AntialiasAttrib.MMultisample` — NOT `MAuto` (draws wireframe
  edges) and NOT simplepbr (asserts under manual offscreen `renderFrame()`).
- **Managed UI objects** (`library/core/ui`, a `UIObjectController` per screen): build each
  widget ONCE, then tweak in place (`get(key).text()/.color()/.is_visible()/.enabled()/
  .command_fn()`). Tasks build-once + edit; event-driven panels `clear()`+rebuild on each
  `draw()`. Never recreate widgets every frame — a rebuild straddling a click drops it.
- **ONE render loop** on the app (`MK7Tuner3D._render`) drives music/toast/notifications, the
  active stage's `render(dt)`, and the shared Simon/Discord panels — plus the achievement
  poll (`game.check_unlocks()` every ~250 ms). Stages expose `render(dt)`, not their own tasks.
- **Achievements are table-driven:** add a row to `constants.ACHIEVEMENTS`
  (`label, blurb, cred, [(stat_path, required)]`) + a stat for it to watch. Gameplay code
  only keeps STATS current — do **not** sprinkle `unlock()` calls around. (The two Wizard
  endings are the only manual unlocks, via `grant_god`.)
- **Save:** `Game.to_dict`/`from_dict` (bro + car build/mods/turbo + discord + counters/
  achievements), stamped `SAVE_VERSION`; mutates the existing Game **in place** (cached panel
  refs stay valid). The **rival ladder is NOT saved** (rebuilt from `RIVALS`). Saves +
  `options.cfg` live under `%APPDATA%\MK7 GTI Tuner\`, not `data/`.
- **Font:** the mono UI font (Consolas) lacks some glyphs — `★`(U+2605) / `✓` render as tofu;
  use `*` / ASCII. `◄ ▲ ▼` (U+25C4/25B2/25BC) render fine.
- **Offscreen test caveats:** `direct.interval` animations don't advance under rapid
  `taskMgr.step()` (dt ≈ 0) — call `interval.finish()` to jump to the end-state for a
  screenshot/assert. Real-time dyno pulls likewise can't be fast-forwarded — call
  `dyno.tick(0.6)` repeatedly. `LineSegs.getNumVertices()` is unreliable — test
  `not segs.isEmpty()`.
