import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firestore inicializálás ---
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["firestore"])
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Admin jelszó ellenőrzés ---
st.title("Laser Kalkulátor 2026")

if "admin_ok" not in st.session_state:
    st.session_state["admin_ok"] = False

if not st.session_state["admin_ok"]:
    pw = st.text_input("Admin jelszó:", type="password")
    if pw == st.secrets["ADMIN_PASSWORD"]:
        st.session_state["admin_ok"] = True
        st.success("Admin mód aktiválva.")
    else:
        st.info("Add meg az admin jelszót a beállításokhoz.")
        st.stop()
# --- Gépértékek Firestore-ból ---
def load_machine_values():
    doc_ref = db.collection("gepek").document("alapertelmezett")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return {
            "teljesitmeny": 40,
            "fogyasztas": 0.12,
            "oradij": 3500,
            "karbantartas": 0.05,
            "amortizacio": 0.03
        }

gep = load_machine_values()

st.subheader("Gépértékek")
st.write(gep)
# --- Gépértékek mentése Firestore-ba ---
st.subheader("Gépértékek módosítása")

teljesitmeny = st.number_input("Teljesítmény (W)", value=gep["teljesitmeny"])
fogyasztas = st.number_input("Fogyasztás (kWh)", value=gep["fogyasztas"])
oradij = st.number_input("Óradíj (Ft)", value=gep["oradij"])
karbantartas = st.number_input("Karbantartás (%)", value=gep["karbantartas"])
amortizacio = st.number_input("Amortizáció (%)", value=gep["amortizacio"])

if st.button("Gépértékek mentése"):
    db.collection("gepek").document("alapertelmezett").set({
        "teljesitmeny": teljesitmeny,
        "fogyasztas": fogyasztas,
        "oradij": oradij,
        "karbantartas": karbantartas,
        "amortizacio": amortizacio
    })
    st.success("Gépértékek mentve Firestore-ba.")
# --- Kalkulátor ---
st.header("Termék kalkuláció")

ido = st.number_input("Vágási idő (perc)", min_value=1, value=5)
anyag_ar = st.number_input("Anyagköltség (Ft)", min_value=0, value=200)
darabszam = st.number_input("Darabszám", min_value=1, value=1)

koltseg = (
    (gep["teljesitmeny"] / 1000) * gep["fogyasztas"] * (ido / 60) * 52 +
    (gep["oradij"] * (ido / 60)) +
    (anyag_ar * darabszam)
)

ajanlott = koltseg * 1.15

st.write(f"**Teljes költség:** {koltseg:.0f} Ft")
st.write(f"**Ajánlott ár:** {ajanlott:.0f} Ft")
# --- Termék mentése Firestore-ba ---
st.subheader("Termék mentése Firestore-ba")

termek_nev = st.text_input("Termék neve")

if st.button("Mentés"):
    db.collection("termekek").add({
        "nev": termek_nev,
        "koltseg": koltseg,
        "ajanlott": ajanlott,
        "ido": ido,
        "anyag_ar": anyag_ar,
        "darabszam": darabszam
    })
    st.success("Termék mentve Firestore-ba.")
