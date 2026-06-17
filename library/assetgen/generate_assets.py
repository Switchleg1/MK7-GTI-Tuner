#!/usr/bin/env python3
"""Regenerate all game assets into data/models (.glb) and data/images (.png).

Re-runnable and offline (no game window needed). Run from the project root:

    python -m library.assetgen.generate_assets
"""
from __future__ import annotations

import os

from library.assetgen import asset_audio
from library.assetgen import asset_car
from library.assetgen import asset_character
from library.assetgen import asset_ground
from library.assetgen import asset_images
from library.assetgen import asset_obd
from library.assetgen import asset_phone
from library.core.constants import AUDIO_DIR, IMAGES_DIR, MODELS_DIR

# Project root (library/assetgen/ -> library -> root); write data there.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_BUILDERS = [asset_ground, asset_car, asset_character, asset_phone, asset_obd]


def main():
    models_dir = os.path.join(ROOT, MODELS_DIR)
    images_dir = os.path.join(ROOT, IMAGES_DIR)
    audio_dir = os.path.join(ROOT, AUDIO_DIR)
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    print("Models:")
    for module in MODEL_BUILDERS:
        path = module.build(models_dir)
        print(f"  {os.path.basename(path):<16} {os.path.getsize(path):>7} bytes")

    print("Images:")
    for path in asset_images.build(images_dir):
        print(f"  {os.path.basename(path):<24} {os.path.getsize(path):>7} bytes")

    print("Audio:")
    for path in asset_audio.build(audio_dir):
        print(f"  {os.path.basename(path):<18} {os.path.getsize(path):>7} bytes")

    print("Done.")


if __name__ == "__main__":
    main()
