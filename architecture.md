# Architecture

## Stage flow

```
mk7_gti_tuner.py -> configure_panda3d() -> MK7Tuner3D (ShowBase: shell + Game)
       |
  MenuStage (title) --New Game--> UnlockStage (cinematic) --on_complete--\
       ^  ^  |        --Load Game--------------------------------------> GarageStage (3D hub)
       |  |  Options (sound/graphics, options.cfg)                          | on_pick(key)   ^ on_back
       |  Save Game (savegame.json)                                         v                |
       Esc / MENU button <---- (pause menu, resumable) ----            <Task>.enter() -- <Task>.exit()
```

`MK7Tuner3D` (`library/game/app.py`) is a thin shell: it owns the window, lights,
glTF render setup, the mono font, the `Game` model, **one active stage**, and the
game-level overlays. `set_stage(stage)` calls `self.stage.exit()` then `stage.enter()`,
then `_sync_overlays(stage)` (point the music + shared panels at the new stage's key).
Every stage owns its own `aspect2d` sub-node (UI) and `render` sub-node (scene) and
removes them on `exit()` — so a task never renders over the hub (the old tab/back
overlap bug). There is no tab bar: the **GarageStage** hub (the GTI on a turntable)
launches one task at a time, and each task's **Back** button (bottom-left) returns to it.

### Render loop (one place)

A single task, `MK7Tuner3D._render`, drives every frame in a fixed order:

```
game.render():
  per-frame updates   -> music.update(dt), toast.render(dt), notifications.render(dt)
  current stage       -> self.stage.render(dt)         (task tick/redraw or hub spin)
  advisor panels      -> game.simon_panel.render(dt), game.discord_panel.render(dt)
```

So the **Ask-Simon / Ask-Discord panels are owned by the Game** (`game.simon_panel` /
`game.discord_panel`), not by the task — they're built once on first hub entry (by the
app, which has the Panda context), persist for the session, and get re-pointed at the new
context on each `set_stage`. (The Discord *model* is `game.discord`; the panel is
`game.discord_panel` — distinct.) Tasks no longer add their own per-frame task or their
own panels, and because the panels live on the game, a task can hide them via
**`game.set_advisors_visible(bool)`** (stash/unstash + close): the **race** hides both
pills the moment it stages and restores them when it concludes (in lock-step with
`allow_back`), so the cockpit isn't cluttered mid-run.

All game-level overlays (the panels, the toast, the notifications) draw in a dedicated
cull bin, **`OVERLAY_BIN`** (`"a2d-overlay"`), registered in `app._register_overlay_bin`
at sort 60 — above Panda's default bins (background/opaque/transparent/fixed/unsorted,
sorts 10-50). aspect2d's DirectGui stage UI lands in `fixed` (40), so the overlays would
otherwise be drawn *under* it; the higher bin keeps them on top regardless of draw
order. `OVERLAY_SORT` orders the overlays within that bin (panel < toast < notify).

That cull bin only controls what's *drawn* on top — **mouse picking** is separate. PGTop
assigns mouse-region priority by scene-graph traversal order, and the persistent panels
are created before each task, so the task's widgets would win clicks. `_sync_overlays`
therefore calls **`_lift_overlays`**, which reparents the overlays to the end of
`aspect2d` after each `set_stage`, putting their regions above the new stage's UI. The
**Discord window** adds a full-screen `state=NORMAL` modal shade behind itself (in
`_modal_shade`); lifted above the task, it swallows click-through (the window's own
button + entry are created after it, so they stay interactive).

### Menu + save/load

The app **boots into `MenuStage`** (the title screen) rather than straight into the
cinematic. **New Game** runs the same `UnlockStage` cinematic; **Load Game** restores a
`savegame.json` and jumps straight to the hub (no cinematic — the ECU state is already
flashed). At the hub, the **MENU** button or **Esc** opens the same stage as a *pause*
menu (`resumable=True`), which adds **Resume** + **Save Game**. `Esc` toggles it (open at
the hub, resume from the menu) and is inert during the cinematic / inside a task. Because
`MenuStage` is a normal stage that *replaces* the current one, there's no modal/​click
concern — but the persistent Ask pills don't belong on the menu, so after `_lift_overlays`
(which un-stashes via `reparentTo`) `_sync_overlays` calls
`game.set_advisors_visible(not isinstance(stage, MenuStage))` — the single switch that
hides them on the menu and shows them by default on any real stage (a task may then hide
them itself). Stash (not hide) is used so their mouse regions go too.

