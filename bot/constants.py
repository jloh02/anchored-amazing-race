from enum import Enum


class Role(Enum):
    Admin = 0
    GL = 1
    Unregistered = 2


class ConvState(str, Enum):
    ChooseDirection = "ChooseDirection"
    ChooseDirectionConfirmation = "ChooseDirectionConfirmation"
    ChooseDirectionConfirmationNo = "ChooseDirectionConfirmationNo"


class Direction(str, Enum):
    A1 = "A1"
    A0 = "A0"
    B1 = "B1"
    B0 = "B0"
