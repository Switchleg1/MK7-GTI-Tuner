# Architecture

## Stage flow

```
mk7_gti_tuner.py -> configure_panda3d() -> MK7Tuner3D (ShowBase: shell + GameState)
       |
  UnlockStage (cinematic) --on_complete--> GarageStage (3D hub)
                                              | on_pick(key)        ^ on_back
                                              v                     |
                                           <Task>.enter()  ----  <Task>.exit()
```

`MK7Tuner3D` (`library/game/app.py`) is a thin shell: it owns the window, lights,
glTF render setup, the mono font, the `GameState` model, and **one active stage**.
`set_stage(stage)` calls `self.stage.exit()` then `stage.enter()`. Every stage owns
its own `aspect2d` sub-node (UI) and `render` sub-node (scene) and removes them on
`exit()` — so a task never renders over the hub (the old tab/back overlap bug). There
is no tab bar: the **GarageStage** hub (the GTI on a turntable) launches one task at
a time, and each task's **Back** button (bottom-left, Simon-pill style) returns to it.

## Layout

All code lives under `library/` (grouped subpackages); only the entry script is at
the root. Assets stay at the root in `data/`.

```
mk7_gti_tuner.py            entry point
library/
  core/      constants.py utils.py panda_config.py assets.py audio.py
  game/      app.py game.py tuner_bro.py rival_green_name.py car.py car_library.py
             geometry.py tuning.py simos.py
  stages/    hud.py task_base.py garage_stage.py simon_panel.py
             unlock_stage.py phone_screen.py character.py picker.py progress_bar.py
    tasks/   bench_task.py maps_task.py dyno_task.py street_task.py race_task.py shop_task.py
  assetgen/  glb_builder.py asset_*.py generate_assets.py   (offline; not shipped)
data/        models/*.glb  images/*.png  audio/*.wav
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
- `audio.py` — `GameAudio`: the runtime sound service on the shell. A looping engine
  note (+ intake roar + turbo whistle) pitched by RPM via `setPlayRate` and leveled by
  throttle load, plus pooled pop/bang/blow-off one-shots so overrun bursts overlap.
  No-ops if Panda has no audio backend; tasks drive it via `app.audio` and it is
  silenced on `TaskBase.exit()`. Sounds resolve via `assets.sound_path(key)`.

### `library/stages` — navigation + shared widgets
- `hud.py` — `Hud(DirectObject)`: a tracked node tree under `aspect2d` plus the draw
  helpers (`label`/`frame`/`button`/`image`/`pill`), the shared `draw_header(game)`,
  and `back_button(cmd)`. `destroy()` removes the whole tree. Base for screens.
- `task_base.py` — `TaskBase(Hud)`: one full-screen task. Owns a 3D `scene` node + a
  `SimonPanel`; `enter()` sets the camera, builds scene/UI, binds keys, and runs a
  per-frame `_update` (calls `tick(dt)` + flame update + a `dirty`/live redraw);
  `exit()` tears it all down. Subclasses set `title`/`key`/`live` and override
  `build_scene`/`build_ui`/`bind_keys`/`tick`. Provides `add_garage_scene()`,
  `panel_pair()`, `bind()` (run action + mark dirty), and exhaust `spawn_flames`.
- `garage_stage.py` — `GarageStage(Hud)`: the home hub — ground + glb GTI on a slow
  turntable, header, a row of task buttons from `MODES`, and Simon. `on_pick(key)`.
- `simon_panel.py` — `SimonPanel(Hud)`: the reusable Ask-Simon pill + roast/tip popup
  (own node tree, toggles independently of the host screen), fed by `simos`.

### `library/stages` — cinematic unlock + its pieces
- `unlock_stage.py` — `UnlockStage`: plug → phone → flash → done via `direct.interval`
  (self-managed cleanup; calls `on_complete` to reach the hub).
- `character.py`, `phone_screen.py`, `picker.py`, `progress_bar.py` — posable rig,
  SimonTools phone overlay, camera-ray picking, and the fill bar (also used by tasks).

### `library/assetgen` — asset pipeline (offline, not bundled in the exe)
- `glb_builder.py` — `GlbScene`: a tiny procedural glTF writer over `pygltflib`
  (boxes, cylinders, a named node hierarchy with translation + HPR rotation +
  per-color PBR materials). Authoring is Panda Z-up; HPR→quaternion via Panda's
  `LQuaternion`, valid because models load with `skip_axis_conversion=True`.
- `asset_ground.py`, `asset_car.py`, `asset_character.py`, `asset_phone.py`,
  `asset_obd.py` — each a `build(out_dir)` **function** that composes one `.glb`.
  Data-driven (parts tables / side loops), no class.
- `asset_images.py` — PNG generation via Panda's `PNMImage` (no PIL): phone
  wallpaper, app icon, completion check, logo, the Simon face/panel/pill, and the
  emoji HUD icons (cred / Karen faces, pops burst, fire, cash).
- `asset_audio.py` — WAV synthesis with the standard library (no numpy): a seamless
  harmonic engine loop (+ tanh grit), an intake-noise loop, a turbo whistle, and short
  pop / bang / blow-off one-shots. Deterministic (seeded); writes `data/audio/*.wav`.
- `generate_assets.py` — orchestrator that writes everything into `data/`
  (run via `python -m library.assetgen.generate_assets`).

### `library/game` — model tree + math
A save-ready object tree (each node has `to_dict`/`from_dict`; serialization itself is
a later step). Display reads go straight to `game.bro`/`game.car`; cross-node actions
are orchestrated on `Game`.
- `game.py` — `Game`: root/session. Holds `bro: TunerBro`, `rivals: [RivalGreenName]`,
  `cars: CarLibrary`, transient `logs`/`race`, a `car` property, and the orchestration
  that spans nodes (`buy_mod`, `register_pops`, the quarter-mile race, log).
- `tuner_bro.py` — `TunerBro`: the user — cash, cred, Karen/heat, rep, ladder progress
  (`spend`/`earn`/`add_cred`/`add_heat`). Room for emotional damage / route / skills.
- `rival_green_name.py` — `RivalGreenName`: a bad-guy ladder rival (from `RIVALS`).
- `car.py` — `Car`: ECU state, tune/slots/mods, last dyno; state-change methods return
  `(message, kind)` so `Game` logs them. `car_perf`/`compute` feed the dyno + race.
- `car_library.py` — `CarLibrary`: the bro's car(s) + active index (`active()`).
- `app.py` — `MK7Tuner3D`: the ShowBase shell + stage manager + `TASK_CLASSES`.
- `geometry.py` — box/grid builders (the exhaust-flame cubes).
- `tuning.py` — tune math: `compute_tune`, `dyno_curve`, grading, pops, rep.
- `simos.py` — "Ask Simon" rules engine; `build_context(game, tab)` reads bro + car.

The **DynoTask** (`library/stages/tasks/dyno_task.py`) is SimosTools-style: a pull
sweeps RPM idle→redline (`tick`), driving gauge **tiles** (scale, big value, `min:max`,
unit, green fill + red danger band, from `constants.DYNO_GAUGES`) and a live power-vs-RPM
`LineSegs` graph, then records the peak + `grade_for_result` on the `Car`.

## Key conventions

- **Coordinates:** the car sits at the origin facing **+Y**; the driver side is **−X**
  (LHD), so the OBD2 port is under the dash on the −X side. The seated guy faces −X
  out the open door. Z is up.
- **Sequencing/animation:** `direct.interval` `Sequence`/`Parallel`/`LerpFunc`/
  `LerpHprInterval` drive every delay, progress fill, and pose, so timings come
  straight from the tables in `constants.py`.
- **Picking:** 3D hotspots are tagged (`setTag("pick", …)`) and resolved by a camera
  ray; 2D buttons (task buttons, Back, FLASH, Continue) use DirectGui commands.
- **Cleanup:** `set_stage` exits the current stage before entering the next; each
  stage removes its UI + scene roots, its per-frame task, its SimonPanel/intervals,
  and `ignoreAll()`s — so nothing leaks or renders over the next stage.
- **Mono UI:** `Hud` draws with `app.mono_font` (Consolas on Windows, else default).

## Packaging (PyInstaller)

`build.bat` builds a one-file windowed exe with `--add-data "data;data"` so the
generated models/images/audio ship inside the bundle, and `--collect-all panda3d`
pulls in the OpenAL audio plugin so sound works in the frozen build.
At runtime `assets.data_root()` returns `sys._MEIPASS` when frozen (where the
bundled `data/` is extracted) and the project root otherwise — so the same code
path works from source and from the exe. The committed `.spec` mirrors this
(`datas=[('data','data')]`), though `build.bat` drives the build via flags.

## Verifying changes

1. `python -m library.assetgen.generate_assets` — rebuild assets (offline, no window).
2. `python mk7_gti_tuner.py` — unlock cinematic → garage hub → open each task → Back
   → open another (no overlay left behind); throttle/pops on STREET, a dyno pull, a
   race all run. For quick visual checks render in a `window-type offscreen` ShowBase
   and `saveScreenshot` (drive a task's `_update` with `taskMgr.step()`).
3. `build.bat` then run `dist/MK7-GTI-Tuner.exe` — confirm the packaged build loads
   its assets (the bundled `data/`).