**New Game / Load Game mutate the single `Game` in place** (`Game.new_game()` /
`from_dict`) rather than constructing a new one, so the shared panels' cached `game`
reference stays valid. **Options** live in `options.cfg` (a `Config`): music + FX volume
now (applied live to `MusicPlayer.set_volume` / `GameAudio.set_fx_volume` and persisted on
change), graphics later. Both files live under the per-user app-data dir (`storage.py`),
not the bundled `data/`, so they're writable in a frozen build. NB: the player options are
`app.options`; `app.config` is ShowBase's own Panda config — don't shadow it.

## Layout

All code lives under `library/` (grouped subpackages); only the entry script is at
the root. Assets stay at the root in `data/`.

```
mk7_gti_tuner.py            entry point
library/
  core/      constants.py utils.py panda_config.py assets.py audio.py music.py
             config.py storage.py
  game/      app.py game.py tuner_bro.py rival_green_name.py car.py car_library.py
             discord.py discord_user.py discord_admin.py discord_green_name.py
             discord_normal_user.py geometry.py tuning.py simos.py
  stages/    hud.py task_base.py button.py button_controller.py garage_stage.py menu_stage.py
             simon_panel.py discord_panel.py toast.py notifications.py unlock_stage.py
             phone_screen.py character.py picker.py progress_bar.py
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
- `assets.py` — `load_model(type, key)` (loads a `.glb` via panda3d-gltf with
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
  `set_fx_volume(v)` sets the master SFX gain via the `AudioManager` (options menu).
- `music.py` — `MusicPlayer`: per-stage background music. `set_track(key)` plays a
  random song from `data/music/<key>/` (resolved by `assets.music_paths`); on the
  finished event it auto-plays another random one. Each start raises a "now playing"
  toast. `set_volume(v)` (driven by the options menu) levels the current + future songs.
  Owned by the app and re-pointed in `_sync_overlays`.
- `storage.py` — writable per-user paths + JSON I/O: `app_data_dir()` (`%APPDATA%/<APP_NAME>`,
  created on demand — writable even in a frozen build, unlike bundled `data/`),
  `config_path()`/`save_path()`/`has_save()`, and tolerant `read_json`/`write_json`
  (atomic temp-file replace; never raises).
- `config.py` — `Config`: the player's options, persisted to `options.cfg`
  (`load()`/`save()`/`to_dict`/`from_dict`). Holds `music_volume`, `fx_volume`, and a
  forward-compat `graphics` bag. `apply(app)` pushes the volumes into the music player +
  audio. Lives on the app as **`app.options`** (not `app.config`, which is Panda's).

### `library/stages` — navigation + shared widgets
- `hud.py` — `Hud(DirectObject)`: a tracked node tree under `aspect2d` plus the draw
  helpers (`label`/`frame`/`button`/`slider`/`image`/`pill`), the shared
  `draw_header(game)`, and `back_button(cmd)`. **Boxes are translucent + rounded:**
  `frame`/`button` tint the `ui_box` texture for the fill and `ui_ring` for the border
  (via `_glass`); the `slider` thumb is the round `knob` texture. `set_visible(bool)`
  stash/unstashes the whole tree (regions included); `destroy()` removes it. Base for
  every screen.
- `button.py` — `Button`: one managed task button — a rounded glass `DirectButton`
  (`ui_box` fill + `ui_ring` border) that **flashes a "clicked" colour** for
  `BUTTON_CLICK_HOLD`s on press then reverts (auto-brightens the normal colour if no
  clicked colour is given). Built once, then tweaked via getter/setter methods —
  `text()` / `color()` / `enabled()` / `is_visible()` / `command_fn()` (no arg = read,
  one arg = set). **`is_visible`** defaults True; `render(dt)` enforces it (a not-visible
  button is *stashed* — off-screen and unclickable) and advances the flash. Never
  destroyed by a redraw.
- `button_controller.py` — `ButtonController`: owns one task's buttons (created on enter,
  destroyed on exit). Buttons are **built once** via `add(key, …)` and then changed in
  place — `get(key).text(…)` / `.is_visible(…)` / … or `edit(key, **props)` — rather than
  recreated. `render(dt)` ticks every button's visibility + flash; `lift()` keeps the
  buttons drawn above the frames/labels a redraw just rebuilt.
- `task_base.py` — `TaskBase(Hud)`: one full-screen task. Owns a 3D `scene` node;
  `enter()` sets the camera, builds the scene, **builds the buttons once
  (`build_buttons()`)**, draws the UI, and binds keys; the app's render loop calls
  `render(dt)` (which runs `tick(dt)` + flame/reaction updates + the button controller's
  visibility/flash tick + a `dirty`/live redraw). **Buttons are built once and only
  edited afterwards** (each task creates them in `build_buttons` and changes their
  text/colour/enabled/visibility from `build_ui`); they live on their own layer, persist
  across redraws (so a click can't be dropped by the UI rebuilding mid-press), and are
  freed on exit. A redraw still `clear()`s/rebuilds the labels/frames (and the Back pill +
  sliders), so `render` also **defers the redraw while the mouse button is held**
  (`_mouse_held`) to protect those remaining recreated widgets. `exit()` destroys the
  controller, then tears
  the rest down. The Simon/Discord panels are **not** owned here
  — they live on the app. Subclasses set `title`/`key`/`live` (and `music_key`, which
  defaults to `key` but is the themed folder name for TUNE→`tuning`/SKREETS→`skreetz`)
  and override `build_scene`/`build_ui`/`bind_keys`/`tick`. Provides
  `add_garage_scene()`, `panel_pair()`, `bind()`, exhaust `spawn_flames`, and
  `prepare_wheels(car)`. `prepare_wheels` makes the detailed car `.glb` wheels spin in
  place: the wheel meshes (under `WHEEL_PREFIX` = `w:` nodes) pivot at the *model* origin,
  so spinning them directly flings them across the scene. It gathers the spinnable wheel
  **geom leaves** (brake calipers — `WHEEL_STATIC` — dropped; the caliper label can be on
  a leaf *or* a named ancestor, so `_wheel_static` checks the whole chain), **clusters
  them into the four corners by car-space position**, and wraps each corner in a pivot at
  the wheel's centre (reparenting preserves world position), returning the four pivots to
  rotate about the axle (X). Position clustering is model-agnostic: it handles both
  `mk7_gti.glb` (flat per-corner `w:` siblings) **and** `civic_type_r.glb` (all four wheels
  lumped in one `w:wheels` group — which the old per-node version pivoted at the car centre,
  the "wheels fly off" bug). Falls back to the old procedural `tire_`/`rim_` nodes if a
  model has no `w:` geometry.
- `garage_stage.py` — `GarageStage(Hud)`: the home hub — ground + glb GTI on a slow
  turntable, header, a **MENU** button (`on_menu`), a row of task buttons from `MODES`,
  and Simon. `on_pick(key)`.
- `menu_stage.py` — `MenuStage(Hud)`: the title + pause menu. One stage walking three
  pages (root / options / graphics) on a centred glass card. Root rows come from
  `MENU_ITEMS` filtered by `resumable` (Resume/Save only mid-career; Load auto-disabled
  with no save). The app passes the actions (`new`/`load`/`save`/`resume`/`quit`); the
  options page hosts the music + FX volume sliders (apply live + persist to `options.cfg`).
- `simon_panel.py` — `SimonPanel(Hud)`: the reusable Ask-Simon pill + roast/tip popup
  (own node tree, toggles independently of the host screen), fed by `simos`.
- `discord_panel.py` — `DiscordPanel(Hud)`: the **Ask-Discord chat window**. A pill
  opens a Discord-style window (server rail, channel list, `#ecu-tuning` message area
  with a `DirectEntry`, and the online/offline member list sampled from the roster).
  Typing + Enter calls `game.ask_discord(text)` and appends the replies + the result
  line. Own node tree; companion to `SimonPanel`.
