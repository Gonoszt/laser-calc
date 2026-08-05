import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import base64

def get_db_client():
    try:
        if "firestore" not in st.secrets:
            st.error("HIBA: A 'firestore' kulcs hiányzik a Streamlit Secrets-ből!")
            return None

        # BASE64-ből visszaalakítás
        private_key_raw = base64.b64decode(st.secrets["firestore"]["private_key_b64"]).decode("utf-8")

        info = {
            "type": st.secrets["firestore"]["type"],
            "project_id": st.secrets["firestore"]["project_id"],
            "private_key_id": st.secrets["firestore"]["private_key_id"],
            "private_key": private_key_raw,
            "client_email": st.secrets["firestore"]["client_email"],
            "client_id": st.secrets["firestore"]["client_id"],
            "auth_uri": st.secrets["firestore"]["auth_uri"],
            "token_uri": st.secrets["firestore"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firestore"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firestore"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firestore"]["universe_domain"],
        }

        credentials = service_account.Credentials.from_service_account_info(info)
        db = firestore.Client(project=info["project_id"], credentials=credentials)

        st.write("DB client:", db)

        return db

    except Exception as e:
        st.error(f"Hiba a Firestore kapcsolódásnál: {e}")
        return None
