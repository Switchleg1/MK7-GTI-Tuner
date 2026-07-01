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
  chrome objects      -> game.ui.render(dt)        (Ask Simon / Ask Discord / Back)
```

So the **Ask-Simon / Ask-Discord panels are owned by the Game** (`game.simon_panel` /
`game.discord_panel`), not by the task — they're built once on first hub entry (by the
app, which has the Panda context), persist for the session, and get re-pointed at the new
context on each `set_stage`. (The Discord *model* is `game.discord`; the panel is
`game.discord_panel` — distinct.) Each panel now owns **only its popup/window**; the
**Ask Simon / Ask Discord / Back triggers are `Button`s in the game-level `UIObjectController`,
`game.ui`** (also built on first hub entry, on its own OVERLAY_BIN layer). The Ask
buttons call `panel.ask()`; the **Back** button is shared across tasks — `TaskBase` points
it at the active task's `on_back` and shows it only in a task (hidden at the hub/menu).
A task hides the Ask buttons via **`game.set_advisors_visible(bool)`** (toggles their
`is_visible` + closes the panels): the **race** hides both the moment it stages and
restores them when it concludes (in lock-step with `allow_back`, which also drives Back).

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
             discord_normal_user.py geometry.py tuning.py simos.py scoreboard.py
  stages/    hud.py task_base.py garage_stage.py menu_stage.py simon_panel.py discord_panel.py
             wizard_choice_stage.py wizard_trial_stage.py dongle_stage.py
             shop_item.py review_overlay.py
             unlock_stage.py toast.py notifications.py phone_screen.py
             character.py picker.py progress_bar.py
             base_object.py text.py button.py frame.py image.py slider.py entry.py ui_object_controller.py
    tasks/   bench_task.py maps_task.py dyno_task.py street_task.py race_task.py shop_task.py
             scoreboard_task.py
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
  and the mode list. The single source of tunable values. Includes **`CAR_TABLE`** (each
  car's real-world spec: stock rpm→whp `power_curve`, gears, final drive, tire circ, mass,
  grip, redline, spool, `max_boost` (the stock boost-slider ceiling), boost ceiling —
  keyed by `car_id`) and **`PARTS`** — the SINGLE catalog of everything buyable. `TRACK_M`
  is the only global gearing value left (per-car gearing moved into `CAR_TABLE`). Each
  `PARTS` row holds BOTH its shop copy (`name`/`price`/`blurb`/`review`/`accent`) AND its
  curve effect (`spool`/`weight`/`grip`/`max_boost`/compounding rpm `curve` adders). `kind`
  splits behaviour: `"mod"` bolt-ons are cumulative bools on `Car.mods`; `"turbo"` rows are
  the mutually-exclusive turbo family (is38/cts_jb600/vortex/arashi_3076, `category="turbo"`)
  that additionally carry `compute_tune` caps (`boost_limit`/`blown_boost` — lower = grenades
  sooner AND a lower boost-slider ceiling), a `dave_on_blow` Dave-pool key, and `ed_cut`
  flavour. Derived views (single source of truth is `PARTS`): `MOD_IDS`/`TURBO_IDS` (by
  kind), `TURBO_DEFAULT` (baseline IS38 for rivals/old saves), `MOD_KEYS` (the bool ids on
  `Car.mods` = bolt-ons + the `"turbo"` anchor), `BASE_EFFECTS` (the curve-effect lookup).
  (`mods["turbo"]` stays a bool anchor; `Car.turbo` picks the variant — see car.py.)
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
- `base_object.py` — `BaseObject`: base for a managed UI object — wraps one DirectGui
  NodePath with shared **`is_visible`** / **`enabled`** / `pos()` getter/setters.
  `render(dt)` enforces visibility by stash/unstash (a hidden object is off-screen AND
  unclickable). Built once, tweaked over its life, never destroyed by a redraw. **Every
  `Hud` primitive has a `BaseObject`-derived equivalent:** `Text`, `Button`, `Frame`,
  `Image`, `Slider`, `Entry`.
- `text.py` — `Text(BaseObject)`: a managed `DirectLabel`. `text()` / `color()` /
  `is_visible()` / `enabled()` change it in place (instead of destroy+recreate each
  redraw). `enabled(False)` dims to an optional `disabled_color`.
- `button.py` — `Button(BaseObject)`: a managed button in three **styles**
  (`constants.BUTTON_STYLES`): **box** (rounded glass — `ui_box` fill tinted by the colour
  + `ui_ring` border, white text, flashes the *clicked colour*), **pill** (textured
  `simon_button`, the colour tints the *text*, optional left `icon`, flashes by
  colour-scale brighten), and **garage** (box + a green top **accent** strip, for the hub
  task cards). Flash holds `BUTTON_CLICK_HOLD`s then reverts. Extra setters: `text()` /
  `color()` / `command_fn()` (visibility/enabled/pos come from `BaseObject`). (Task
  buttons = `box`; game-level Ask/Back chrome = `pill`; hub task cards = `garage`.)
- `frame.py` — `Frame(BaseObject)`: a managed rectangle — by default a translucent rounded
  `ui_box` tinted by `color` with an optional `ui_ring` border child (the glass look);
  `texture=None` gives a plain flat frame and `state=DGG.NORMAL` makes it catch clicks (the
  Discord modal shade). Setters: `color()` / `frame_size()`.
- `image.py` — `Image(BaseObject)`: a managed `OnscreenImage` keyed by an asset name.
  Setters: `color_scale()` / `scale()` (used for the Discord avatars, Simon art, logos).
- `slider.py` — `Slider(BaseObject)`: a managed `DirectSlider` (round `knob` thumb on a
  rounded track). `value()` reads/sets the value; `command_fn()` wires the callback after
  build so it doesn't fire on init (the options-menu volume sliders).
- `entry.py` — `Entry(BaseObject)`: a managed single-line `DirectEntry`; `command` fires
  with the typed text on Enter. `text()` reads/clears, `focus()` re-grabs the caret (the
  Discord help-request box).
- `ui_object_controller.py` — `UIObjectController`: owns a set of managed UI objects — every
  `Hud` primitive has an `add_*` here: `add_text` / `add_button` / `add_frame` / `add_image`
  / `add_slider` / `add_entry`. Objects are changed in place (`get(key).text(…)` /
  `.is_visible(…)` / …). **Persistent screens** (tasks) build them once on enter and only
  tweak them; **event-driven screens** (the panels, the hub) instead `clear()` and re-add on
  each `draw()` (they redraw only on a user action, never on a per-frame timer, so a rebuild
  can't drop a click). `render(dt)` ticks every object (visibility + any flash); `lift()`
  keeps them drawn above the frames a redraw just rebuilt; `destroy()` frees them.
- `task_base.py` — `TaskBase(Hud)`: one full-screen task. Owns a 3D `scene` node and a
  `UIObjectController` (`self.ui`); `enter()` sets the camera, builds the scene, **builds
  the UI objects once (`build_objects()`)**, draws, and binds keys; the app's render loop
  calls `render(dt)` (which runs `tick(dt)` + flame/reaction updates + the controller's
  visibility/flash tick + a `dirty`/live redraw). **Text and buttons are built once and
  only edited afterwards** (each task creates them in `build_objects` and changes their
  text/colour/enabled/visibility from `build_ui`); they live on their own layer, persist
  across redraws (no destroy/recreate per render — clicks aren't dropped, labels don't
  churn), and are freed on exit. The `redraw` still `clear()`s/rebuilds the transient
  header + frames/images (panel backgrounds, the karen bar, the dyno gauge fills, the race
  tach), so `render` **defers the redraw while the mouse is held** (`_mouse_held`) to
  protect the few remaining recreated widgets (the maps sliders). `exit()` destroys the
  controller, then tears the rest down. The Simon/Discord panels are **not** owned here
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
  turntable, header, a **MENU** button (`on_menu`), a **HIGH SCORES** button (`on_scores`
  → opens the scoreboard task), and a row of task cards from `MODES`.
  Its buttons go through its own `UIObjectController` (`self.ui`): the task cards use
  the **garage** style (green accent), MENU + the wizard DM use `box`. `on_pick(key)`.
  All four of these screens express their UI as **managed objects on `self.ui`** (a
  `UIObjectController`), rebuilt on each `draw()` (event-driven, not per-frame) — they use
  no raw `Hud` primitives. Each overrides `render(dt)` to tick its controller (visibility +
  the button click-flash).
- `menu_stage.py` — `MenuStage(Hud)`: the title + pause menu. One stage walking three
  pages (root / options / graphics) on a centred glass card. Root rows come from
  `MENU_ITEMS` filtered by `resumable` (Resume/Save only mid-career; Load auto-disabled
  with no save). The app passes the actions (`new`/`load`/`save`/`resume`/`quit`); the
  options page hosts the music + FX volume `Slider`s (apply live + persist to `options.cfg`).
- `simon_panel.py` — `SimonPanel(Hud)`: the Ask-Simon roast/tip popup (own node tree,
  toggles independently of the host screen), fed by `simos`. The trigger is the
  game-level `ask_simon` button (`game.ui`), which calls `SimonPanel.ask()`.
- `discord_panel.py` — `DiscordPanel(Hud)`: the **Ask-Discord chat window** (server rail,
  channel list, `#ecu-tuning` message area with a managed `Entry`, online/offline member
  list, and a click-eating modal `Frame` shade). Opened by the game-level `ask_discord`
  button (`game.ui.get("ask_discord")` → `DiscordPanel.ask()`).
  Typing + Enter calls `game.ask_discord(text)` and appends the replies + the result
  line. Own node tree; companion to `SimonPanel`.
