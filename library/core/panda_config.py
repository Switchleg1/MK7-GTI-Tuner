from __future__ import annotations

from panda3d.core import loadPrcFileData

from library.core.constants import DEFAULT_HEIGHT, DEFAULT_WIDTH, APP_NAME


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
                "framebuffer-multisample 1",
                "multisamples 4",
            ]
        ),
    )


def enable_gltf(base):
    """Render glTF materials with Panda's auto-shader (PBR base colors + lights).

    panda3d-gltf loads the .glb files; simplepbr is intentionally not used so we
    avoid its per-frame camera-input requirement and keep startup robust.
    """
    from panda3d.core import AntialiasAttrib

    base.render.setShaderAuto()
    # Multisample (not MAuto) so we don't get polygon-smoothing edge lines.
    base.render.setAntialias(AntialiasAttrib.MMultisample)
