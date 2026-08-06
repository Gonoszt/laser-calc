import streamlit as st
from firebase_admin import credentials, firestore, initialize_app, get_app


@st.cache_resource
def get_db_client():
    """
    Firestore kliens inicializálása.
    @st.cache_resource biztosítja, hogy ez CSAK EGYSZER fusson le
    az app teljes életciklusa alatt (minden felhasználó ugyanazt a
    kapcsolatot használja), és megvédi a firebase_admin-t az
    "app already exists" hibától reruns / több session esetén.
    """
    try:
        try:
            app = get_app()
        except ValueError:
            cred = credentials.Certificate(st.secrets["firestore"])
            app = initialize_app(cred)
        return firestore.client(app)
    except Exception as e:
        st.sidebar.warning(f"Firestore kapcsolódási hiba: {e}")
        return None


@st.cache_data(ttl=3600)
def get_admin_password():
    try:
        pwd = st.secrets["ADMIN_PASSWORD"]
        return str(pwd).strip()
    except Exception as e:
        st.sidebar.warning(f"Secrets olvasási hiba: {e}")
        return "alapertelmezett_vedelem"
