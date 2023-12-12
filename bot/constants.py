from enum import Enum

RECENT_LOCATION_MAX_TIME = 300  # seconds
NUMBER_LOCATIONS = 4
PHOTO_ROTATION_TIME = 10  # seconds

END_LAT_LNG = (1.3343111322740955, 103.84651235559575)
END_TOLERANCE = 50  # m

# Performance tuning
TELEGRAM_READ_TIMEOUT = 10
TELEGRAM_CONCURRENT_UPDATES = 16
CONVERSATION_TIMEOUT = 600


class Role(Enum):
    Admin = 0
    GL = 1
    Unregistered = 2


class ConvState(str, Enum):
    ChooseDirection = "ChooseDirection"
    ChooseDirectionConfirmation = "ChooseDirectionConfirmation"
    ChooseDirectionConfirmationNo = "ChooseDirectionConfirmationNo"
    SelectChallenge = "SelectChallenge"
    SubmitText = "SubmitText"
    SubmitPhoto = "SubmitPhoto"
    SubmitVideo = "SubmitVideo"


class ChallengeType(str, Enum):
    Text = "Text"
    Photo = "Photo"
    Video = "Video"


class Direction(str, Enum):
    A1 = "A1"
    A0 = "A0"
    B1 = "B1"
    B0 = "B0"
