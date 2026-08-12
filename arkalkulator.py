import streamlit as st
import pandas as pd
import re
from datetime import datetime
from google.cloud import firestore
from streamlit_autorefresh import st_autorefresh
from config import get_db_client, get_admin_password
from realtime import start_listeners, get_gepek, get_kalkulaciok

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

# --- VALÓS IDEJŰ LISTENEREK INDÍTÁSA (csak egyszer fut le az egész app életében) ---
if db:
    start_listeners(db)
    # Az app minden 3 másodpercben újrarendereli magát, hogy a háttérben
    # frissült (listener által frissített) adatot megjelenítse.
    # Ha zavaróan gyakori lenne gépelés közben, nyugodtan vedd feljebb (pl. 5000-10000 ms-re).
    st_autorefresh(interval=3000, key="rt_refresh")

DEFAULT_SETTINGS = {
    "Kis Lézer": {
        "lazer": 0.8,
        "material": 0.005,
        "power": 4.6,
        "work": 25.0,
        "magnet": 150.0,
        "paint": 0.002,
    },
    "Nagy Lézer": {
        "lazer": 1.5,
        "material": 0.005,
        "power": 5.5,
        "work": 25.0,
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


def load_all_settings():
    """
    Elsőként a valós idejű (listener által frissen tartott) cache-ből próbál olvasni.
    Ha még nem érkezett adat a listenertől (pl. app épp most indult el), visszaesik
    egy közvetlen Firestore olvasásra, ez pedig a végső esetben az alapértelmezettekre.
    """
    live = get_gepek()
    if live is not None:
        # hiányzó gépeket/kulcsokat pótoljuk az alapértelmezettekkel
        merged = {k: dict(v) for k, v in DEFAULT_SETTINGS.items()}
        for gep_nev, adatok in live.items():
            merged.setdefault(gep_nev, {})
            merged[gep_nev].update(adatok)
        return merged

    if db:
        try:
            doc = db.collection("beallitasok").document("gepek").get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            st.warning("Nem sikerült beolvasni a beállításokat az adatbázisból.")
    return DEFAULT_SETTINGS


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
                        format="%.5f",
                        step=0.00001,
                        key=f"l_{key_s}",
                    )
                    m_val = c2.number_input(
                        "Anyag alapár (Ft/mm²)",
                        value=float(current_gep_data.get("material", 0.0)),
                        format="%.5f",
                        step=0.00001,
                        key=f"m_{key_s}",
                    )
                    p_val = c3.number_input(
                        "Áram (Ft/p)",
                        value=float(current_gep_data.get("power", 0.0)),
                        format="%.5f",
                        step=0.00001,
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
                        format="%.5f",
                        step=0.00001,
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
            calculated_unit_price = round(total_with_margin / pcs) if pcs > 0 else 0

            st.subheader(f"Javasolt eladási ár: {calculated_unit_price} Ft / db")
            suggested_price = st.number_input(
                "Kiajánlott ár (Ft / db)",
                value=None,
                placeholder="Hagyd üresen, ha a számított ár érvényes",
                min_value=0,
                key=f"sugg_{key_s}",
            )

            # Az "érvényes" egységár: ha van kiajánlott ár, azt vesszük figyelembe,
            # egyébként a rendszer által számítottat.
            effective_unit_price = suggested_price if suggested_price is not None else calculated_unit_price
            total_calculated_price = calculated_unit_price * pcs
            total_effective_price = effective_unit_price * pcs

            oc1, oc2 = st.columns(2)
            oc1.metric("Egységár (érvényes)", f"{effective_unit_price:,.0f} Ft/db".replace(",", " "))
            oc2.metric(f"Összesen ({pcs} db)", f"{total_effective_price:,.0f} Ft".replace(",", " "))
            if suggested_price is not None and suggested_price != calculated_unit_price:
                st.caption(
                    f"Számított egységár alapján: {calculated_unit_price:,.0f} Ft/db "
                    f"→ összesen {total_calculated_price:,.0f} Ft".replace(",", " ")
                )

            # Archiválás
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
                                    "darabszam": pcs,
                                    "meret": {
                                        "szelesseg_mm": width,
                                        "magassag_mm": height,
                                        "terulet_mm2": area,
                                    },
                                    "gepido_perc": runtime,
                                    "extra": {
                                        "magnes": use_magnet,
                                        "festes": use_paint,
                                        "festes_szorzo": paint_multiplier if use_paint else None,
                                    },
                                    # A számításnál ténylegesen használt gépi alapárak pillanatképe -
                                    # így később is visszakereshető, milyen árazással készült a kalkuláció,
                                    # akkor is ha az admin időközben módosítja az alapbeállításokat.
                                    "gep_parameterek": {
                                        "lazer": l_val,
                                        "material": m_val,
                                        "power": p_val,
                                        "work": w_val,
                                        "magnet": mag_val,
                                        "paint": pai_val,
                                    },
                                    "koltsegek": {
                                        "anyag": round(cost_material, 2),
                                        "gep": round(cost_machine, 2),
                                        "extra": round(cost_extra, 2),
                                        "netto_osszesen": round(total_netto, 2),
                                        "brutto_margoval": round(total_with_margin, 2),
                                    },
                                    "szamitott_ar": calculated_unit_price,
                                    # Ha üresen maradt a mező, None-t mentünk - ez azt jelenti,
                                    # hogy nem lett külön kiajánlott ár megadva, a számított ár érvényes.
                                    "kiajanlott_ar": suggested_price,
                                    "osszegzes": {
                                        "egysegar_szamitott": calculated_unit_price,
                                        "egysegar_kiajanlott": suggested_price,
                                        "egysegar_vegleges": effective_unit_price,
                                        "osszesen_szamitott": round(total_calculated_price, 2),
                                        "osszesen_vegleges": round(total_effective_price, 2),
                                    },
                                }
                            )
                            st.success(f"'{t_name.strip()}' sikeresen archiválva!")
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
        # Valós idejű adat: a listener által frissen tartott cache-ből olvasunk,
        # ez NEM indít újabb Firestore olvasást minden rerun-nál.
        raw_docs = get_kalkulaciok()

        # Ha a listener még nem futott le (pl. app épp most indult), essünk
        # vissza egy közvetlen olvasásra, hogy sose maradjon üres a felület.
        if not raw_docs:
            try:
                raw_docs = [
                    {**d.to_dict(), "id": d.id}
                    for d in db.collection("kalkulaciok")
                    .order_by("datum", direction=firestore.Query.DESCENDING)
                    .limit(100)
                    .stream()
                ]
            except Exception as e:
                st.warning(f"Hiba: {e}")
                raw_docs = []

        try:
            res = []
            for v in raw_docs:
                dt_val = v.get("datum")
                dt_str = dt_val.strftime("%Y-%m-%d %H:%M") if hasattr(dt_val, "strftime") else str(dt_val)

                # .get(..., {}) mindenhol: a régebbi, e bővítés előtt mentett rekordoknál
                # ezek a mezők még nem léteznek, így nem szabad hibát dobniuk.
                meret = v.get("meret", {})
                extra = v.get("extra", {})
                koltsegek = v.get("koltsegek", {})
                kiajanlott = v.get("kiajanlott_ar")
                osszegzes = v.get("osszegzes", {})
                # Régi (bővítés előtti) rekordoknál nincs "osszegzes" mező -
                # ilyenkor a darabszám × számított egységár alapján számolunk fallback összeget.
                osszesen_ft = osszegzes.get(
                    "osszesen_vegleges",
                    v.get("szamitott_ar", 0) * v.get("darabszam", 1),
                )

                res.append(
                    {
                        "id": v.get("id"),
                        "Dátum": dt_str,
                        "Gép": v.get("gep"),
                        "Termék": v.get("termek"),
                        "Méret (mm)": (
                            f"{meret.get('szelesseg_mm')}×{meret.get('magassag_mm')}"
                            if meret
                            else "-"
                        ),
                        "Gépidő (p)": v.get("gepido_perc", "-"),
                        "Darabszám": v.get("darabszam", 1),
                        "Mágnes": "igen" if extra.get("magnes") else "-",
                        "Festés": "igen" if extra.get("festes") else "-",
                        "Anyagköltség": koltsegek.get("anyag", "-"),
                        "Gépköltség": koltsegek.get("gep", "-"),
                        "Extra ktg": koltsegek.get("extra", "-"),
                        "Egységár (Ft/db)": v.get("szamitott_ar", 0),
                        "Kiajánlott Ár (Ft/db)": kiajanlott if kiajanlott is not None else "-",
                        "Összesen (Ft)": round(osszesen_ft, 0),
                    }
                )

            if res:
                df_arch = pd.DataFrame(res)
                df_display = df_arch.drop(columns=["id"])
                st.dataframe(df_display, use_container_width=True)

                st.divider()
                st.subheader("Tétel részletei")
                selected_detail = st.selectbox(
                    "Válassz egy tételt a teljes adatok (pl. az adott gép akkori árbeállításai) megtekintéséhez:",
                    options=[f"{row['id']} | {row['Dátum']} - {row['Gép']} - {row['Termék']}" for row in res],
                    index=None,
                    placeholder="Válassz tételt...",
                )
                if selected_detail:
                    detail_id = selected_detail.split(" | ")[0]
                    detail_doc = next((v for v in raw_docs if v.get("id") == detail_id), None)
                    if detail_doc:
                        st.json({k: v for k, v in detail_doc.items() if k != "id"})

                st.divider()
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
