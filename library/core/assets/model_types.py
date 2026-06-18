from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

from library.core.constants import (
    CAR_MODEL_FILES, CAR_MODEL_DIRECTORY, 
    CHARACTER_MODEL_DIRECTORY, CHARACTER_MODEL_FILES, 
    GEOMETRY_MODEL_DIRECTORY, GEOMETRY_MODEL_FILES,
    MISC_MODEL_DIRECTORY, MISC_MODEL_FILES,
)

@dataclass
class ModelInfo:
    directory:          str     # location of models
    dictionary:         dict    # list of model file names
    

class ModelType(Enum):
    CAR         = ModelInfo(CAR_MODEL_DIRECTORY, CAR_MODEL_FILES)
    CHARACTOR   = ModelInfo(CHARACTER_MODEL_DIRECTORY, CHARACTER_MODEL_FILES)
    GEOMETRY    = ModelInfo(GEOMETRY_MODEL_DIRECTORY, GEOMETRY_MODEL_FILES)
    MISC        = ModelInfo(MISC_MODEL_DIRECTORY, MISC_MODEL_FILES)