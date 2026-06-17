from __future__ import annotations

from direct.interval.IntervalGlobal import LerpHprInterval, Parallel

from library.core.constants import CHARACTER_POSES

# Every joint named across all poses; used to resolve NodePaths once up front.
POSE_JOINTS = sorted({joint for pose in CHARACTER_POSES.values() for joint in pose})


class Character:
    """Controls the seated guy's posable joints (loaded from character.glb).

    Poses are HPR targets in constants.CHARACTER_POSES; ``pose_interval`` lerps the
    relevant joints so the stage can sequence: rest -> reach (plug) -> hold_phone
    -> cheer. The phone prop reparents to the right hand.
    """

    def __init__(self, model):
        self.model = model
        self.joints = {name: model.find(f"**/{name}") for name in POSE_JOINTS}
        self.right_hand = model.find("**/rHand")
        self.set_pose("rest")

    def set_pose(self, name: str):
        for joint, hpr in CHARACTER_POSES[name].items():
            np = self.joints.get(joint)
            if np is not None and not np.isEmpty():
                np.setHpr(*hpr)

    def pose_interval(self, name: str, seconds: float) -> Parallel:
        lerps = [
            LerpHprInterval(self.joints[joint], seconds, hpr, blendType="easeInOut")
            for joint, hpr in CHARACTER_POSES[name].items()
            if joint in self.joints and not self.joints[joint].isEmpty()
        ]
        return Parallel(*lerps)

    def attach_to_hand(self, np, offset):
        if not self.right_hand.isEmpty():
            np.reparentTo(self.right_hand)
            np.setPos(*offset)
