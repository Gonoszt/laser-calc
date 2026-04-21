import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account

# SVG elemzéshez szükséges könyvtár
try:
    from svgpathtools import svg2paths
except ImportError:
    st.error("Hiányzó csomag! A requirements.txt-be írd bele: svgpathtools")

# --- ADATBÁZIS KAPCSOLAT (Firestore) ---
def get_db_client():
    if "gcp_service_account" in st.secrets:
        info = json.loads(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials)
    try:
        return firestore.Client.from_service_account_json("firebase_kulcs.json")
    except:
        return None

db = get_db_client()

# --- BEÁLLÍTÁSOK KEZELÉSE ---
def load_all_settings():
    defaults = {
        "Kis Lézer": {"lazer": 0.8, "material": 0.005, "power": 4.6, "work": 25.0, "magnet": 150.0, "paint": 0.002},
        "Nagy Lézer": {"lazer": 1.5, "material": 0.005, "power": 5.5, "work": 25.0, "magnet": 0.0, "paint": 0.0},
        "3D Nyomtatás": {"lazer": 0.0, "material": 15.0, "power": 1.2, "work": 25.0, "magnet": 0.0, "paint": 0.0}
    }
    if db:
        try:
            doc = db.collection("beallitasok").document("gepek").get()
            if doc.exists:
                return doc.to_dict()
        except: pass
    return defaults

def save_gep_setting(gep_nev, adatok):
    if db:
        db.collection("beallitasok").document("gepek").set({gep_nev: adatok}, merge=True)

st.set_page_config(page_title="Melus & SK Profi Kalkulátor", layout="wide")
all_settings = load_all_settings()

# --- MENÜ ---
st.sidebar.title("Műhely Vezérlő")
page = st.sidebar.radio("Válassz:", ["Költség Kalkulátor", "SVG Időbecslő", "Archívum"])

# --- 1. OLDAL: KÖLTSÉG KALKULÁTOR ---
if page == "Költség Kalkulátor":
    st.title("🧮 Gyártási Költség Kalkulátor")
    tabs = st.tabs(["Kis Lézer", "Nagy Lézer", "3D Nyomtatás"])

    def render_laser_tab(gep_nev, tab_obj, key_s):
        with tab_obj:
            # Beállítások bővítése
            with st.expander(f"⚙️ Alapárak szerkesztése ({gep_nev})"):
                c1, c2, c3 = st.columns(3)
                l_val = c1.number_input("Lézer amort. (Ft/p)", value=float(all_settings[gep_nev]["lazer"]), key=f"l{key_s}")
                m_val = c2.number_input("Anyag (Ft/mm²)", value=float(all_settings[gep_nev]["material"]), format="%.5f", key=f"m{key_s}")
                p_val = c3.number_input("Áram (Ft/p)", value=float(all_settings[gep_nev]["power"]), key=f"pw{key_s}")
                if st.button(f"Mentés felhőbe ({gep_nev})", key=f"b{key_s}"):
                    save_gep_setting(gep_nev, {"lazer": l_val, "material": m_val, "power": p_val, "work": 25.0, "magnet": 0.0, "paint": 0.0})
                    st.success("Minden eszközön frissítve!")

            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                t_name = st.text_input("Termék megnevezése", key=f"tn{key_s}")
                width_mm = st.number_input("Szélesség (mm)", value=100.0, key=f"w{key_s}")
                height_mm = st.number_input("Magasság (mm)", value=100.0, key=f"h{key_s}")
                work_time = st.number_input("Munkaidő (perc)", value=5.0, key=f"t{key_s}")
            with col_b:
                pcs = st.number_input("Hány darab jön ki a táblából?", min_value=1, value=1, key=f"pc{key_s}")
            
            # Kalkuláció (10% felárral)
            base_cost = (m_val * width_mm * height_mm) + ((l_val + p_val + 25.0) * work_time)
            final_cost = base_cost * 1.10
            unit_price = final_cost / pcs

            st.subheader(f"💰 Becsült darabár: {round(unit_price)} Ft")
            
            if st.button("💾 Mentés az Archívumba", key=f"s{key_s}", use_container_width=True):
                if db and t_name:
                    db.collection("kalkulaciok").add({
                        "datum": datetime.now(), "gep": gep_nev, "termek": t_name, "ar": round(unit_price)
                    })
                    st.success("Tétel elmentve!")

    render_laser_tab("Kis Lézer", tabs[0], "kis")
    render_laser_tab("Nagy Lézer", tabs[1], "nagy")

