import os
import json
import logging
import asyncio
import datetime
import firebase_admin
from constants import (
    Role,
    Direction,
    RECENT_LOCATION_MAX_TIME,
    NUMBER_LOCATIONS,
    MAX_BONUS_GROUPS,
)
from firebase_admin import credentials, firestore

db = None
app = None
broadcast_channel = None

logger = logging.getLogger("firebase")


group_cache = {}
challenge_cache = {}


def init():
    global app, db

    cred = credentials.Certificate(os.environ.get("SERVICE_ACCOUNT_PATH"))
    app = firebase_admin.initialize_app(cred)
    db = firestore.client()


def reset():
    global group_cache, challenge_cache
    group_cache = {}
    challenge_cache = {}
    for doc in db.collection("admins").list_documents():
        if doc.id == "_globals":
            continue
        doc.delete()
    with open("admins.txt") as f:
        for x in list(
            filter(lambda x: len(x), map(lambda x: x.strip(), f.readlines()))
        ):
            db.collection("admins").document(x).set({"registered": False})
    for doc in db.collection("groups").list_documents():
        doc.delete()
    for doc in db.collection("users").list_documents():
        doc.delete()
    with open("gls.json") as f:
        gl = json.loads(f.read())
        for key in gl:
            db.collection("groups").document(key).set({"name": key})
            group_ref = db.collection("groups").document(key)
            for user in gl[key]:
                db.collection("users").document(user).set(
                    {"registered": False, "group": group_ref}
                )
    for doc in db.collection("challenges").list_documents():
        doc.delete()
    for doc in db.collection("bonus").list_documents():
        doc.delete()
    with open("challenges.json") as f:
        challs = json.loads(f.read())
        standard_challs = challs["standard"]
        for key in standard_challs:
            db.collection("challenges").document(key).set(standard_challs[key])
        db.collection("challenges").document("bonus").set(challs["bonus"])
        db.collection("bonus").document("current").set(
            {"idx": -1, "completed": [-1 for _ in range(MAX_BONUS_GROUPS)]}
        )
    for doc in db.collection("approvals").list_documents():
        doc.delete()
    db.collection("approvals").document("placeholder").set({})


def set_broadcast_group(username: str, chatid: int):
    get_user_group(username).update({"broadcast_channel": chatid})


def get_admin_broadcast() -> int:
    global broadcast_channel

    if broadcast_channel:
        return broadcast_channel

    res = db.collection("admins").document("_globals").get().to_dict()
    broadcast_channel = (res.get("broadcast"), res.get("broadcast_thread"))
    return broadcast_channel


def register_user(username: str, userid: int):
    ref = db.collection("users").document(username)
    if not ref.get().exists:
        return False
    ref.update({"registered": True})
    set_broadcast_group(username, userid)
    return True


def register_admin(username: str):
    db.collection("admins").document(username).update({"registered": True})


def get_user_group(username: str) -> firestore.firestore.DocumentReference:
    if username in group_cache:
        return group_cache[username]
    group_cache[username] = (
        db.collection("users").document(username).get().to_dict()["group"]
    )
    return group_cache[username]


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


def recent_location_update(username: str) -> bool:
    user = db.collection("users").document(username).get().to_dict()
    try:
        return (
            user["location"]
            and (
                datetime.datetime.now(datetime.timezone.utc) - user["last_update"]
            ).total_seconds()
            < RECENT_LOCATION_MAX_TIME
        )
    except KeyError:
        return False


def get_location(username: str) -> bool:
    user = db.collection("users").document(username).get().to_dict()
    try:
        return user["location"]
    except KeyError:
        return None


def has_race_started(username: str) -> bool:
    try:
        return bool(get_user_group(username).get().to_dict()["start_time"])
    except KeyError:
        return False


def has_race_ended(username: str) -> bool:
    try:
        return bool(get_user_group(username).get().to_dict()["race_completed"])
    except KeyError:
        return False


def get_start_chall_index(direction: Direction) -> int:
    if direction == Direction.A0:
        return 1
    if direction == Direction.B0:
        return NUMBER_LOCATIONS
    return 0


def start_race(username: str, direction: Direction) -> dict | None:
    group_ref = get_user_group(username)
    group_ref.update(
        {
            "start_time": firestore.firestore.SERVER_TIMESTAMP,
            "current_location": get_start_chall_index(direction),
            "challenges_completed": [],
            "direction": str(direction),
            "race_completed": False,
            "bonus_completed": 0,
            "challenges_skipped": 0,
        }
    )
    return group_ref.get().to_dict()


def end_race(username: str) -> tuple[datetime.datetime]:
    group_ref = get_user_group(username)
    group_ref.update({"end_time": firestore.firestore.SERVER_TIMESTAMP})
    data = group_ref.get().to_dict()
    return data["start_time"], data["end_time"]


def get_current_challenge(username: str) -> tuple[str | dict]:
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
        challs = doc.to_dict()["challenges"]
        return (
            group,
            doc.id,
            list(
                filter(
                    lambda iv: iv[0] not in group["challenges_completed"],
                    enumerate(challs),
                )
            ),
        )


