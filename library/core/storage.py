from __future__ import annotations

import json
import os

from library.core.constants import APP_NAME, CONFIG_FILE, SAVE_FILE


def app_data_dir() -> str:
    """Writable per-user folder for the save game and options.

    ``%APPDATA%/MK7 GTI Tuner`` on Windows, ``~/.MK7 GTI Tuner`` elsewhere -- always
    writable (unlike the bundled ``data/`` dir in a frozen build). Created on demand."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(app_data_dir(), CONFIG_FILE)


def save_path() -> str:
    return os.path.join(app_data_dir(), SAVE_FILE)


def has_save() -> bool:
    return os.path.isfile(save_path())


def read_json(path: str):
    """Parsed JSON, or ``None`` if the file is missing or corrupt (never raises)."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def write_json(path: str, data) -> bool:
    """Write JSON atomically (temp file + replace). Returns success."""
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)
        return True
    except OSError:
        return False
