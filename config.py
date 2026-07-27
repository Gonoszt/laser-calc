import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    try:
        # Ha a gcp_json teljes egésze szótárként vagy TOML táblaként érkezik be
        if "gcp_json" in st.secrets:
            info = dict(st.secrets["gcp_json"])
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
            st.error("Nincs adatbázis konfiguráció a Secrets-ben!")
            return None

        # Privát kulcs sorszüneteinek helyreállítása, ha szükséges
        if "private_key" in info and info["private_key"]:
            info["private_key"] = info["private_key"].replace("\\n", "\n")

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
