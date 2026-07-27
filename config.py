import streamlit as st
import json
from google.cloud import firestore
from google.oauth2 import service_account

def get_admin_password():
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")

def get_db_client():
    try:
        # Ellenőrizzük, hogy létezik-e a gcp_json a secrets-ben
        if "gcp_json" in st.secrets:
            raw_gcp = st.secrets["gcp_json"]
            
            # Ha a Streamlit már dict-ként értelmezte
            if isinstance(raw_gcp, dict):
                info = raw_gcp
            # Ha stringként érkezett be
            else:
                info = json.loads(str(raw_gcp))
        else:
            st.error("A 'gcp_json' hiányzik a Streamlit Secrets-ből!")
            return None

        # Biztosítjuk a privát kulcs helyes sorszüneteit
        if "private_key" in info and info["private_key"]:
            # Ha esetleg dupla vagy szimpla \\n maradt benne, normalizáljuk
            info["private_key"] = info["private_key"].replace("\\n", "\n")

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
        
    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