- `notifications.py` — `Notifications`: a session-long top-screen overlay (achievement
  toasts + Dyno Dave bubbles) drained from `game.toast_queue` / `game.dave_queue`.
  `render(dt)` is called by the app loop (no task of its own).
- `toast.py` — `Toast(Hud)`: a single game-level bottom-centre prompt. `show(title,
  message, seconds)` flashes it (used by `MusicPlayer` for "now playing"); `render(dt)`
  holds it then fades it out.

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
  wallpaper, app icon, completion check, logo, the Simon face/panel/pill, the emoji
  HUD icons (cred / Karen faces, pops burst, fire, cash), and the UI chrome — `ui_box`
  (solid rounded rect), `ui_ring` (rounded outline), `knob` (round slider thumb), and
  `avatar` (default round Discord avatar, tinted per user). The chrome PNGs are white
  so they tint via `frameColor` / `setColorScale` at runtime.
- `asset_audio.py` — WAV synthesis with the standard library (no numpy): a seamless
  harmonic engine loop (+ tanh grit), an intake-noise loop, a turbo whistle, and short
  pop / bang / blow-off one-shots. Deterministic (seeded); writes `data/audio/*.wav`.
- `generate_assets.py` — orchestrator that writes everything into `data/`
  (run via `python -m library.assetgen.generate_assets`).

