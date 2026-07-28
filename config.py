import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account


def get_admin_password():
    # Admin jelszó a Streamlit Secrets-ben: ADMIN_PASSWORD
    return st.secrets.get("ADMIN_PASSWORD", "alapertelmezett_vedelem")


def get_db_client():
    """
    Firestore kliens létrehozása.
    - Ha hiányzik bármelyik kötelező kulcs, visszatér None-nal.
    - Ha a private_key \n-ekkel van tárolva, visszaalakítjuk valódi sortörésre.
    """

    try:
        # Kötelező kulcsok ellenőrzése
        required_keys = ["project_id", "private_key", "client_email"]
        missing = [k for k in required_keys if not st.secrets.get(k)]

        if missing:
            st.warning(
                "Firestore beállítás hiányzik a Streamlit Secrets-ben: "
                + ", ".join(missing)
            )
            return None

        # Private key sortörések javítása
        raw_private_key = st.secrets["private_key"]
        fixed_private_key = raw_private_key.replace("\\n", "\n")

        info = {
            "type": st.secrets.get("type", "service_account"),
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets.get("private_key_id"),
            "private_key": fixed_private_key,
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets.get("client_id"),
            "auth_uri": st.secrets.get(
                "auth_uri", "https://accounts.google.com/o/oauth2/auth"
            ),
            "token_uri": st.secrets.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            ),
            "auth_provider_x509_cert_url": st.secrets.get(
                "auth_provider_x509_cert_url",
                "https://www.googleapis.com/oauth2/v1/certs",
            ),
            "client_x509_cert_url": st.secrets.get("client_x509_cert_url"),
            "universe_domain": st.secrets.get("universe_domain", "googleapis.com"),
        }

        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)

    except Exception as e:
        st.error(f"Firestore kapcsolódási hiba: {e}")
        return None
