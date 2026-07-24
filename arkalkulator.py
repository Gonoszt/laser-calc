import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account

# --- SVG elemzéshez szükséges könyvtár ---
try:
    from svgpathtools import svg2paths
except ImportError:
    st.error("Hiányzó csomag! A requirements.txt-be írd bele: svgpathtools")

# --- ADATBÁZIS KAPCSOLAT (Firestore) ---
def get_db_client():
    if "gcp_service_account" in st.secrets:
        try:
            info = json.loads(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(info)
            return firestore.Client(credentials=credentials)
        except Exception as e:
            st.error(f"Firestore hiba: {e}")
            return None
    try:
        return firestore.Client.from_service_account_json("firebase_kulcs.json")
    except:
        return None

db = get_db_client()

st.set_page_config(page_title="Melis & SK Profi Kalkulátor", layout="wide")

# --- ADMIN JELSZÓ KEZELÉSE (Session State) ---
ADMIN_PASSWORD = "titkosjelszo_helye" # Cseréld le a kívánt admin jelszóra!

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
        except Exception:
            pass
    return defaults

def save_gep_setting(gep_nev, adatok):
    if db:
        db.collection("beallitasok").document("gepek").set({gep_nev: adatok}, merge=True)

all_settings = load_all_settings()

# --- URL PARAMÉTEREK FIGYELÉSE (Idő átvétel az SVG kalkulátorból) ---
query_params = st.query_params
default_gtime = 5.0
if "gtime" in query_params:
    try:
        default_gtime = float(query_params["gtime"])
    except:
        pass

# --- MENÜ ÉS ADMIN VEZÉRLÉS AZ OLDALSÁVBAN ---
st.sidebar.title("Műhely Vezérlő")
page = st.sidebar.radio("Választó:", ["Költség Kalkulátor", "SVG Időbecslő", "Archívum"])

st.sidebar.divider()
st.sidebar.subheader("🔒 Adminisztráció")
if not st.session_state.logged_in:
    passw = st.sidebar.text_input("Admin jelszó", type="password")
    if st.sidebar.button("Bejelentkezés"):
        if passw == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.success("Sikeres bejelentkezés!")
            st.rerun()
        else:
            st.error("Hibás jelszó!")
else:
    st.sidebar.success("Admin mód aktív ✅")
    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.rerun()

# --- 1. OLDAL: KALKULÁTOR ---
if page == "Költség Kalkulátor":
    st.title("🧮 Részletes Költség Kalkulátor")
    tabs = st.tabs(["Kis Lézer", "Nagy Lézer", "3D Nyomtatás"])

    def render_calc_tab(gep_nev, tab_obj, key_s):
        with tab_obj:
            current_gep_data = all_settings.get(gep_nev, {})
            
            # Alapárak szerkesztése - CSAK ADMINNAK
            with st.expander(f"⚙️ Alapárak és rezsi szerkesztése ({gep_nev}) - (Csak admin)"):
                if st.session_state.logged_in:
                    c1, c2, c3 = st.columns(3)
                    l_val = c1.number_input("Lézer amort. (Ft/p)", value=float(current_gep_data.get("lazer", 0.0)), key=f"l{key_s}", format="%.3f")
                    m_val = c2.number_input("Anyag alapár (Ft/mm²)", value=float(current_gep_data.get("material", 0.006)), format="%.5f", key=f"m{key_s}")
                    p_val = c3.number_input("Áram (Ft/p)", value=float(current_gep_data.get("power", 0.0)), key=f"pw{key_s}")
                    
                    c4, c5, c6 = st.columns(3)
                    w_val = c4.number_input("Munkadíj (Ft/p)", value=float(current_gep_data.get("work", 25.0)), key=f"w{key_s}")
                    mag_val = c5.number_input("Mágnes ára (Ft/db)", value=float(current_gep_data.get("magnet", 0.0)), key=f"mag{key_s}")
                    pai_val = c6.number_input("Festés egységár (Ft/mm²)", value=float(current_gep_data.get("paint", 0.0)), format="%.5f", key=f"pai{key_s}")
                    
                    if st.button(f"Mentés minden eszközre ({gep_nev})", key=f"btn_save_{key_s}"):
                        new_set = {"lazer": l_val, "material": m_val, "power": p_val, "work": w_val, "magnet": mag_val, "paint": pai_val}
                        save_gep_setting(gep_nev, new_set)
                        st.success(f"Sikeres mentés: {gep_nev} szinkronizálva!")
                        st.rerun()
                else:
                    st.warning("⚠️ Az alapértékek módosításához jelentkezz be az oldalsávban admin jelszóval!")
                    st.json(current_gep_data)

            st.divider()
            
            # Aktuális értékek a számításhoz
            m_val = float(current_gep_data.get("material", 0.006))
            l_val = float(current_gep_data.get("lazer", 0.0))
            p_val = float(current_gep_data.get("power", 0.0))
            w_val = float(current_gep_data.get("work", 25.0))
            mag_val = float(current_gep_data.get("magnet", 0.0))
            pai_val = float(current_gep_data.get("paint", 0.0))

            col_a, col_b = st.columns(2)
            with col_a:
                t_name = st.text_input("Termék neve", key=f"tn{key_s}")
                width = st.number_input("Szélesség (mm)", value=100.0, key=f"width{key_s}")
                height = st.number_input("Magasság (mm)", value=100.0, key=f"height{key_s}")
                
                # Ha érkezett idő az SVG kalkulátorból, azt írjuk be alapértelmezettként
                runtime = st.number_input("Gépidő (perc)", value=float(default_gtime), key=f"time{key_s}")
            
            with col_b:
                pcs = st.number_input("Darabszám a táblán", min_value=1, value=1, key=f"pcs{key_s}")
                use_magnet = st.checkbox("Mágnes kell rá?", key=f"umag{key_s}")
                use_paint = st.checkbox("Festés / Koptatás kell?", key=f"upai{key_s}")
                
                paint_multiplier = 1
                if use_paint:
                    paint_multiplier = st.number_input("Festés szorzó (pl. réteg vagy darab)", min_value=1, value=1, step=1, key=f"paimult{key_s}")

            # Költségszámítás
            area = width * height
            cost_material = area * m_val
            cost_machine = (l_val + p_val + w_val) * runtime
            
            cost_extra = 0
            if use_magnet: 
                cost_extra += mag_val
            if use_paint: 
                cost_extra += (area * pai_val * paint_multiplier)
            
            total_netto = (cost_material + cost_machine + cost_extra)
            total_with_margin = total_netto * 1.10 # 10% felár
            unit_price = total_with_margin / pcs

            st.subheader(f"💰 Javasolt eladási ár: {round(unit_price)} Ft / db")
            
            # Mentés az archívumba - CSAK ADMINNAK
            if st.session_state.logged_in:
                if st.button("💾 Mentés az Archívumba", key=f"final_save_{key_s}", use_container_width=True):
                    if db and t_name:
                        db.collection("kalkulaciok").add({
                            "datum": datetime.now(),
                            "gep": gep_nev,
                            "termek": t_name,
                            "ar": round(unit_price)
                        })
                        st.success(f"{t_name} archiválva!")
                    else:
                        st.error("Add meg a termék nevét a mentéshez!")
            else:
                st.info("💡 Az eredmények archiválásához jelentkezz be az oldalsávban.")

    render_calc_tab("Kis Lézer", tabs[0], "kis")
    render_calc_tab("Nagy Lézer", tabs[1], "nagy")
    render_calc_tab("3D Nyomtatás", tabs[2], "3d")

# --- 2. OLDAL: SVG IDŐBECSLŐ ---
elif page == "SVG Időbecslő":
    st.title("⏱️ SVG Időbecslő (DPI alapú)")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        v_raster = st.number_input("Fekete sebesség (Raszter) [mm/s]", value=300)
        dpi = st.number_input("Felbontás (DPI)", value=254)
        scan_gap_mm = 25.4 / dpi if dpi > 0 else 0.1
        st.caption(f"Kalkulált sorköz: {round(scan_gap_mm, 4)} mm")
        
        st.divider()
        v_blue = st.number_input("Kék sebesség (Vektor) [mm/s]", value=25)
        v_red = st.number_input("Piros sebesség (Vektor) [mm/s]", value=20)
        uploaded_file = st.file_uploader("Válassz SVG fájlt", type=["svg"])

    with col2:
        if uploaded_file:
            svg_raw = uploaded_file.getvalue().decode("utf-8")
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
                    st.caption(f"📏 Skálázás: {round(scaling, 4)}x")
            except: pass

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
                        for c in o_cls.split(): all_p += css_map.get(c, "") + " "

                    r_path_len = path.length() * scaling

                    if any(c in all_p for c in ['blue', '#0000ff', '0,0,255']):
                        b_len += r_path_len
                    elif any(c in all_p for c in ['red', '#ff0000', '255,0,0']):
                        r_len += r_path_len
                    elif any(c in all_p for c in ['black', '#000000', '0,0,0']) and 'fill:none' not in all_p:
                        try:
                            xmin, xmax, ymin, ymax = path.bbox()
                            w, h = (xmax-xmin)*scaling, (ymax-ymin)*scaling
                            over = (v_raster * 0.05)
                            t_rast += ((h/scan_gap_mm) * (w+(2*over))/v_raster) / 60
                        except: pass

                t_b = (b_len/v_blue)*1.15/60 if v_blue > 0 else 0
                t_r = (r_len/v_red)*1.15/60 if v_red > 0 else 0
                total = t_b + t_r + t_rast
                total_rounded = round(total, 2)

                st.success(f"✅ Becsült idő: {total_rounded} perc")
                st.metric("Összesen", f"{total_rounded} p")
                
                c1, c2, c3 = st.columns(3)
                c1.write(f"Kék: {round(b_len)}mm")
                c2.write(f"Piros: {round(r_len)}mm")
                c3.write(f"Raszter: {round(t_rast, 2)}p")

                st.divider()
                # Gomb, ami visszairányít a kalkulátor oldalra a kiszámolt idővel
                st.link_button("✅ IDŐ ÁTVÉTELE A KALKULÁTORBA", f"/?gtime={total_rounded}")
            except Exception as e:
                st.error(f"Hiba az SVG elemzésekor: {e}")

# --- 3. OLDAL: ARCHÍVUM ---
elif page == "Archívum":
    st.title("📁 Központi Archívum")
    if db:
        try:
            docs = db.collection("kalkulaciok").order_by("datum", direction=firestore.Query.DESCENDING).limit(50).stream()
            res = []
            for d in docs:
                v = d.to_dict()
                dt_val = v.get('datum')
                dt_str = dt_val.strftime("%Y-%m-%d %H:%M") if hasattr(dt_val, 'strftime') else str(dt_val)
                res.append([dt_str, v.get('gep'), v.get('termek'), f"{v.get('ar')} Ft"])
            if res:
                st.table(pd.DataFrame(res, columns=["Dátum", "Gép", "Termék", "Darabár"]))
            else:
                st.info("Még nincsenek mentett kalkulációk.")
        except Exception as e:
            st.warning(f"Hiba az archívum betöltésekor: {e}")
