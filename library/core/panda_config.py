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
    _select_audio_backend()


def _select_audio_backend():
    """Prefer the FMOD backend, which honours per-sound stereo balance (used to pan the two
    engines in a race). Fall back to OpenAL (Panda's default) when FMOD isn't available --
    panning then no-ops but everything else still plays. An explicit ``null`` (offscreen
    tests) is left untouched."""
    from panda3d.core import AudioManager, ConfigVariableString

    if ConfigVariableString("audio-library-name", "").getValue() == "null":
        return
    loadPrcFileData("", "audio-library-name p3fmod_audio")
    try:
        mgr = AudioManager.createAudioManager()
        if mgr is not None and mgr.isValid():
            return
    except Exception:  # noqa: BLE001 - never let audio setup crash startup
        pass
    loadPrcFileData("", "audio-library-name p3openal_audio")


def enable_gltf(base):
    """Render glTF materials with Panda's auto-shader (PBR base colors + lights).

    panda3d-gltf loads the .glb files; simplepbr is intentionally not used so we
    avoid its per-frame camera-input requirement and keep startup robust.
    """
    from panda3d.core import AntialiasAttrib

    base.render.setShaderAuto()
    # Multisample (not MAuto) so we don't get polygon-smoothing edge lines.
    base.render.setAntialias(AntialiasAttrib.MMultisample)
