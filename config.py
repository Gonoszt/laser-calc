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

import streamlit as st

def get_admin_password():
    try:
        # Kiolvassuk a secret-et
        pwd = st.secrets["ADMIN_PASSWORD"]
        return str(pwd).strip()
    except Exception as e:
        # Ha hibát dob, jelezzük a felületen, hogy miért nem éri el
        st.sidebar.warning(f"Secrets olvasási hiba: {e}")
        return "alapertelmezett_vedelem"
