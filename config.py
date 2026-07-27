import streamlit as st
import json
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    try:
        # Megnézzük, hogy létezik-e a gcp_json a secrets-ben
        if "gcp_json" in st.secrets:
            raw_gcp = st.secrets["gcp_json"]
            
            # Ha a Streamlit már szótárként adta át
            if isinstance(raw_gcp, dict):
                info = raw_gcp
            # Ha szöveges/JSON formátumú stringként érkezett
            elif isinstance(raw_gcp, str):
                info = json.loads(raw_gcp)
            else:
                # Ha valamilyen Streamlit Secret proxy objektum
                info = dict(raw_gcp)
                
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
        else:
            st.error("Nincs megfelelő adatbázis konfiguráció a Secrets-ben!")
            return None

        # A privát kulcsban lévő escaped sorjelek kezelése
        if "private_key" in info and info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
