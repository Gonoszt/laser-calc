import streamlit as st
import json
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    # Megnézzük, hogy a gcp_json-t vagy a darabolt mezőket használjuk-e
    try:
        if "gcp_json" in st.secrets:
            raw_json = st.secrets["gcp_json"]
            info = dict(raw_json) if hasattr(raw_json, "items") else json.loads(raw_json)
        elif "project_id" in st.secrets:
            # Ha külön mezőkként vannak benne, gyűjtsük össze szótárba
            info = {
                "type": st.secrets.get("type"),
                "project_id": st.secrets.get("project_id"),
                "private_key_id": st.secrets.get("private_key_id"),
                "private_key": st.secrets.get("private_key"),
                "client_email": st.secrets.get("client_email"),
                "client_id": st.secrets.get("client_id"),
                "auth_uri": st.secrets.get("auth_uri"),
                "token_uri": st.secrets.get("token_uri"),
                "auth_provider_x509_cert_url": st.secrets.get("auth_provider_x509_cert_url"),
                "client_x509_cert_url": st.secrets.get("client_x509_cert_url"),
                "universe_domain": st.secrets.get("universe_domain", "googleapis.com")
            }
        else:
            return None

        # Ha a privát kulcsban escaped \n karakterek vannak, valódi sortöréssé alakítjuk
        if "private_key" in info and info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
