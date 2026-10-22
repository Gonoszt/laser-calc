"""
Az SVG és DXF időbecslő oldalak közös elemei.

Ide kerül minden, ami a két oldalon azonos:
- a sebesség/DPI beállítások widgetjei,
- az idő-számítás (vektor hossz + raszter terület, 15% tartalékkal),
- a hosszú feldolgozások időkorlátos futtatója,
- az eredmény megjelenítése és a kalkulátorba való átvétel gombja.
"""

import concurrent.futures

import streamlit as st

MAX_FELDOLGOZASI_IDO_MP = 30  # ha ennél tovább tartana, inkább hibát adunk, mint örök várakozást
VEKTOR_TARTALEK = 1.15  # 15% ráhagyás a vektoridőkre (gépindulás, gyorsítások)


def sebessegek_beallitasa(prefix):
    """
    A bal oldali közös widget-készlet: raszter sebesség, felbontás, vektor sebességek.

    prefix: "svg" vagy "dxf" — a widget-azonosítók így nem ütköznek a két oldal között.
    Visszatér szótárban az értékeket (a scan_gap_mm-et is kiszámolva).
    """
    v_raster = st.number_input(
        "Fekete sebesség (Raszter) [mm/s]", value=300, key=f"{prefix}_v_raster"
    )
    dpi = st.number_input("Felbontás (DPI)", value=254, key=f"{prefix}_dpi")
    scan_gap_mm = 25.4 / dpi if dpi > 0 else 0.1
    st.divider()
    v_blue = st.number_input(
        "Kék sebesség (Vektor) [mm/s]", value=25, key=f"{prefix}_v_blue"
    )
    v_red = st.number_input(
        "Piros sebesség (Vektor) [mm/s]", value=20, key=f"{prefix}_v_red"
    )
    return {
        "v_raster": v_raster,
        "dpi": dpi,
        "scan_gap_mm": scan_gap_mm,
        "v_blue": v_blue,
        "v_red": v_red,
    }


def idokorlatos_futtatas(fuggveny, *args, max_mp=MAX_FELDOLGOZASI_IDO_MP, **kwargs):
    """
    Futtat egy függvényt külön szálon, legfeljebb max_mp másodpercig vár rá.
    Visszatér a függvény eredményével, vagy None-nal időtúllépésnél
    (a hívó jeleníti meg a hibaüzenetet).

    Megjegyzés: a ThreadPoolExecutor 'with' kontextuskezelője a kilépéskor
    shutdown(wait=True)-et hív, tehát a timeout UTÁN is megvárná a szálat —
    ezért itt kézzel, wait=False-zal zárjuk le, hogy az időkorlát valóban
    ne blokkolja tovább a kérést.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(fuggveny, *args, **kwargs).result(timeout=max_mp)
    except concurrent.futures.TimeoutError:
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def szamit_es_megjelenit(b_len, r_len, t_rast, seb, idotartam_mp, debug_szoveg=""):
    """
    Vektorhosszakból (mm) + raszteridőből (perc) kiszámolja a becsült időt,
    megjeleníti, és visszaadja a percértéket.
    """
    t_b = (b_len / seb["v_blue"]) * VEKTOR_TARTALEK / 60 if seb["v_blue"] > 0 else 0
    t_r = (r_len / seb["v_red"]) * VEKTOR_TARTALEK / 60 if seb["v_red"] > 0 else 0
    total = round(t_b + t_r + t_rast, 2)

    st.success(f"Becsült idő: {total} perc")
    caption = f"Fájl feldolgozása: {idotartam_mp:.2f} másodperc"
    if debug_szoveg:
        caption += f" ({debug_szoveg})"
    st.caption(caption)
    st.link_button("IDŐ ÁTVÉTELE A KALKULÁTORBA", f"/?gtime={total}")
    return total