# --- 2. OLDAL: SVG IDŐBECSLŐ ---
elif page == "SVG Időbecslő":
    st.title("⏱️ SVG Időbecslő (DPI alapú)")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        v_raster = st.number_input("Fekete sebesség (Raszter) [mm/s]", value=300)
        dpi = st.number_input("Felbontás (DPI)", value=254, help="254 DPI = 0.1mm sorköz")
        # Átszámítás mm-re a matekhoz
        scan_gap_mm = 25.4 / dpi if dpi > 0 else 0.1
        st.caption(f"Kalkulált sorköz: {round(scan_gap_mm, 4)} mm")
        
        st.divider()
        v_blue = st.number_input("Kék sebesség (Vektor) [mm/s]", value=25)
        v_red = st.number_input("Piros sebesség (Vektor) [mm/s]", value=20)
        
        uploaded_file = st.file_uploader("Válassz SVG fájlt", type=["svg"])

    with col2:
        if uploaded_file:
            svg_raw = uploaded_file.getvalue().decode("utf-8")
            
            # Méretarány (Scaling) meghatározása
            scaling = 1.0
            try:
                w_match = re.search(r'width="([\d\.]+)(mm|cm|px|pt)?"', svg_raw)
                vb_match = re.search(r'viewBox="[\d\.]+\s+[\d\.]+\s+([\d\.]+)', svg_raw)
                if w_match and vb_match:
                    p_w = float(w_match.group(1))
                    unit = w_match.group(2)
                    if unit == 'cm': p_w *= 10
                    elif unit == 'pt': p_w *= 0.3527
                    scaling = p_w / float(vb_match.group(1))
                    st.caption(f"📏 Automatikus skálázás: {round(scaling, 4)}x")
            except: pass

            # Corel CSS stílusok
            css_map = {}
            styles = re.findall(r'\.([\w\d]+)\s*\{([^}]+)\}', svg_raw)
            for c_name, props in styles:
                css_map[c_name.lower()] = props.lower()

            with open("temp.svg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                paths, attributes = svg2paths("temp.svg")
                b_len, r_len, t_rast = 0.0, 0.0, 0.0

                for path, attr in zip(paths, attributes):
                    o_cls = attr.get('class', '').lower()
                    o_str = attr.get('stroke', '').lower()
                    o_fil = attr.get('fill', '').lower()
                    
                    all_p = f"{o_str} {o_fil} "
                    if o_cls:
                        for c in o_cls.split():
                            all_p += css_map.get(c, "") + " "

                    r_len_path = path.length() * scaling

                    if any(c in all_p for c in ['blue', '#0000ff', '0,0,255']):
                        b_len += r_len_path
                    elif any(c in all_p for c in ['red', '#ff0000', '255,0,0']):
                        r_len += r_len_path
                    elif any(c in all_p for c in ['black', '#000000', '0,0,0']) and 'fill:none' not in all_p:
                        try:
                            xmin, xmax, ymin, ymax = path.bbox()
                            w, h = (xmax - xmin) * scaling, (ymax - ymin) * scaling
                            over = (v_raster * 0.05)
                            lines = h / scan_gap_mm
                            t_rast += (lines * (w + (2 * over)) / v_raster) / 60
                        except: pass

                t_b = (b_len / v_blue) * 1.15 / 60 if v_blue > 0 else 0
                t_r = (r_len / v_red) * 1.15 / 60 if v_red > 0 else 0
                total = t_b + t_r + t_rast

                st.success(f"✅ Becsült idő: {round(total, 2)} perc")
                st.metric("Összesen", f"{round(total, 2)} p")
                st.text_area("Vágólapra:", value=str(round(total, 2)))
                
                c1, c2, c3 = st.columns(3)
                c1.write(f"Kék: {round(b_len)}mm")
                c2.write(f"Piros: {round(r_len)}mm")
                c3.write(f"Raszter: {round(t_rast, 2)}p")
            except Exception as e:
                st.error(f"Hiba: {e}")

# --- 3. OLDAL: ARCHÍVUM ---
elif page == "Archívum":
    st.title("📁 Felhő alapú Archívum")
    if db:
        docs = db.collection("kalkulaciok").order_by("datum", direction=firestore.Query.DESCENDING).limit(50).stream()
        res = []
        for d in docs:
            v = d.to_dict()
            res.append([v['datum'].strftime("%Y-%m-%d %H:%M"), v['gep'], v['termek'], f"{v['ar']} Ft"])
        if res:
            st.table(pd.DataFrame(res, columns=["Dátum", "Gép", "Termék", "Darabár"]))
        else:
            st.info("Még nincs mentett adat.")
