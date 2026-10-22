"""
DXF Időbecslő oldal (CorelDraw export alapján).

Az arkalkulator.py a render() függvényt hívja meg, amikor a felhasználó
a menüben a "DXF Időbecslő" oldalt választja. A logika 1:1-ben megegyezik
a korábbi arkalkulator.py belső ágával.
"""

import time

import streamlit as st

try:
    import ezdxf
    from ezdxf import bbox as ezdxf_bbox
except ImportError:
    ezdxf = None

from views.kozos import (
    MAX_FELDOLGOZASI_IDO_MP,
    idokorlatos_futtatas,
    sebessegek_beallitasa,
    szamit_es_megjelenit,
)


def _entitas_hossza(e):
    """Egy DXF entitás valódi (görbe menti) hossza mm-ben."""
    try:
        if e.dxftype() == "LINE":
            p1, p2 = e.dxf.start, e.dxf.end
            return ((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2) ** 0.5
        if hasattr(e, "flattening"):
            pts = list(e.flattening(0.05))
            return sum(
                ((pts[i].x - pts[i - 1].x) ** 2 + (pts[i].y - pts[i - 1].y) ** 2) ** 0.5
                for i in range(1, len(pts))
            )
    except Exception:
        pass
    return 0.0


def elemez_dxf(dxf_bajtok, v_raster, scan_gap_mm):
    """
    Egy DXF fájl feldolgozása színkódolás szerint.

    Visszatér: (kek_hossz_mm, piros_hossz_mm, raszter_ido_perc, entitasok_szama).
    """
    with open("temp_dxf.dxf", "wb") as f:
        f.write(dxf_bajtok)

    doc = ezdxf.readfile("temp_dxf.dxf")
    msp = doc.modelspace()
    layer_colors = {layer.dxf.name: layer.dxf.color for layer in doc.layers}

    def resolve_color(e):
        c = e.dxf.color
        if c == 256:  # ByLayer - a réteg saját színét kell figyelembe venni
            return layer_colors.get(e.dxf.layer, 7)
        if c == 0:  # ByBlock - egyszerűsítésként alapszínnek vesszük
            return 7
        return c

    b_len, r_len, t_rast = 0.0, 0.0, 0.0
    count = 0
    for e in msp:
        count += 1
        color = resolve_color(e)
        length = _entitas_hossza(e)

        if color == 1:  # piros
            r_len += length
        elif color == 5:  # kék
            b_len += length
        else:  # minden egyéb szín = raszteres égetendő terület
            try:
                box = ezdxf_bbox.extents([e])
                w = box.extmax.x - box.extmin.x
                h = box.extmax.y - box.extmin.y
                over = v_raster * 0.05
                t_rast += ((h / scan_gap_mm) * (w + (2 * over)) / v_raster) / 60
            except Exception:
                pass
    return b_len, r_len, t_rast, count


def render():
    st.title("DXF Időbecslő (CorelDraw export alapján)")
    st.caption(
        "Színkódolás: **piros vonal** (ACI 1) = vektor vágás/gravírozás, "
        "**kék vonal** (ACI 5) = vektor gravírozás, "
        "**minden más** (alapértelmezett rétegszín) = raszteres égetendő terület."
    )
    col1, col2 = st.columns([1, 2])

    with col1:
        seb = sebessegek_beallitasa("dxf")
        dxf_file = st.file_uploader("Válassz DXF fájlt", type=["dxf"], key="dxf_uploader")

    with col2:
        if not dxf_file:
            return
        if ezdxf is None:
            st.error("Hiányzó csomag! A requirements.txt-be írd bele: ezdxf")
            st.stop()

        t_start = time.perf_counter()
        eredmeny = idokorlatos_futtatas(
            elemez_dxf,
            dxf_file.getvalue(),
            seb["v_raster"],
            seb["scan_gap_mm"],
        )
        if eredmeny is None:
            st.error(
                f"A fájl feldolgozása túllépte a {MAX_FELDOLGOZASI_IDO_MP} másodperces "
                "időkorlátot - valószínűleg túl sok vagy túl bonyolult entitást tartalmaz."
            )
            st.stop()

        b_len, r_len, t_rast, ent_count = eredmeny
        szamit_es_megjelenit(
            b_len,
            r_len,
            t_rast,
            seb,
            idotartam_mp=time.perf_counter() - t_start,
            debug_szoveg=f"{ent_count} entitás",
        )