### `library/game` — model tree + math
A save-ready object tree: each node has `to_dict`/`from_dict`, and `Game.to_dict` rolls
them into a single career snapshot written to `savegame.json` (see `storage.py`). Display
reads go straight to `game.bro`/`game.car`; cross-node actions are orchestrated on `Game`.
- `game.py` — `Game`: root/session. Holds `bro: TunerBro`, `rivals: [RivalGreenName]`,
  `cars: CarLibrary`, `discord: Discord` (model), transient `logs`, a `car` property, and
  the orchestration that spans nodes (`buy_mod`, `register_pops`, `ask_discord`, log). It
  also owns the **advisor panels** `simon_panel`/`discord_panel` (the app builds them on
  first hub entry and assigns them here; not reset by `new_game`) plus
  `set_advisors_visible(bool)` so a task can show/hide the Ask pills. `new_game()` resets
  a fresh career **in place** (so cached references survive); `to_dict`/`from_dict` cover
  the bro, car library (build + mods), discord presence, and the career
  counters/achievements (stamped with `SAVE_VERSION`), restoring in place. The **rival
  ladder is intentionally not saved** — it's static reference data from `RIVALS`, always
  rebuilt by `new_game`; only progress (`bro.unlocked_rival`/`selected_rival`) persists.
  (`SAVE_VERSION 1` saved the ladder and froze stale specs into old saves — e.g. a rival's
  `model` — so a constant edit didn't take effect on load; v2 drops it.)
- `tuner_bro.py` — `TunerBro`: the user — cash, cred, Karen/heat, rep, ladder progress,
  `unlocked_maps` (`spend`/`earn`/`pay_repair`/`add_cred`/`add_heat`/`unlock_map`). Room
  for emotional damage / route / skills.
- `rival_green_name.py` — `RivalGreenName`: a bad-guy ladder rival (from `RIVALS`).
- `car.py` — `Car`: ECU state, tune/slots/mods, last dyno; state-change methods return
  `(message, kind)` so `Game` logs them. `apply_preset` accepts `PRESETS` **and**
  `COMMUNITY_MAPS` keys. `car_perf`/`compute` feed the dyno + race.
- `car_library.py` — `CarLibrary`: the bro's car(s) + active index (`active()`).
- `discord.py` — `Discord`: the *MQB Vibe Coders* server. Builds the roster from
  `DISCORD_ROSTER` (each row → an `Admin`/`GreenName`/`NormalUser`), samples who's
  online (`refresh_online`), supplies channel `backlog` chatter, and `resolve(text, ctx)`
  → an outcome (request quality + who's online + a dice roll decide good vs bad).
- `discord_user.py` — `DiscordUser` base (identity, online roll, chatter, persona
  `lean`); `discord_admin.py`/`discord_green_name.py`/`discord_normal_user.py` are the
  role subclasses (Admin trusts good, GreenName pulls money, NormalUser is persona-only).
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
- **Rounded glass chrome:** all boxes/buttons go through `Hud._glass` (the `ui_box` /
  `ui_ring` textures tinted by `frameColor`); panel fills are translucent so the 3D
  scene shows through. No square `DGG.RIDGE` frames.
- **Street throttle:** **hold** Space (`space` / `space-up`) to peg the throttle; on
  release the revs decay and the overrun crackle fires (the throttle button is a blip).
- **Discord outcomes:** `Discord.resolve` is table-driven (`DISCORD_GOOD`/`DISCORD_BAD`
  pools, `PERSONA_LEAN`, keyword lists); `Game.ask_discord` applies the effect to the
  bro/car (cash / cred / `unlock_map` / repair) and logs it — no `if/elif` staircase.

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
2. `python mk7_gti_tuner.py` — title menu → New Game → unlock cinematic → garage hub →
   open each task → Back → open another (no overlay left behind); throttle/pops on
   STREET, a dyno pull, a race all run. At the hub, MENU/Esc opens the pause menu: Save
   Game, then New Game/Load Game round-trips the career; Options sliders change music/FX
   volume live and survive a relaunch (`options.cfg`). For quick visual checks render in a
   `window-type offscreen` ShowBase and `saveScreenshot` (drive `taskMgr.step()`).
3. `build.bat` then run `dist/MK7-GTI-Tuner.exe` — confirm the packaged build loads
   its assets (the bundled `data/`).
