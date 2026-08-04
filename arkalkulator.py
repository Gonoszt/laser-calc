import streamlit as st
import pandas as pd
import re
from datetime import datetime
from google.cloud import firestore
from config import get_db_client, get_admin_password
import math

# --- SVG elemzéshez szükséges könyvtár ---
try:
    from svgpathtools import svg2paths
except ImportError:
    st.error("Hiányzó csomag! A requirements.txt-be írd bele: svgpathtools")

# --- ADATBÁZIS ÉS JELSZÓ INICIALIZÁLÁS ---
db = get_db_client()
ADMIN_PASSWORD = get_admin_password()

st.set_page_config(page_title="Melis & SK Profi Kalkulátor", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- KEREKÍTŐ SEGÉDFÜGGVÉNY ---
def round_up_to_5_or_0(val):
    if val <= 0:
        return 0
    return int(math.ceil(val / 5.0) * 5)

# --- BEÁLLÍTÁSOK KEZELÉSE ---
def load_all_settings():
    defaults = {
        "Kis Lézer": {
            "lazer": 0.8,
            "material": 0.005,
            "power": 4.6,
            "work": 25.0,
            "magnet": 150.0,
            "paint": 0.002,
        },
        "Nagy Lézer": {
            "lazer": 2.92,
            "material": 0.01,
            "power": 7.0,
            "work": 65.20,
            "magnet": 0.0,
            "paint": 0.0,
        },
        "3D Nyomtatás": {
            "lazer": 0.0,
            "material": 15.0,
            "power": 1.2,
            "work": 25.0,
            "magnet": 0.0,
            "paint": 0.0,
        },
    }
    if db:
        try:
            doc = db.collection("beallitasok").document("gepek").get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            st.warning("Nem sikerült beolvasni a beállításokat az adatbázisból.")
    return defaults


def save_gep_setting(gep_nev, adatok):
    if not db:
        st.error("Nem tudok menteni, mert nincs Firestore kapcsolat.")
        return
    try:
        db.collection("beallitasok").document("gepek").set({gep_nev: adatok}, merge=True)
        st.success(f"Sikeres mentés: {gep_nev} beállításai frissítve!")
    except Exception as e:
        st.error(f"Hiba a beállítások mentésekor: {e}")


all_settings = load_all_settings()

# --- URL PARAMÉTEREK FIGYELÉSE ---
query_params = st.query_params
default_gtime = 5.0
if "gtime" in query_params:
    try:
        default_gtime = float(query_params["gtime"])
    except Exception:
        pass

# --- MENÜ ÉS ADMIN VEZÉRLÉS ---
st.sidebar.title("Műhely Vezérlő")
menu_options = ["Költség Kalkulátor", "SVG Időbecslő"]
if st.session_state.logged_in:
    menu_options.append("Archívum")

page = st.sidebar.radio("Választó:", menu_options)
st.sidebar.divider()

st.sidebar.subheader("Adminisztráció")
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
    st.sidebar.success("Admin mód aktív")
    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.rerun()

# --- 1. OLDAL: KALKULÁTOR ---
if page == "Költség Kalkulátor":
    st.title("Részletes Költség Kalkulátor")
    tabs = st.tabs(["Kis Lézer", "Nagy Lézer", "3D Nyomtatás"])

    def render_calc_tab(gep_nev, tab_obj, key_s):
        with tab_obj:
            current_gep_data = all_settings.get(gep_nev, {})

            # Admin beállítás szerkesztés
            if st.session_state.logged_in:
                with st.expander(f"Alapárak és rezsi szerkesztése ({gep_nev})"):
                    c1, c2, c3 = st.columns(3)
                    l_val = c1.number_input(
                        "Lézer amort. (Ft/p)",
                        value=float(current_gep_data.get("lazer", 0.0)),
                        key=f"l_{key_s}",
                    )
                    m_val = c2.number_input(
                        "Anyag alapár (Ft/mm²)",
                        value=float(current_gep_data.get("material", 0.0)),
                        format="%.4f",
                        key=f"m_{key_s}",
                    )
                    p_val = c3.number_input(
                        "Áram (Ft/p)",
                        value=float(current_gep_data.get("power", 0.0)),
                        key=f"pw_{key_s}",
                    )

                    c4, c5, c6 = st.columns(3)
                    w_val = c4.number_input(
                        "Munkadíj (Ft/p)",
                        value=float(current_gep_data.get("work", 25.0)),
                        key=f"w_{key_s}",
                    )
                    mag_val = c5.number_input(
                        "Mágnes ára (Ft/db)",
                        value=float(current_gep_data.get("magnet", 0.0)),
                        key=f"mag_{key_s}",
                    )
                    pai_val = c6.number_input(
                        "Festés egységár (Ft/mm²)",
                        value=float(current_gep_data.get("paint", 0.0)),
                        format="%.4f",
                        key=f"pai_{key_s}",
                    )

                    if st.button(f"Mentés minden eszközre ({gep_nev})", key=f"btn_save_{key_s}"):
                        new_set = {
                            "lazer": l_val,
                            "material": m_val,
                            "power": p_val,
                            "work": w_val,
                            "magnet": mag_val,
                            "paint": pai_val,
                        }
                        save_gep_setting(gep_nev, new_set)
                        st.rerun()

            st.divider()

            # Aktuális értékek
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
                runtime = st.number_input("Gépidő (perc)", value=float(default_gtime), key=f"time{key_s}")

            with col_b:
                pcs = st.number_input("Darabszám a táblán", min_value=1, value=1, key=f"pcs{key_s}")
                use_magnet = st.checkbox("Mágnes kell rá?", key=f"umag{key_s}")
                use_paint = st.checkbox("Festés / Koptatás kell?", key=f"upai{key_s}")
                paint_multiplier = 1
                if use_paint:
                    paint_multiplier = st.number_input(
                        "Festés szorzó", min_value=1, value=1, key=f"pmulti{key_s}"
                    )

            area = width * height
            cost_material = area * m_val
            cost_machine = (l_val + p_val + w_val) * runtime
            cost_extra = 0
            if use_magnet:
                cost_extra += mag_val
            if use_paint:
                cost_extra += (area * pai_val * paint_multiplier)

            total_netto = cost_material + cost_machine + cost_extra
            total_with_margin = total_netto * 1.11
            
            calc_unit_raw = total_with_margin / pcs if pcs > 0 else 0
            calculated_unit_price = round_up_to_5_or_0(calc_unit_raw)
            calculated_total_price = calculated_unit_price * pcs

            st.subheader(f"Számított darabár: {calculated_unit_price} Ft / db | Teljes ár: {calculated_total_price} Ft")
            
            sugg_unit_raw = st.number_input(
                "Kiajánlott darabár (Ft / db)",
                value=int(calculated_unit_price),
                key=f"sugg_{key_s}",
            )
            
            suggested_unit_price = round_up_to_5_or_0(sugg_unit_raw)
            suggested_total_price = suggested_unit_price * pcs

            st.info(f"Rögzítendő kiajánlott adatok -> Darabár: {suggested_unit_price} Ft/db | Teljes ár: {suggested_total_price} Ft")

            # Archiválás (teljes adattartalom mentése)
            if st.session_state.logged_in:
                if st.button("Mentés az Archívumba", key=f"final_save_{key_s}", use_container_width=True):
                    if not db:
                        st.error("Nincs adatbázis kapcsolat!")
                    elif not t_name or not t_name.strip():
                        st.error("Add meg a termék nevét!")
                    else:
                        try:
                            db.collection("kalkulaciok").add(
                                {
                                    "datum": datetime.now(),
                                    "gep": gep_nev,
                                    "termek": t_name.strip(),
                                    "szelesseg": width,
                                    "magassag": height,
                                    "gepido_perc": runtime,
                                    "darabszam": pcs,
                                    "magnes_kell": use_magnet,
                                    "festes_kell": use_paint,
                                    "festes_szorzo": paint_multiplier,
                                    "szamitott_ar": calculated_unit_price,
                                    "kiajanlott_ar": suggested_unit_price,
                                    "teljes_ar": suggested_total_price,
                                }
                            )
                            st.success(f"'{t_name.strip()}' és minden paramétere sikeresen archiválva!")
                        except Exception as e:
                            st.error(f"Hiba történt a mentés során: {e}")

    render_calc_tab("Kis Lézer", tabs[0], "kis")
    render_calc_tab("Nagy Lézer", tabs[1], "nagy")
    render_calc_tab("3D Nyomtatás", tabs[2], "3d")

# --- 2. OLDAL: SVG IDŐBECSLŐ ---
elif page == "SVG Időbecslő":
    st.title("SVG Időbecslő (DPI alapú)")
    col1, col2 = st.columns([1, 2])

    with col1:
        v_raster = st.number_input("Fekete sebesség (Raszter) [mm/s]", value=300)
        dpi = st.number_input("Felbontás (DPI)", value=254)
        scan_gap_mm = 25.4 / dpi if dpi > 0 else 0.1
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
                    if unit == "cm":
                        p_w *= 10
                    elif unit == "pt":
                        p_w *= 0.3527
                    scaling = p_w / float(vb_match.group(1))
            except Exception:
                pass

            css_map = {}
            styles = re.findall(r"\.([\w\d]+)\s*\{([^}]+)\}", svg_raw)
            for c_name, props in styles:
                css_map[c_name.lower()] = props.lower()

            with open("temp.svg", "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                paths, attributes = svg2paths("temp.svg")
                b_len, r_len, t_rast = 0.0, 0.0, 0.0
                for path, attr in zip(paths, attributes):
                    o_cls = attr.get("class", "").lower()
                    o_str = attr.get("stroke", "").lower()
                    o_fil = attr.get("fill", "").lower()
                    all_p = f"{o_str} {o_fil}"
                    if o_cls:
                        for c in o_cls.split():
                            all_p += css_map.get(c, "") + " "

                    r_path_len = path.length() * scaling
                    if any(c in all_p for c in ["blue", "#0000ff", "0,0,255"]):
                        b_len += r_path_len
                    elif any(c in all_p for c in ["red", "#ff0000", "255,0,0"]):
                        r_len += r_path_len
                    elif any(c in all_p for c in ["black", "#000000", "0,0,0"]) and "fill:none" not in all_p:
                        try:
                            xmin, xmax, ymin, ymax = path.bbox()
                            w, h = (xmax - xmin) * scaling, (ymax - ymin) * scaling
                            over = v_raster * 0.05
                            t_rast += ((h / scan_gap_mm) * (w + (2 * over)) / v_raster) / 60
                        except Exception:
                            pass

                t_b = (b_len / v_blue) * 1.15 / 60 if v_blue > 0 else 0
                t_r = (r_len / v_red) * 1.15 / 60 if v_red > 0 else 0
                total = round(t_b + t_r + t_rast, 2)

                st.success(f"Becsült idő: {total} perc")
                st.link_button("IDŐ ÁTVÉTELE A KALKULÁTORBA", f"/?gtime={total}")
            except Exception as e:
                st.error(f"Hiba az SVG elemzésekor: {e}")

# --- 3. OLDAL: ARCHÍVUM ---
elif page == "Archívum" and st.session_state.logged_in:
    st.title("Központi Archívum")
    if not db:
        st.error("Firestore kapcsolat nem elérhető.")
    else:
        try:
            docs = list(
                db.collection("kalkulaciok")
                .order_by("datum", direction=firestore.Query.DESCENDING)
                .limit(100)
                .stream()
            )
            res = []
            for d in docs:
                v = d.to_dict()
                dt_val = v.get("datum")
                dt_str = dt_val.strftime("%Y-%m-%d %H:%M") if hasattr(dt_val, "strftime") else str(dt_val)
                pcs_val = v.get("darabszam", 1)
                sugg_u = v.get("kiajanlott_ar", 0)
                tot_p = v.get("teljes_ar", sugg_u * pcs_val)
                
                res.append(
                    {
                        "id": d.id,
                        "Dátum": dt_str,
                        "Gép": v.get("gep"),
                        "Termék": v.get("termek"),
                        "Szélesség": v.get("szelesseg", 0),
                        "Magasság": v.get("magassag", 0),
                        "Gépidő (p)": v.get("gepido_perc", 0),
                        "Darabszám": pcs_val,
                        "Mágnes": "Igen" if v.get("magnes_kell") else "Nem",
                        "Festés": "Igen" if v.get("festes_kell") else "Nem",
                        "Számított Ár (Ft/db)": v.get("szamitott_ar", 0),
                        "Kiajánlott Ár (Ft/db)": sugg_u,
                        "Teljes Ár (Ft)": tot_p,
                    }
                )

            if res:
                df_arch = pd.DataFrame(res)
                df_display = df_arch.drop(columns=["id"])
                st.dataframe(df_display, use_container_width=True)

                selected_to_delete = st.multiselect(
                    "Törlendő elemek kijelölése:",
                    options=[f"{row['id']} | {row['Dátum']} - {row['Gép']} - {row['Termék']}" for row in res],
                )

                if selected_to_delete and st.button("Kiválasztottak törlése", type="primary"):
                    try:
                        for item in selected_to_delete:
                            db.collection("kalkulaciok").document(item.split(" | ")[0]).delete()
                        st.success("Törölve!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hiba törlés közben: {e}")
            else:
                st.info("Nincsenek mentett adatok.")
        except Exception as e:
            st.warning(f"Hiba: {e}")
