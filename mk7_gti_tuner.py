#!/usr/bin/env python3
from __future__ import annotations

from library.core.panda_config import configure_panda3d

configure_panda3d()

from library.game.app import MK7Tuner3D


if __name__ == "__main__":
    MK7Tuner3D().run()