- `wizard_choice_stage.py` — `WizardChoiceStage(Hud)`: a 2D modal shown when the Wizard's
  DM is answered (`app.open_wizard`). Two cards — **Bench an ECU** (`on_bench` →
  `WizardTrialStage`) and **Make Dongles** (`on_dongle` → `DongleStage`). Both paths grant
  the same reward; only the trophy differs (see `grant_god`).
- `wizard_trial_stage.py` — `WizardTrialStage(Hud)`: the Bench Wizard's three-part Trial
  (power the rig → probe a 3D pogo board → hit the sync window) → `Game.grant_god()` (default
  `TRIAL_ACHIEVEMENT` → "Passed the Trial"). Its 2D overlay is managed objects on `self.ui`
  (the animated sync marker is a persistent `Frame` moved in `render`); the 3D board lives
  under its own `scene` node.
- `dongle_stage.py` — `DongleStage(Hud)`: the *other* Wizard challenge — **Make Dongles**, a
  3D drag-and-drop game. Loads `misc/dongle.glb` (the *assembled* dongle), splits it by node-
  name prefix into a fixed PCB base + four draggable parts (OBD port / blue IC / green IC /
  diode), each grouped under a pivot at its centroid (so its natural position IS its home).
  Scatters the loose parts around a glowing target socket per part; a left-press (`Picker`)
  grabs the part under the cursor, it floats toward the camera and follows a board-plane
  projection of the mouse (`_cursor_on_plane`), and release seats it if within
  `DONGLE_SNAP_DIST` of home (else it drops back to the bench). Seat all four →
  `Game.grant_god(DONGLE_ACHIEVEMENT)` → "Certified Plug". `board_root` is unrotated at the
  origin so world == board frame; all tuning lives in the `DONGLE_*` constants.
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
- **Achievements are table-driven (no scattered unlock calls).** `constants.ACHIEVEMENTS`
  is the single source: `key → Achievement(label, blurb, cred, check)`, where `check` is a
  list of `(stat_path, required)` pairs. The app calls **`Game.check_unlocks()` every ~250ms**
  (`UNLOCK_POLL_SECONDS`, gated on `session_started`); it resolves each dotted `stat_path`
  against the game (`Game._resolve` — e.g. `"bro.total_pops"`, `"car.flashed"`,
  `"wizard_ready"`) and unlocks the moment ANY pair reads `>= required` (uniform for ints and
  bools). `Game.unlock(key)` is idempotent and pulls the label + cred from the table. So
  gameplay code only keeps **stats** current (`bro.total_pops`, `tunes_sold`, `beat_king`,
  `car.fully_built`, …) — the dyno/bench/shop/race/street tasks no longer call `unlock` at
  all. A few derived booleans/ints back the compound checks (`Car.e30_lifestyle`/`is_grade_s`/
  `last_blown`/`dyno_pop`/`fully_built`, `TunerBro.community_maps`/`pro_maps`,
  `Game.wizard_ready`). The only **manual** unlocks are the two Wizard endings (`god_status`/
  `dongle_dealer`, `check=()`) — both set `bro.god`, so no stat tells them apart; `grant_god(key)`
  unlocks the chosen one. To add an achievement: add one table row + a stat for it to watch.
