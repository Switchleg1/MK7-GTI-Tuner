# MK7 GTI Tuner (3D)

A 3D Panda3D remake of the *MK7 GTI Tuner* parody game. You unlock and flash a
MK7 Golf GTI's ECU, then tune it, dyno it, run the streets, race the strip, and
spend your winnings on mods.

The headline of this build is the **cinematic ECU unlock**: instead of clicking
through instant buttons, you watch a guy sitting in the open driver door plug an
OBD2 adapter into the car, pull out his phone, and flash the ECU — with real
delays, progress bars, and the ECU readout streaming onto the phone screen.

## Requirements

- Python 3.x
- `pip install -r requirements.txt`
  - `panda3d` — engine
  - `panda3d-gltf` — loads the `.glb` models at runtime (pulls in `panda3d-simplepbr`)
  - `pygltflib` — generates the `.glb` models (only needed to rebuild assets)

## Run

```
python mk7_gti_tuner.py
```

## Regenerate assets

Models and images are committed under `data/`, but you can rebuild them any time
(run from the project root):

```
python -m library.assetgen.generate_assets
```

This writes `data/models/*.glb`, `data/images/*.png`, and `data/audio/*.wav`. All
geometry is built procedurally in Panda's Z-up convention and loaded with
`skip_axis_conversion=True`; the sound effects are synthesized with the standard
library (no extra deps) by `library/assetgen/asset_audio.py`.

## Build a standalone .exe (Windows)

```
build.bat
```

This runs PyInstaller (`--onefile --windowed`) and **bundles `data/`** so the exe
finds its models/images. At runtime assets resolve from `sys._MEIPASS` when frozen,
or the project root when run from source (see `library/core/assets.py`).

## How it plays

1. **Unlock (cinematic).** The guy sits in the open driver door, feet on the ground.
   1. **Click the OBD2 port** under the dash → he plugs in the adapter (link progress).
   2. **Tap the phone** → he raises it and the SimosTools app opens.
   3. **Hit FLASH** on the phone → progress bars + delays while the ECU readout
      (VIN, ECU, software, calibration, flash size…) streams onto the screen.
   4. He celebrates → **Continue**.
2. **Garage hub.** The GTI sits in the bay; click a task button to enter a task:
   - **TUNE** — boost/timing/fuel presets and switch-patch map slots.
   - **DYNO** — strap it down, run a pull, get a graded result.
   - **STREET** — blip the throttle and preview pops for cred (mind the Karen meter).
   - **RACE** — quarter-mile vs the street ladder.
   - **SHOP** — spend winnings on mods. **BENCH** — re-flash the current tune.
3. Each task has a **Back** button (bottom-left) that returns you to the garage hub.

### Controls

- **Mouse** — click task buttons, in-task buttons, Back, and the phone.
- **Space** — throttle (Street) / launch & shift (Race). **Esc** — quit.

## Data layout

```
data/
  models/   ground.glb car.glb character.glb phone.glb obd.glb   (.glb, glTF binary)
  images/   phone_wallpaper.png simostools_icon.png flash_complete.png logo.png
  audio/    engine_loop.wav intake_loop.wav turbo_loop.wav pop_*.wav bang_*.wav bov.wav
```

Standard formats for now; a packed custom format may come later.

## Project rules

- One class (or data class) per file.
- All defaults, thresholds, sequences, and placements live in `constants.py`.
- Logic lives in tables and is iterated — no large `if/elif` staircases.
- Keep modules small and modular.

See `architecture.md` for the module map and how the pieces fit together.
