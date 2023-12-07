import os
import json
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


def get_role(username: str) -> Role:
    if db.collection("admins").document(username).get().exists:
        return Role.Admin
    if not db.collection("users").document(username).get().exists:
        return Role.Unregistered
    return Role.GL


def register_admin(username: str) -> Role:
    db.collection("admins").document(username).update({"registered": True})


def register_user(username: str) -> Role:
    db.collection("users").document(username).update({"registered": True})
