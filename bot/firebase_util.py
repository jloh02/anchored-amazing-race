import os
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

db = None
app = None

def init():
  global app, db

  cred = credentials.Certificate(os.environ.get("SERVICE_ACCOUNT_PATH"))
  app = firebase_admin.initialize_app(cred)
  db = firestore.client()


def read():
  users_ref = db.collection("users")  
  print(users_ref.get()[0].to_dict())