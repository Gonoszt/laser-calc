import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    if "project_id" in st.secrets:
        try:
            info = {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key_id": st.secrets["private_key_id"],
                "private_key": st.secrets["private_key"],
                "client_email": st.secrets["client_email"],
                "client_id": st.secrets["client_id"],
                "auth_uri": st.secrets["auth_uri"],
                "token_uri": st.secrets["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["client_x509_cert_url"],
                "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
            }
            credentials = service_account.Credentials.from_service_account_info(info)
            return firestore.Client(credentials=credentials)
        except Exception as e:
            st.error(f"Firestore kapcsolódási hiba: {e}")
            return None
    return None
