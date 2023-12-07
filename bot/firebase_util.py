import os
import json
import datetime
import firebase_admin
from constants import Role
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
        for idx, x in enumerate(list(filter(lambda x: len(x), f.readlines()))):
            db.collection("groups").document(f"{idx + 1}").set({"name": x})
    with open("admins.txt") as f:
        for x in list(filter(lambda x: len(x), f.readlines())):
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


def get_role(username: str) -> Role:
    user = db.collection("users").document(username).get()
    if user.exists and user.to_dict()["registered"]:
        return Role.GL
    admin = db.collection("admins").document(username).get()
    if admin.exists and admin.to_dict()["registered"]:
        return Role.Admin
    return Role.Unregistered


def set_location(username, lat, lng):
    db.collection("users").document(username).update(
        {
            "location": firestore.firestore.GeoPoint(lat, lng),
            "last_update": firestore.SERVER_TIMESTAMP,
        }
    )


# last 5 minutes
def recent_location_update(username) -> bool:
    user = db.collection("users").document(username).get().to_dict()
    return (
        user["location"]
        and (
            datetime.datetime.now(datetime.timezone.utc) - user["last_update"]
        ).total_seconds()
        < 300
    )


def register_admin(username: str) -> Role:
    db.collection("admins").document(username).update({"registered": True})


def register_user(username: str) -> Role:
    db.collection("users").document(username).update({"registered": True})
