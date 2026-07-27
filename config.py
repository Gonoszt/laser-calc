import streamlit as st
import json
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    try:
        info = None
        
        # 1. Megpróbáljuk kinyerni a gcp_json-t, ha létezik
        if "gcp_json" in st.secrets:
            raw_gcp = st.secrets["gcp_json"]
            if isinstance(raw_gcp, dict):
                info = dict(raw_gcp)
            elif isinstance(raw_gcp, str):
                info = json.loads(raw_gcp)
            else:
                # Ha esetleg AttrDict vagy más Streamlit speciális típus
                info = json.loads(json.dumps(dict(raw_gcp)))
                
        # 2. Ha külön mezőkként vannak megadva a Secrets-ben
        elif "project_id" in st.secrets:
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
        
        if not info:
            st.error("Nincs adatbázis konfiguráció a Streamlit Secrets-ben!")
            return None

        # Privát kulcs sorszüneteinek helyreállítása
        if "private_key" in info and info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