- `game.py` — `Game`: root/session. Holds `bro: TunerBro`, `rivals: [RivalGreenName]`,
  `cars: CarLibrary`, `discord: Discord` (model), transient `logs`, a `car` property, and
  the orchestration that spans nodes (`buy_mod`, `register_pops`, `ask_discord`, log). It
  also owns the **advisor panels** `simon_panel`/`discord_panel` and the game-level
  **chrome `UIObjectController` `ui`** (Ask Simon / Ask Discord / Back) — all built by
  the app on first hub entry and assigned here, not reset by `new_game` — plus
  `set_advisors_visible(bool)` so a task can show/hide the Ask buttons. `new_game()` resets
  a fresh career **in place** (so cached references survive); `to_dict`/`from_dict` cover
  the bro, car library (build + mods), discord presence, and the career
  counters/achievements (stamped with `SAVE_VERSION`), restoring in place. The **rival
  ladder is intentionally not saved** — it's static reference data from `RIVALS`, always
  rebuilt by `new_game`; only progress (`bro.unlocked_rival`/`selected_rival`) persists.
  (`SAVE_VERSION 1` saved the ladder and froze stale specs into old saves — e.g. a rival's
  `model` — so a constant edit didn't take effect on load; v2 drops it.)
- `tuner_bro.py` — `TunerBro`: the user — cash, **cred** (which doubles as the arcade
  score), Karen/heat, rep, ladder progress, `unlocked_maps`
  (`spend`/`earn`/`pay_repair`/`add_cred`/`add_heat`/`unlock_map`).
- `scoreboard.py` — `build_scoreboard(name, score)`: the arcade hall-of-fame — the fixed
  made-up handles (`SCOREBOARD_NAMES`) plus the player's row, sorted + ranked.
  `build_achievements(unlocked)`: the trophy case — every key in the `ACHIEVEMENTS` registry
  flagged unlocked-or-not, unlocked floated to the top (drives the scoreboard's pane).
- `rival_green_name.py` — `RivalGreenName`: a ladder rival = encounter metadata
  (`name`/`purse`/`color`/win-loss clips) **plus a `Car`** built from the spec's `car_id`
  (from `RIVALS`). Rivals start mod-free; the ladder will be tuned later by giving them
  mods.
- `car.py` — `Car(car_id)`: one class for the player AND rivals. Pulls its physics spec
  (real-world rpm→whp curve, gears, final drive, tire circ, mass, grip, redline, spool,
  boost ceiling) from `CAR_TABLE[car_id]`; ECU/tune/slot state is the player's (inert on
  rivals, which never flash). **`build_whp()`** composes the final rpm→whp curve = base
  curve + owned mods (+ the flashed tune, which scales it) via `tuning.build_whp_curve`;
  `whp_at(rpm)` interpolates it; `car_perf()` returns the curve + peak whp + mass/grip
  (base ± mod deltas) + blown/rel. **Turbo variants (owned + equipped):** `Car.owned_turbos`
  is the set you've bought and `Car.turbo` is the one fitted; `buy_turbo(id)` owns+equips,
  `equip_turbo(id)` switches free among owned. `_turbo_spec()` resolves the fitted variant
  (defaulting to IS38 for rivals/old saves that only have the `mods["turbo"]` bool) and
  `_effects_table()` = `BASE_EFFECTS` with `"turbo"` swapped for that spec, so `build_whp`/
  `car_perf`/`compute` reflect the chosen turbo. `boost_slider_max()` returns the boost
  slider's ceiling (stock `max_boost`, or the fitted turbo's `blown_boost`). `blow_dave_pool()`
  picks the Dave pool when it grenades. State-change methods return `(message, kind)` so `Game` logs them.
  `apply_preset` accepts `PRESETS` **and** `COMMUNITY_MAPS` keys. Save dict adds `car_id` +
  `turbo` + `owned_turbos` (old v3 saves with `mods["turbo"]` migrate to IS38 + back-fill
  owned; `SAVE_VERSION` 4).
