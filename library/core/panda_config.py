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
                # Hard-cap the frame rate so the render loop can't free-run. `sync-video`
                # (vsync) alone isn't enough -- some drivers ignore it in windowed mode, and
                # then the loop spins as fast as possible, pegging a CPU core and hammering
                # the GPU with frames until the whole system bogs down. `clock-mode limited`
                # makes Panda sleep to hold this rate regardless of vsync.
                "clock-mode limited",
                "clock-frame-rate 60",
                "textures-power-2 none",
                "framebuffer-multisample 1",
                "multisamples 4",
            ]
        ),
    )
    _select_audio_backend()


def _select_audio_backend():
    """Use the OpenAL backend (Panda's default). Its ffmpeg path decodes the audio track out
    of the race-result ``.mp4`` clips; the FMOD backend cannot ("Unsupported file or audio
    format") -- that's why we don't use FMOD despite its per-sound stereo balance. An explicit
    ``null`` (offscreen tests) is left untouched."""
    from panda3d.core import ConfigVariableString

    if ConfigVariableString("audio-library-name", "").getValue() == "null":
        return
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
