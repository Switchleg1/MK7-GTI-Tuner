from __future__ import annotations

from panda3d.core import loadPrcFileData

from constants import DEFAULT_HEIGHT, DEFAULT_WIDTH, APP_NAME


def configure_panda3d():
    loadPrcFileData(
        "",
        "\n".join(
            [
                f"window-title {APP_NAME}",
                f"win-size {DEFAULT_WIDTH} {DEFAULT_HEIGHT}",
                "show-frame-rate-meter false",
                "sync-video true",
                "textures-power-2 none",
            ]
        ),
    )
