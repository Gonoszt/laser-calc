import streamlit as st
import pandas as pd
import os
from datetime import datetime
try:
    from svgpathtools import svg2paths
except ImportError:
    st.error("Hiányzó csomag! Futtasd le a terminálban: pip install svgpathtools")
import re

# --- FÁJLOK ---
CALC_DATA_FILE = "kalkulaciok_archivum.csv"
SETTINGS_FILE = "gep_beallitasok.csv"

st.set_page_config(page_title="Melis & SK Profi Kalkulátor", layout="wide")

# --- ADATKEZELÉS (Betöltés/Mentés) ---
def load_settings():
    defaults = {
        "Kis Lézer": {"lazer": 0.8, "material": 0.005, "power": 4.6, "work": 25.0, "magnet": 150.0, "paint": 0.002},
        "Nagy Lézer": {"lazer": 1.5, "material": 0.005, "power": 5.5, "work": 25.0, "magnet": 0.0, "paint": 0.002},
        "3D Nyomtatás": {"lazer": 0.0, "material": 15.0, "power": 1.2, "work": 25.0, "magnet": 0.0, "paint": 0.0}
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            return pd.read_csv(SETTINGS_FILE).set_index('gep').to_dict('index')
        except:
            return defaults
    return defaults

def save_settings(gep_nev, adatok):
    if os.path.exists(SETTINGS_FILE):
        current = pd.read_csv(SETTINGS_FILE).set_index('gep')
    else:
        current = pd.DataFrame.from_dict(load_settings(), orient='index')
        current.index.name = 'gep'
    for k, v in adatok.items():
        current.at[gep_nev, k] = v
    current.reset_index().to_csv(SETTINGS_FILE, index=False, encoding="utf-8-sig")

all_settings = load_settings()

# --- ADMIN MÓD ---
if "admin_ok" not in st.session_state:
    st.session_state["admin_ok"] = False

st.sidebar.title("Műhely Vezérlő")

with st.sidebar.expander("🔐 Admin belépés"):
    admin_pw = st.text_input("Admin jelszó", type="password")
    if st.button("Belépés"):
        # IDE ÍRD A SAJÁT JELSZÓT VAGY HASZNÁLD st.secrets["ADMIN_PASSWORD"]
        if admin_pw == "admin123":
            st.session_state["admin_ok"] = True
            st.success("Admin mód aktiválva.")
        else:
            st.session_state["admin_ok"] = False
            st.error("Hibás jelszó.")

if st.session_state["admin_ok"]:
    st.sidebar.success("Admin mód aktív.")
else:
    st.sidebar.info("Vendég mód – csak kalkuláció, mentés nélkül.")

page = st.sidebar.radio("Válassz funkciót:", ["Költség Kalkulátor", "SVG Időbecslő"])

# --- 1. OLDAL: KÖLTSÉG KALKULÁTOR ---
if page == "Költség Kalkulátor":
    st.title("🧮 Gyártási Önköltég Kalkulátor")

    if st.session_state["admin_ok"]:
        tabs = st.tabs(["Kis Lézer", "Nagy Lézer", "3D Nyomtatás"])
    else:
        tabs = st.tabs(["Kis Lézer", "Nagy Lézer"])

    def render_laser_tab(gep_nev, tab_obj, key_suffix):
        with tab_obj:
            st.header(f"⚙️ {gep_nev} - Munkalap")
            
            # Alapértékek szerkesztése – csak adminnak
            if st.session_state["admin_ok"]:
                with st.expander(f"Alapértékek módosítása ({gep_nev})"):
                    c1, c2, c3 = st.columns(3)
                    lazer_f = c1.number_input(
                        "Lézer amort. (Ft/perc)",
                        value=float(all_settings[gep_nev]["lazer"]),
                        format="%.4f",
                        key=f"l_{key_suffix}"
                    )
                    mat_f = c2.number_input(
                        "Anyagár (Ft/mm²)",
                        value=float(all_settings[gep_nev]["material"]),
                        format="%.6f",
                        key=f"m_{key_suffix}"
                    )
                    pow_f = c3.number_input(
                        "Áram (Ft/perc)",
                        value=float(all_settings[gep_nev]["power"]),
                        format="%.4f",
                        key=f"p_{key_suffix}"
                    )
                    
                    c4, c5, c6 = st.columns(3)
                    work_f = c4.number_input(
                        "Munkadíj (Ft/perc)",
                        value=float(all_settings[gep_nev]["work"]),
                        format="%.2f",
                        key=f"w_{key_suffix}"
                    )
                    mag_f = c5.number_input(
                        "Szerelék (Ft/db)",
                        value=float(all_settings[gep_nev]["magnet"]),
                        format="%.2f",
                        key=f"mag_{key_suffix}"
                    )
                    paint_f = c6.number_input(
                        "Festék (Ft/mm²)",
                        value=float(all_settings[gep_nev]["paint"]),
                        format="%.6f",
                        key=f"paint_{key_suffix}"
                    )
                    
                    if st.button(f"Alapértékek mentése ({gep_nev})", key=f"btn_{key_suffix}"):
                        save_settings(
                            gep_nev,
                            {
                                "lazer": lazer_f,
                                "material": mat_f,
                                "power": pow_f,
                                "work": work_f,
                                "magnet": mag_f,
                                "paint": paint_f
                            }
                        )
                        st.success("Mentve a fájlba!")
            else:
                # Vendég módban csak a jelenlegi értékekkel számolunk
                lazer_f = float(all_settings[gep_nev]["lazer"])
                mat_f = float(all_settings[gep_nev]["material"])
                pow_f = float(all_settings[gep_nev]["power"])
                work_f = float(all_settings[gep_nev]["work"])
                mag_f = float(all_settings[gep_nev]["magnet"])
                paint_f = float(all_settings[gep_nev]["paint"])

            st.divider()

            # Beviteli mezők a számításhoz
            col_a, col_b = st.columns(2)
            with col_a:
                t_nev = st.text_input("Termék neve", key=f"tn_{key_suffix}")
                x = st.number_input("Szélesség (mm)", min_value=1.0, value=100.0, key=f"x_{key_suffix}")
                y = st.number_input("Magasság (mm)", min_value=1.0, value=100.0, key=f"y_{key_suffix}")
                g_time = st.number_input(
                    "Munkaidő (perc)",
                    min_value=0.0,
                    value=5.0,
                    key=f"gt_{key_suffix}",
                    help="Ide másold az SVG becslő eredményét!"
                )

            with col_b:
                db_per_tabla = st.number_input("Hány termék jön ki ebből?", min_value=1, value=1, key=f"db_{key_suffix}")
                festek_reteg = st.number_input("Festék rétegek száma", min_value=0, value=0, key=f"fr_{key_suffix}")
                szerelek_db = st.number_input("Szerelék (db/késztermék)", min_value=0, value=1, key=f"sz_{key_suffix}")

            # SZÁMÍTÁSOK
            terulet = x * y
            anyag_osszeg = mat_f * terulet
            grav_osszeg = (lazer_f + pow_f + work_f) * g_time
            festes_osszeg = festek_reteg * terulet * paint_f
            szerelek_osszeg = mag_f * szerelek_db * db_per_tabla
            
            netto_munkadij = anyag_osszeg + grav_osszeg + festes_osszeg + szerelek_osszeg
            eloallitasi_koltseg = netto_munkadij * 1.11  # 11% felár

            egy_db_ara = eloallitasi_koltseg / db_per_tabla

            teljes_ar = eloallitasi_koltseg
            ajanlott_ar = ((round(teljes_ar) + 9) // 10) * 10

            # EREDMÉNYEK
            st.subheader("📊 Kalkuláció eredménye")
            res1, res2, res3 = st.columns(3)
            with res1:
                st.write(f"Nettó önköltség: **{round(netto_munkadij, 1)} Ft**")
                st.caption(f"Anyag: {round(anyag_osszeg)} Ft | Gravír: {round(grav_osszeg)} Ft")
            with res2:
                st.write("Előállítási költség (+11%):")
                st.header(f"{round(eloallitasi_koltseg)} Ft")
            with res3:
                st.write("**Egy darab ára:**")
                st.title(f"{round(egy_db_ara)} Ft")

            st.subheader("💰 Teljes ár és ajánlott ár")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.write(f"Teljes ár: **{round(teljes_ar)} Ft**")
            with col_t2:
                st.write("Kiajánlott ár (10-re kerekítve):")
                st.header(f"{ajanlott_ar} Ft")

            # ARCHÍVUM MENTÉS – csak adminnak
            if st.button(f"💾 {gep_nev} MENTÉSE ARCHÍVUMBA", key=f"arch_{key_suffix}", use_container_width=True):
                if not st.session_state["admin_ok"]:
                    st.error("Mentés csak admin módban lehetséges.")
                else:
                    if t_nev:
                        data = {
                            "Dátum": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Gép": gep_nev,
                            "Termék": t_nev,
                            "Szélesség (mm)": x,
                            "Magasság (mm)": y,
                            "Munkaidő (perc)": g_time,
                            "Darabszám / tábla": db_per_tabla,
                            "Festék rétegek": festek_reteg,
                            "Szerelék (db/késztermék)": szerelek_db,
                            "Kell-e mágnes": "igen" if szerelek_db > 0 else "nem",
                            "Anyagköltség": round(anyag_osszeg),
                            "Gravírköltség": round(grav_osszeg),
                            "Festésköltség": round(festes_osszeg),
                            "Szerelék költség": round(szerelek_osszeg),
                            "Nettó önköltség": round(netto_munkadij),
                            "Teljes ár": round(teljes_ar),
                            "Ajánlott ár": ajanlott_ar,
                            "Darabár": round(egy_db_ara)
                        }
                        pd.DataFrame([data]).to_csv(
                            CALC_DATA_FILE,
                            mode='a',
                            header=not os.path.exists(CALC_DATA_FILE),
                            index=False,
                            encoding="utf-8-sig"
                        )
                        st.success(f"'{t_nev}' archiválva!")
                    else:
                        st.error("Kérlek, adj meg egy terméknevet!")

    # A két lézer fül
    render_laser_tab("Kis Lézer", tabs[0], "kis")
    render_laser_tab("Nagy Lézer", tabs[1], "nagy")
    
    if st.session_state["admin_ok"] and len(tabs) > 2:
        with tabs[2]:
            st.info("3D Nyomtatás kalkulátor - Fejlesztés alatt... (csak adminnak látható)")

# --- 2. OLDAL: SVG IDŐBECSLŐ ---
elif page == "SVG Időbecslő":
    st.title("⏱️ SVG Munkaidő Becslő (Profi Verzió)")
    st.info("CorelDRAW kompatibilis, automatikus méret-korrekcióval (mm).")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Gép paraméterei")
        v_raster = st.number_input("Fekete sebesség (Raszter) [mm/s]", value=300)
        scan_gap = st.number_input("Scan Gap (Sorköz) [mm]", value=0.1, format="%.3f")
        st.divider()
        v_blue = st.number_input("Kék sebesség (Vektor) [mm/s]", value=25)
        v_red = st.number_input("Piros sebesség (Vektor) [mm/s]", value=20)
        
        uploaded_file = st.file_uploader("Válassz SVG fájlt", type=["svg"])

    with col2:
        if uploaded_file:
            svg_raw = uploaded_file.getvalue().decode("utf-8")
            
            scaling = 1.0
            try:
                width_match = re.search(r'width="([\d\.]+)(mm|cm|px|pt)?"', svg_raw)
                viewbox_match = re.search(r'viewBox="[\d\.]+\s+[\d\.]+\s+([\d\.]+)', svg_raw)
                
                if width_match and viewbox_match:
                    phys_w = float(width_match.group(1))
                    unit = width_match.group(2)
                    vb_w = float(viewbox_match.group(1))
                    
                    if unit == 'cm':
                        phys_w *= 10
                    elif unit == 'pt':
                        phys_w *= 0.3527
                    
                    scaling = phys_w / vb_w
                    st.caption(f"📏 Automatikus skálázás: {round(scaling, 4)}x")
            except:
                st.warning("⚠️ Nem sikerült a méretarány meghatározása.")

            css_map = {}
            styles = re.findall(r'\.([\w\d]+)\s*\{([^}]+)\}', svg_raw)
            for class_name, props in styles:
                css_map[class_name.lower()] = props.lower()

            with open("temp.svg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                paths, attributes = svg2paths("temp.svg")
                blue_len, red_len, t_raster = 0.0, 0.0, 0.0

                for path, attr in zip(paths, attributes):
                    obj_class = attr.get('class', '').lower()
                    obj_stroke = attr.get('stroke', '').lower()
                    obj_fill = attr.get('fill', '').lower()
                    
                    all_props = f"{obj_stroke} {obj_fill} "
                    if obj_class:
                        for cls in obj_class.split():
                            all_props += css_map.get(cls, "") + " "

                    real_length = path.length() * scaling

                    if any(c in all_props for c in ['blue', '#0000ff', '0,0,255']):
                        blue_len += real_length
                    
                    elif any(c in all_props for c in ['red', '#ff0000', '255,0,0']):
                        red_len += real_length
                    
                    elif any(c in all_props for c in ['black', '#000000', '0,0,0']):
                        if 'fill:none' not in all_props:
                            try:
                                xmin, xmax, ymin, ymax = path.bbox()
                                w = (xmax - xmin) * scaling
                                h = (ymax - ymin) * scaling
                                overscan = (v_raster * 0.05)
                                lines = h / scan_gap
                                line_time = (w + (2 * overscan)) / v_raster
                                t_raster += (lines * line_time) / 60
                            except:
                                pass

                t_blue = (blue_len / v_blue) * 1.15 / 60 if v_blue > 0 else 0
                t_red = (red_len / v_red) * 1.15 / 60 if v_red > 0 else 0
                total_m = t_blue + t_red + t_raster

                if total_m < 0.1:
                    st.error(f"Hiba: Irreálisan kevés idő ({round(total_m, 2)} perc).")
                else:
                    st.success("✅ Kalkuláció kész!")
                    st.metric("Becsült munkaidő", f"{round(total_m, 2)} perc")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Kék hossza", f"{round(blue_len)} mm")
                    c2.metric("Piros hossza", f"{round(red_len)} mm")
                    c3.metric("Raszter idő", f"{round(t_raster, 2)} p")
                    
                    st.text_area("Vágólapra:", value=str(round(total_m, 2)))

            except Exception as e:
                st.error(f"Hiba: {e}")
