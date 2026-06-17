# Architecture

## Stage flow

```
mk7_gti_tuner.py  ->  configure_panda3d()  ->  MK7Tuner3D (ShowBase)
                                                   |
   boot  ->  UnlockStage (cinematic)  ->  ModeSelectStage  ->  Garage (tabbed game)
                on_complete=start_mode_select   on_pick=enter_garage
```

`MK7Tuner3D` (`library/game/app.py`) is the single root app. It owns the ShowBase, lights, the
glTF render setup, and the existing tabbed "garage" game. On boot it does **not**
build the garage — it launches `UnlockStage`. Each stage is a standalone object
that takes the ShowBase plus a callback, draws into its own `render`/`aspect2d`
sub-nodes, and fully cleans up (nodes, tasks, events, intervals) when it exits.

> Trade-off: `MK7Tuner3D` is both the shell and the garage stage (the garage build
> is just deferred to `enter_garage`). This avoids rewriting the working 600-line
> garage. A future refactor could split a thin `GameShell(ShowBase)` from a plain
> `GarageStage`.

## Layout

All code lives under `library/` (grouped subpackages); only the entry script is at
the root. Assets stay at the root in `data/`.

```
mk7_gti_tuner.py            entry point
library/
  core/      constants.py utils.py panda_config.py assets.py
  game/      app.py geometry.py tuning.py simos.py
  stages/    unlock_stage.py mode_select_stage.py phone_screen.py
             character.py picker.py progress_bar.py
  assetgen/  glb_builder.py asset_*.py generate_assets.py   (offline; not shipped)
data/        models/*.glb  images/*.png
```

Modules import each other by absolute path (`from library.<sub>.<mod> import …`).

## Modules

### Entry + `library/core`
- `mk7_gti_tuner.py` — entry point: configure Panda, run `MK7Tuner3D`.
- `panda_config.py` — `configure_panda3d()` (window/MSAA prc) and `enable_gltf(base)`
  (auto-shader + multisample; no simplepbr, for robust startup).
- `assets.py` — `load_model(key)` (loads a `.glb` via panda3d-gltf with
  `skip_axis_conversion=True`), `image_path(key)`, and `data_root()` (frozen-aware:
  `sys._MEIPASS` when packaged, project root from source).
- `constants.py` — **all** defaults, thresholds, colors, asset paths, the cinematic
  camera/placements, phase prompts, flash-step / ECU-readout / character-pose tables,
  and the mode list. The single source of tunable values.
- `utils.py` — `clamp`, `pick`, `rgba`.

### `library/stages` — cinematic unlock (the new work)
- `unlock_stage.py` — `UnlockStage`: builds the scene (ground/car/character/phone/obd),
  sets the driver-side camera, and runs a phase machine
  **plug → phone → flash → done** using `direct.interval` sequences for delays,
  progress, and posing. The FLASH portion (PhoneScreen + ProgressBar + `UNLOCK_FLASH_STEPS`)
  is self-contained so the BENCH tab can later reuse it to flash staged maps.
- `character.py` — `Character`: resolves the posable joints of `character.glb` and
  returns `pose_interval(name, t)` lerps from `constants.CHARACTER_POSES`
  (rest / reach / hold_phone / cheer); reparents the phone prop to the right hand.
- `phone_screen.py` — `PhoneScreen`: the SimosTools 2D overlay (status bar, app
  header, streaming ECU log, FLASH button, progress, completion check).
- `picker.py` — `Picker`: camera-ray click picking of tagged 3D nodes (the OBD port
  and the phone prop). Reusable.
- `progress_bar.py` — `ProgressBar`: left-anchored fill bar (phone + link progress).
- `mode_select_stage.py` — `ModeSelectStage`: full-screen mode menu built from `MODES`.

### `library/assetgen` — asset pipeline (offline, not bundled in the exe)
- `glb_builder.py` — `GlbScene`: a tiny procedural glTF writer over `pygltflib`
  (boxes, cylinders, a named node hierarchy with translation + HPR rotation +
  per-color PBR materials). Authoring is Panda Z-up; HPR→quaternion via Panda's
  `LQuaternion`, valid because models load with `skip_axis_conversion=True`.
- `asset_ground.py`, `asset_car.py`, `asset_character.py`, `asset_phone.py`,
  `asset_obd.py` — each a `build(out_dir)` **function** that composes one `.glb`.
  Data-driven (parts tables / side loops), no class.
- `asset_images.py` — PNG generation via Panda's `PNMImage` (no PIL): phone
  wallpaper, app icon, completion check, logo.
- `generate_assets.py` — orchestrator that writes everything into `data/`
  (run via `python -m library.assetgen.generate_assets`).

### `library/game` — existing garage game (unchanged logic)
- `geometry.py` — box/grid/simple-car builders for the garage scene.
- `tuning.py` — tune math: `compute_tune`, `dyno_curve`, grading, pops, rep.
- `simos.py` — "Ask Simon" roast/tip rules engine (table of rules).

## Key conventions

- **Coordinates:** the car sits at the origin facing **+Y**; the driver side is **−X**
  (LHD), so the OBD2 port is under the dash on the −X side. The seated guy faces −X
  out the open door. Z is up.
- **Sequencing/animation:** `direct.interval` `Sequence`/`Parallel`/`LerpFunc`/
  `LerpHprInterval` drive every delay, progress fill, and pose, so timings come
  straight from the tables in `constants.py`.
- **Picking:** 3D hotspots are tagged (`setTag("pick", …)`) and resolved by a camera
  ray; 2D buttons (FLASH, Continue, mode cards, tabs) use DirectGui commands.
- **Cleanup:** each stage removes its scene/UI roots, stops intervals, and destroys
  its `Picker`/`PhoneScreen` on exit, so stages don't leak into one another.

## Packaging (PyInstaller)

`build.bat` builds a one-file windowed exe with
`--add-data "data;data"` so the generated models/images ship inside the bundle.
At runtime `assets.data_root()` returns `sys._MEIPASS` when frozen (where the
bundled `data/` is extracted) and the project root otherwise — so the same code
path works from source and from the exe. The committed `.spec` mirrors this
(`datas=[('data','data')]`), though `build.bat` drives the build via flags.

## Verifying changes

1. `python -m library.assetgen.generate_assets` — rebuild assets (offline, no window).
2. `python mk7_gti_tuner.py` — play: OBD2 → phone → FLASH → Continue → pick a mode
   → garage. For quick visual checks you can render the scene to a PNG in an
   `window-type offscreen` ShowBase and `saveScreenshot` after a few `renderFrame`s.
3. `build.bat` then run `dist/MK7-GTI-Tuner.exe` — confirm the packaged build loads
   its assets (the bundled `data/`).