def next_location(
    username: str,
) -> tuple[dict | str | dict] | None:
    group_ref = get_user_group(username)
    group = group_ref.get().to_dict()
    direction = Direction[group["direction"]]

    new_location_index = group["current_location"] + (
        1 if (direction == Direction.A1 or direction == Direction.A0) else -1
    )

    if new_location_index < 0:
        new_location_index = NUMBER_LOCATIONS
    elif new_location_index > NUMBER_LOCATIONS:
        new_location_index = 0

    race_completed = new_location_index == get_start_chall_index(
        direction
    )  # Loop completed

    group_ref.update(
        {
            "current_location": new_location_index,
            "challenges_completed": [],
            "race_completed": race_completed,
        }
    )

    return (group, None, None) if race_completed else get_current_challenge(username)


def get_challenge(location: str):
    if not location in challenge_cache:
        challenge_cache[location] = (
            db.collection("challenges").document(location).get().to_dict()
        )
    return challenge_cache[location]


def get_current_step(
    location: str, challenge_num: int, step_number: int
) -> dict | None:
    try:
        doc = get_challenge(location)
        return doc["challenges"][challenge_num]["steps"][step_number]
    except IndexError:
        return None


def complete_challenge(username: str, location: str, chall_num: int) -> bool:
    group_ref = get_user_group(username)
    if location == "bonus":
        db.collection("bonus").document("current").update(
            {"completed": firestore.firestore.ArrayUnion([group_ref.id])}
        )
        group_ref.update({"bonus_completed": firestore.firestore.Increment(1)})
        return 9999
    group_ref.update(
        {"challenges_completed": firestore.firestore.ArrayUnion([chall_num])}
    )
    return len(get_challenge(location)["challenges"]) - len(
        group_ref.get().to_dict()["challenges_completed"]
    )


def skip_challenge(username: str, location: str, chall_num: int) -> bool:
    group_ref = get_user_group(username)
    group_ref.update({"challenges_skipped": firestore.firestore.Increment(1)})
    return complete_challenge(username, location, chall_num)


def generate_approval_request() -> str:
    update_time, doc = db.collection("approvals").add(
        {"status": False, "approved": False}
    )
    return doc.id


async def wait_approval(id: str, timeout: int):
    output = {"status": False}
    listener = None

    task_completed_event = asyncio.Event()

    def update_status(doc_snapshot, changes, read_time):
        status = doc_snapshot[0].to_dict()
        if status["status"]:
            try:
                if listener:
                    listener.unsubscribe()
            except RuntimeError:
                pass
            db.collection("approvals").document(id).delete()
            output.update(status)
            if output.get("status"):
                task_completed_event.set()

    listener = db.collection("approvals").document(id).on_snapshot(update_status)

    try:
        await asyncio.wait_for(task_completed_event.wait(), timeout)
    except TimeoutError:
        try:
            db.collection("approvals").document(id).delete()
        except RuntimeError:
            pass
        raise TimeoutError

    return output.get("approved"), output.get("approver")


def update_approval(id: str, approved: bool, username: str):
    db.collection("approvals").document(id).update(
        {"status": True, "approved": approved, "approver": username}
    )


def get_current_bonus_challenge() -> dict:
    bonus = db.collection("bonus").document("current").get().to_dict()
    idx = bonus.get("idx")
    if len(bonus.get("completed")) == MAX_BONUS_GROUPS:
        idx += 1
        if idx != 0:
            logger.info(
                f"Moving next bonus challenge. Previous bonus challenge complete: {bonus.get('completed')}"
            )
        db.collection("bonus").document("current").set({"idx": idx, "completed": []})
    bonus_challs = (
        db.collection("challenges").document("bonus").get().to_dict()["challenges"]
    )
    if len(bonus_challs) == idx:
        return None
    return bonus_challs[idx]


def get_number_solved_bonus() -> dict:
    return len(
        db.collection("bonus").document("current").get().to_dict().get("completed")
    )


def has_active_bonus_challenge(username: str, bonus=None) -> dict:
    if bonus == None:
        bonus = db.collection("bonus").document("current").get().to_dict()

    if len(bonus.get("completed")) < MAX_BONUS_GROUPS and not get_user_group(
        username
    ).id in bonus.get("completed"):
        return bonus.get("idx")
    return None


def get_active_bonus_challenge(username: str) -> dict:
    bonus = db.collection("bonus").document("current").get().to_dict()
    if not has_active_bonus_challenge(username, bonus):
        return None
    return (
        db.collection("challenges")
        .document("bonus")
        .get()
        .to_dict()["challenges"][bonus.get("idx")]
    )


def get_all_group_broadcast() -> list[int]:
    result = []
    for doc in db.collection("groups").list_documents():
        data = doc.get().to_dict()
        if "broadcast_channel" in data:
            result.append(data["broadcast_channel"])
    return result
