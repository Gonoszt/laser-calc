import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    try:
        pwd = st.secrets["ADMIN_PASSWORD"]
        return str(pwd).strip()
    except Exception as e:
        return "alapertelmezett_vedelem"

def get_db_client():
    try:
        if "firestore" not in st.secrets:
            st.error("HIBA: A 'firestore' kulcs hiányzik a Streamlit Secrets-ből!")
            return None

        info = {
            "type": st.secrets["firestore"].get("type", "service_account"),
            "project_id": st.secrets["firestore"].get("project_id"),
            "private_key_id": st.secrets["firestore"].get("private_key_id"),
            "private_key": st.secrets["firestore"].get("private_key"),
            "client_email": st.secrets["firestore"].get("client_email"),
            "client_id": st.secrets["firestore"].get("client_id"),
            "auth_uri": st.secrets["firestore"].get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": st.secrets["firestore"].get("token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": st.secrets["firestore"].get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": st.secrets["firestore"].get("client_x509_cert_url"),
            "universe_domain": st.secrets["firestore"].get("universe_domain", "googleapis.com")
        }

        credentials = service_account.Credentials.from_service_account_info(info)
        db = firestore.Client(credentials=credentials)

        # 🔥 IDE KELL TENNI A DIAGNOSZTIKÁT
        st.write("DB client:", db)

        return db

    except Exception as e:
        st.error(f"Részletes kapcsolódási hiba a config.py-ban: {e}")
        return None
