import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    try:
        pwd = st.secrets["ADMIN_PASSWORD"]
        return str(pwd).strip()
    except Exception as e:
        st.sidebar.warning(f"Secrets olvasási hiba: {e}")
        return "alapertelmezett_vedelem"

def get_db_client():
    try:
        # Összeállítjuk a hitelesítő szótárat a Streamlit Secrets natív mezőiből
        info = {
            "type": st.secrets.get("type", "service_account"),
            "project_id": st.secrets.get("project_id"),
            "private_key_id": st.secrets.get("private_key_id"),
            "private_key": st.secrets.get("private_key"),
            "client_email": st.secrets.get("client_email"),
            "client_id": st.secrets.get("client_id"),
            "auth_uri": st.secrets.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": st.secrets.get("token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": st.secrets.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": st.secrets.get("client_x509_cert_url"),
            "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
        }

        if not info["project_id"] or not info["client_email"] or not info["private_key"]:
            return None

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception:
        return None
