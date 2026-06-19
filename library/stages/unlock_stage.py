from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectLabel
from direct.gui.OnscreenImage import OnscreenImage
from direct.interval.IntervalGlobal import Func, LerpColorScaleInterval, LerpFunc, LerpPosInterval, Parallel, Sequence, Wait
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib

import library.core.assets as assets
from library.stages.character import Character
from library.core.constants import (
    BLUE,
    CELEBRATE_SECONDS,
    CHARACTER_POS,
    DIM,
    ECU_READOUT,
    GREEN,
    GREEN_2,
    LINK_STEPS,
    OBD_ADAPTER_PLUGGED,
    OBD_ADAPTER_REST,
    OBD_PORT_POS,
    PHONE_IN_HAND,
    PLUG_IN_SECONDS,
    RAISE_PHONE_SECONDS,
    TEXT,
    UNLOCK_CAMERA,
    UNLOCK_FLASH_STEPS,
    UNLOCK_FOV,
    UNLOCK_PROMPTS,
    WHITE,
)
from library.stages.phone_screen import PhoneScreen
from library.stages.picker import Picker
from library.stages.progress_bar import ProgressBar


class UnlockStage(DirectObject):
    """The cinematic ECU unlock: plug in the OBD2 adapter, raise the phone, FLASH.

    Drives a small phase machine (plug -> phone -> flash -> done) with delays and
    progress so the unlock feels real, then calls ``on_complete`` to move on. The
    FLASH portion (PhoneScreen + ProgressBar + UNLOCK_FLASH_STEPS) is self-contained
    so it can later be reused for re-flashing staged maps from the BENCH tab.
    """

    def __init__(self, base, on_complete):
        super().__init__()
        self.base = base
        self.on_complete = on_complete
        self.root = base.render.attachNewNode("unlock-scene")
        self.ui = base.aspect2d.attachNewNode("unlock-ui")
        self.sequence = None
        self._pulse_iv = None
        self._pulse_np = None
        self.continue_button = None

        self._build_scene()
        self._build_ui()
        self.phone_screen = PhoneScreen(base)
        self.picker = Picker(base)
        self._enter_phase("plug")

    # -- scene -------------------------------------------------------------
    def _build_scene(self):
        assets.load_model(assets.ModelType.GEOMETRY, "ground").reparentTo(self.root)
        assets.load_model(assets.ModelType.CAR, "mk7_gti").reparentTo(self.root)

        char_model = assets.load_model(assets.ModelType.CHARACTOR, "character")
        char_model.reparentTo(self.root)
        char_model.setPos(*CHARACTER_POS)
        self.character = Character(char_model)

        obd = assets.load_model(assets.ModelType.MISC, "obd")
        self.port = obd.find("**/obd_port")
        self.port.reparentTo(self.root)
        self.port.setPos(*OBD_PORT_POS)
        self.adapter = obd.find("**/obd_adapter")
        self.adapter.reparentTo(self.port)
        self.adapter.setPos(*OBD_ADAPTER_REST)

        self.phone = assets.load_model(assets.ModelType.MISC, "phone")
        self.character.attach_to_hand(self.phone, PHONE_IN_HAND)
        self.phone.hide()

        self.base.camera.setPos(*UNLOCK_CAMERA["pos"])
        self.base.camera.lookAt(*UNLOCK_CAMERA["look_at"])
        if self.base.camLens:
            self.base.camLens.setFov(UNLOCK_FOV)

    def _build_ui(self):
        logo = OnscreenImage(parent=self.ui, image=assets.image_path("logo"), pos=(-1.18, 0, 0.86), scale=(0.30, 1, 0.082))
        logo.setTransparency(TransparencyAttrib.MAlpha)
        self.title = DirectLabel(parent=self.ui, text="ECU UNLOCK", pos=(-1.48, 0, 0.74), scale=0.05, text_fg=GREEN, text_align=TextNode.ALeft, frameColor=(0, 0, 0, 0), relief=None)
        self.prompt = DirectLabel(parent=self.ui, text="", pos=(-0.5, 0, -0.82), scale=0.062, text_fg=WHITE, text_align=TextNode.ACenter, frameColor=(0, 0, 0, 0), relief=None)
        self.substep = DirectLabel(parent=self.ui, text="", pos=(-0.5, 0, -0.90), scale=0.036, text_fg=DIM, text_align=TextNode.ACenter, frameColor=(0, 0, 0, 0), relief=None)
        self.link_bar = ProgressBar(self.ui, (-0.5, 0, -0.97), 0.9, 0.03, (0.05, 0.08, 0.10, 1), GREEN)
        self.link_bar.track.hide()

    # -- phase machine -----------------------------------------------------
    def _enter_phase(self, phase: str):
        self.phase = phase
        self._stop_pulse()
        self.picker.clear()
        self.prompt["text"] = UNLOCK_PROMPTS.get(phase, "")
        self.substep["text"] = ""
        if phase == "plug":
            self.picker.register(self.port, "port", self._on_plug)
            self._pulse(self.port)
        elif phase == "phone":
            self.phone.show()
            self.picker.register(self.phone, "phone", self._on_phone)
            self._pulse(self.phone)
        elif phase == "flash":
            self.phone_screen.arm_flash(self._on_flash)
        elif phase == "done":
            self._show_continue()

    def _on_plug(self):
        self.picker.clear()
        self.prompt["text"] = UNLOCK_PROMPTS["plugging"]
        self._stop_pulse()
        self.link_bar.track.show()
        seq = Sequence(
            Parallel(self.character.pose_interval("reach", PLUG_IN_SECONDS), LerpPosInterval(self.adapter, PLUG_IN_SECONDS, OBD_ADAPTER_PLUGGED, blendType="easeInOut")),
        )
        total = len(LINK_STEPS)
        for index, (label, secs) in enumerate(LINK_STEPS):
            seq.append(Func(self._set_substep, label, (index + 1) / total))
            seq.append(Wait(secs))
        seq.append(self.character.pose_interval("rest", 0.5))
        seq.append(Func(self.link_bar.track.hide))
        seq.append(Func(self._enter_phase, "phone"))
        self._play(seq)

    def _set_substep(self, label: str, fraction: float):
        self.substep["text"] = label
        self.link_bar.set(fraction)

    def _on_phone(self):
        self.picker.clear()
        self._stop_pulse()
        self.prompt["text"] = UNLOCK_PROMPTS["raising"]
        seq = Sequence(
            self.character.pose_interval("hold_phone", RAISE_PHONE_SECONDS),
            Func(self.phone_screen.show),
            Func(self._enter_phase, "flash"),
        )
        self._play(seq)

    def _on_flash(self):
        self.prompt["text"] = UNLOCK_PROMPTS["flashing"]
        self.phone_screen.begin_progress()
        seq = Sequence()
        previous = 0.0
        for index, (label, secs, target) in enumerate(UNLOCK_FLASH_STEPS):
            seq.append(Func(self.phone_screen.append_log, label, BLUE))
            if index < len(ECU_READOUT):
                field, value = ECU_READOUT[index]
                seq.append(Func(self.phone_screen.append_log, f"  {field}: {value}", TEXT))
            seq.append(LerpFunc(self.phone_screen.set_progress, fromData=previous, toData=target, duration=secs))
            previous = target
        seq.append(Func(self._on_flash_done))
        self._play(seq)

    def _on_flash_done(self):
        self.phone_screen.append_log("Flash verified. ECU unlocked.", GREEN)
        self.phone_screen.show_complete("ECU UNLOCKED")
        self._play(self.character.pose_interval("cheer", CELEBRATE_SECONDS))
        self._enter_phase("done")

    # -- continue ----------------------------------------------------------
    def _show_continue(self):
        self.prompt["text"] = UNLOCK_PROMPTS["done"]
        self.continue_button = DirectButton(
            parent=self.ui,
            text="Continue  >",
            pos=(-0.5, 0, -0.92),
            scale=1,
            text_scale=0.05,
            text_fg=WHITE,
            text_align=TextNode.ACenter,
            frameSize=(-0.30, 0.30, -0.07, 0.07),
            frameColor=GREEN_2,
            relief=DGG.FLAT,
            pressEffect=0,
            command=self._finish,
        )

    # -- helpers -----------------------------------------------------------
    def _play(self, interval):
        self.sequence = interval
        interval.start()

    def _pulse(self, np):
        self._pulse_np = np
        self._pulse_iv = Sequence(
            LerpColorScaleInterval(np, 0.55, (1.7, 1.6, 1.0, 1), (1, 1, 1, 1)),
            LerpColorScaleInterval(np, 0.55, (1, 1, 1, 1), (1.7, 1.6, 1.0, 1)),
        )
        self._pulse_iv.loop()

    def _stop_pulse(self):
        if self._pulse_iv is not None:
            self._pulse_iv.finish()
            self._pulse_iv = None
        if self._pulse_np is not None and not self._pulse_np.isEmpty():
            self._pulse_np.clearColorScale()
            self._pulse_np = None

    def _finish(self):
        self.cleanup()
        self.on_complete()

    def cleanup(self):
        self._stop_pulse()
        if self.sequence is not None:
            self.sequence.finish()
            self.sequence = None
        self.picker.destroy()
        self.phone_screen.destroy()
        self.link_bar.destroy()
        if self.continue_button is not None:
            self.continue_button.destroy()
        self.ui.removeNode()
        self.root.removeNode()
        self.ignoreAll()
