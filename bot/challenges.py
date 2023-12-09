import firebase_util


def get_current_challenge(username: str):
    return firebase_util.get_current_challenge(username)
