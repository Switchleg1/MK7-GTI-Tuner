#!/usr/bin/env python3
from __future__ import annotations

from panda_config import configure_panda3d

configure_panda3d()

from app import MK7Tuner3D


if __name__ == "__main__":
    MK7Tuner3D().run()
