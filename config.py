import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    try:
        pwd = st.secrets["ADMIN_PASSWORD"]
        return str(pwd).strip()
    except Exception:
        return "alapertelmezett_vedelem"

def get_db_client():
    try:
        if "firestore" not in st.secrets:
            st.error("HIBA: A 'firestore' kulcs hiányzik a Streamlit Secrets-ből!")
            return None

        info = {
            "type": st.secrets["firestore"]["type"],
            "project_id": st.secrets["firestore"]["project_id"],
            "private_key_id": st.secrets["firestore"]["private_key_id"],
            "private_key": st.secrets["firestore"]["private_key"],
            "client_email": st.secrets["firestore"]["client_email"],
            "client_id": st.secrets["firestore"]["client_id"],
            "auth_uri": st.secrets["firestore"]["auth_uri"],
            "token_uri": st.secrets["firestore"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firestore"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firestore"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firestore"]["universe_domain"],
        }

        credentials = service_account.Credentials.from_service_account_info(info)
        db = firestore.Client(credentials=credentials, project=info["project_id"])

        # 🔥 Diagnosztika – ezt látod majd a Streamlit tetején
        st.write("DB client:", db)

        return db

    except Exception as e:
        st.error(f"Részletes kapcsolódási hiba a config.py-ban: {e}")
        return None
