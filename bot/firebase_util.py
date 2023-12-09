import os
import json
import datetime
import firebase_admin
from constants import Role, Direction
from firebase_admin import credentials, firestore

db = None
app = None


def init():
    global app, db

    cred = credentials.Certificate(os.environ.get("SERVICE_ACCOUNT_PATH"))
    app = firebase_admin.initialize_app(cred)
    db = firestore.client()


def reset():
    with open("groups.txt") as f:
        for idx, x in enumerate(
            list(filter(lambda x: len(x), map(lambda x: x.strip(), f.readlines())))
        ):
            db.collection("groups").document(f"{idx + 1}").set({"name": x})
    with open("admins.txt") as f:
        for x in list(
            filter(lambda x: len(x), map(lambda x: x.strip(), f.readlines()))
        ):
            db.collection("admins").document(x).set({"registered": False})
    with open("gls.json") as f:
        gl = json.loads(f.read())
        for key in gl:
            group_ref = db.collection("groups").document(key)
            for user in gl[key]:
                db.collection("users").document(user).set(
                    {"registered": False, "group": group_ref}
                )
    with open("challenges.json") as f:
        challs = json.loads(f.read())
        standard_challs = challs["standard"]
        for key in standard_challs:
            db.collection("challenges").document(key).set(standard_challs[key])
        db.collection("challenges").document("sabotage").set(
            {"challenges": challs["sabotage"]}
        )


def set_broadcast_group(username: str, chatid: int):
    get_user_group(username).update({"broadcast_channel": chatid})


def get_admin_broadcast() -> int:
    return db.collection("admins").document("_globals").get().to_dict()["broadcast"]


def register_user(username: str, userid: int):
    db.collection("users").document(username).update({"registered": True})
    set_broadcast_group(username, userid)


def register_admin(username: str):
    db.collection("admins").document(username).update({"registered": True})


def get_user_group(username: str) -> str | None:
    return db.collection("users").document(username).get().to_dict()["group"]


def get_role(username: str) -> Role:
    user = db.collection("users").document(username).get()
    if user.exists and user.to_dict()["registered"]:
        return Role.GL
    admin = db.collection("admins").document(username).get()
    if admin.exists and admin.to_dict()["registered"]:
        return Role.Admin
    return Role.Unregistered


def set_location(username: str, lat: float, lng: float):
    db.collection("users").document(username).update(
        {
            "location": firestore.firestore.GeoPoint(lat, lng),
            "last_update": firestore.firestore.SERVER_TIMESTAMP,
        }
    )


# last 5 minutes
def recent_location_update(username: str) -> bool:
    user = db.collection("users").document(username).get().to_dict()
    try:
        return (
            user["location"]
            and (
                datetime.datetime.now(datetime.timezone.utc) - user["last_update"]
            ).total_seconds()
            < 300
        )
    except KeyError:
        return False


def has_race_started(username: str) -> bool:
    try:
        return bool(get_user_group(username).get().to_dict()["start_time"])
    except KeyError:
        return False


def get_start_chall_index(direction: Direction) -> int:
    return 0 if str(direction)[1] == "1" else (1 if direction == Direction.A0 else 4)


def start_race(username: str, direction: Direction) -> dict | None:
    group_ref = get_user_group(username)
    group_ref.update(
        {
            "start_time": firestore.firestore.SERVER_TIMESTAMP,
            "current_location": get_start_chall_index(direction),
            "current_task": 0,
            "direction": str(direction),
        }
    )
    return group_ref.get().to_dict()


def get_current_challenge(username: str):
    group = get_user_group(username).get().to_dict()
    for doc in (
        db.collection("challenges")
        .where(
            filter=firestore.firestore.FieldFilter(
                "order", "==", group["current_location"]
            )
        )
        .limit(1)
        .stream()
    ):
        return doc.to_dict()["challenges"][group["current_task"]]