- `car_library.py` — `CarLibrary`: the bro's car(s) + active index (`active()`);
  reconstructs each car from its saved `car_id` so the physics spec reloads.
- `discord.py` — `Discord`: the *MQB Vibe Coders* server. Builds the roster from
  `DISCORD_ROSTER` (each row → an `Admin`/`GreenName`/`NormalUser`), samples who's
  online (`refresh_online`), supplies channel `backlog` chatter, and `resolve(text, ctx)`
  → an outcome (request quality + who's online + a dice roll decide good vs bad).
- `discord_user.py` — `DiscordUser` base (identity, online roll, chatter, persona
  `lean`); `discord_admin.py`/`discord_green_name.py`/`discord_normal_user.py` are the
  role subclasses (Admin trusts good, GreenName pulls money, NormalUser is persona-only).
- `app.py` — `MK7Tuner3D`: the ShowBase shell + stage manager + `TASK_CLASSES`.
- `geometry.py` — box/grid builders (the exhaust-flame cubes).
- `tuning.py` — tune + curve math: `compute_tune(tune, mods, turbo=None)` (calibration →
  tune-only peak whp + knock/EGT/reliability/pop/blown; the optional `turbo` spec sets the
  boost ceiling + blow-up threshold, else it falls back to the `mods["turbo"]` bool;
  **hardware power lives in the mod curves now, not here**), `build_whp_curve(base,
  owned_mods, …, effects=BASE_EFFECTS)` (a car passes its own `effects` so `"turbo"` resolves
  to the fitted variant) + `whp_at(curve, rpm)`, plus grading, pops, rep.
- `simos.py` — "Ask Simon" rules engine; `build_context(game, tab)` reads bro + car (and
  shows Simon the real **built** peak whp, not the tune-only figure).

The **DynoTask** (`library/stages/tasks/dyno_task.py`) is SimosTools-style: a pull
sweeps the car's idle→redline (`tick`), sampling the car's real `build_whp()` curve to
drive compact gauge **tiles** on the left (scale, big value, `min:max`, unit, green fill +
red danger band, from `constants.DYNO_GAUGES`) and a large **power + torque graph** on the
right. The graph (`_draw_graph`/`_trace`, `LineSegs` on the UI layer so it draws above the
panel) plots **whp (cyan) and torque (amber)** for the current build, plus the car's
**stock `base_curve` faint** behind them as a reference, with rpm tick labels on the X axis
and peak whp/lb-ft readouts; the current curve animates up to the live rpm during a pull,
shows full at rest. Records the built peak + `grade_for_result` on the `Car`. (NB:
`LineSegs.getNumVertices()` is unreliable — use `isEmpty()` to test for geometry.)

The **RaceTask** (`library/stages/tasks/race_task.py`) accelerates both cars off their
`Car` curves through their own gearing: `_engine_rpm` derives rpm from speed + the current
gear + final drive + tire circ, `_step_car` makes power = `whp_at(curve, rpm)` (grip-capped
at low speed, **zero on the rev limiter** so you must shift), and the rival `_auto_shift`s
near its redline (the player shifts on SPACE). Each car's curve + mass/grip are built once
per run in `_start_race`.

The **ShopTask** (`library/stages/tasks/shop_task.py`) is a **2×3 grid of cards** (`N_CARDS=6`),
one per `ShopItem` (`shop_item.py`): thumbnail · name · brief description · an owned/equipped
tag · **Read review** · **Buy/Equip**. `build_catalog()` builds the list straight off the
single `PARTS` table (6 bolt-on mods + the 4 turbos, in table order); the task holds the 6 fixed card slots and an item paints itself into
a slot via `ShopItem.bind_to_slot` (wiring that slot's two buttons back to `_card_action` /
`_open_review`), the same windowed-scroll pattern as the scoreboard pane (scroll by a row =
`COLS`, via wheel / ▲▼ / arrows). **Equippable families:** `ShopItem.category` ("turbo" today,
"intercooler" next) marks mutually-exclusive items you **own many of and equip one** —
`is_owned`/`is_equipped`/`owned_label`/`action` drive a dual button: **Buy $price** (unowned,
GREEN) → **Equip** (owned, not fitted, free swap, VIOLET) → **Equipped** (disabled). Bolt-on
mods (`category=None`) are cumulative. `_card_action` spends + `Car.buy_turbo`/`Car.set_mod`,
or free `Car.equip_turbo`; `ed_cut` turbos log an "Ed gets his cut" line. `_open_review` opens
the **`ReviewOverlay`** (`review_overlay.py`) — a faux-browser pane that animates a tiny rect
at the pressed button out to a near-fullscreen, slightly-translucent window (LerpPos+LerpScale
via `direct.interval`, like `unlock_stage`) showing the item's full `review` with the
**detective clipart** (`detective.png`) on the right; the title-bar **X** or Esc animates it
back into the button. The green-name pro storefront (sell tunes / DM the pros) is unchanged
below the grid.

The **ScoreboardTask** (`library/stages/tasks/scoreboard_task.py`, opened by the garage's
HIGH SCORES button) is an 80s-arcade HALL OF FAME: a CRT backdrop + scanlines, the bro's
big score, a stats line, and a ranked board from `scoreboard.build_scoreboard` (the player
vs the made-up handles), with the player's row + exit prompt blinking in `tick`. **The score
is simply the bro's `cred`** — there's no separate points stat; everything that already
grants cred (race purses, pops & bangs via `POP_CRED_CONST`, tune sales, achievement
unlocks via `Game.unlock`, and the Wizard challenge via `Game.grant_god`) climbs the board.
An **ACHIEVEMENTS** button opens a scrollable trophy pane *over* the board (built once,
hidden, toggled by key-prefix visibility so the 80s board is untouched): every trophy from
the `ACHIEVEMENTS` registry via `scoreboard.build_achievements` — unlocked ones gold at the
top, locked ones dimmed with how-to hints — scrolled by the wheel, ▲▼ buttons, or arrow keys.

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
