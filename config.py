import streamlit as st
from firebase_admin import credentials, firestore, initialize_app

_db = None

def get_db_client():
    global _db
    if _db is None:
        try:
            cred = credentials.Certificate(st.secrets["firestore"])
            initialize_app(cred)
            _db = firestore.client()
        except Exception:
            return None
    return _db

def get_admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return None
