"""
SVG Időbecslő oldal (DPI alapú).

Az arkalkulator.py a render() függvényt hívja meg, amikor a felhasználó
a menüben az "SVG Időbecslő" oldalt választja. A logika 1:1-ben megegyezik
a korábbi arkalkulator.py belső ágával.
"""

import re
import time

import streamlit as st

try:
    from svgpathtools import svg2paths
except ImportError:
    st.error("Hiányzó csomag! A requirements.txt-be írd bele: svgpathtools")

from views.kozos import (
    MAX_FELDOLGOZASI_IDO_MP,
    idokorlatos_futtatas,
    sebessegek_beallitasa,
    szamit_es_megjelenit,
)


def elemez_svg(svg_bajtok, scaling, css_map, v_raster, scan_gap_mm):
    """
    Egy SVG fájl feldolgozása: útvonalhosszak szín szerint bontva.

    Visszatér: (kek_hossz_mm, piros_hossz_mm, raszter_ido_perc, utvonalak_szama).
    """
    with open("temp.svg", "wb") as f:
        f.write(svg_bajtok)

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
    return b_len, r_len, t_rast, len(paths)


def _kigyujt_css_map(svg_raw):
    """CSS osztálynevek -> stílusok szótár (a színkódolás feloldásához)."""
    css_map = {}
    styles = re.findall(r"\.([\w\d]+)\s*\{([^}]+)\}", svg_raw)
    for c_name, props in styles:
        css_map[c_name.lower()] = props.lower()
    return css_map


def _szamit_scaling(svg_raw):
    """
    Méretezési arány: a width attribútum és a viewBox szélességének hányadosa.
    Ha nem sikerül kinyerni, 1.0 marad.
    """
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
    return scaling


def render():
    st.title("SVG Időbecslő (DPI alapú)")
    col1, col2 = st.columns([1, 2])

    with col1:
        seb = sebessegek_beallitasa("svg")
        uploaded_file = st.file_uploader("Válassz SVG fájlt", type=["svg"])

    with col2:
        if not uploaded_file:
            return

        svg_raw = uploaded_file.getvalue().decode("utf-8")
        scaling = _szamit_scaling(svg_raw)
        css_map = _kigyujt_css_map(svg_raw)

        t_start = time.perf_counter()
        eredmeny = idokorlatos_futtatas(
            elemez_svg,
            uploaded_file.getvalue(),
            scaling,
            css_map,
            seb["v_raster"],
            seb["scan_gap_mm"],
        )
        if eredmeny is None:
            st.error(
                f"A fájl feldolgozása túllépte a {MAX_FELDOLGOZASI_IDO_MP} másodperces "
                "időkorlátot - valószínűleg túl sok vagy túl bonyolult útvonalat tartalmaz. "
                "Próbáld egyszerűsíteni az SVG-t (kevesebb csomópont, egyszerűsített útvonalak), "
                "vagy darabold több kisebb fájlra."
            )
            st.stop()

        b_len, r_len, t_rast, path_count = eredmeny
        szamit_es_megjelenit(
            b_len,
            r_len,
            t_rast,
            seb,
            idotartam_mp=time.perf_counter() - t_start,
            debug_szoveg=f"{path_count} útvonal",
        )
