"""
Funkcionális teszt a szétbontás után:
- views.svg_idobecsl.elemez_svg valódi SVG-en
- views.dxf_idobecsl.elemez_dxf valódi DXF-en
- views.kozos.idokorlatos_futtatas: normál futás ÉS időkorlát
- views.kozos.szamit_es_megjelenit matematikája (st nélkül, stub-al)
Futás: a projekt mappából: python teszt_views.py
"""
import os
import sys
import tempfile
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

eredmenyek = []


def check(nev, feltetel, reszlet=""):
    allapot = "RENDBEN" if feltetel else "HIBA"
    eredmenyek.append(feltetel)
    print(f"[{allapot}] {nev}" + (f" -- {reszlet}" if reszlet else ""))


# --- 1) SVG elemzés ---
from views.svg_idobecsl import elemez_svg

# 10x10 mm-es viewBox: kek vonal (10mm átló), piros vonal (10mm), fekete kitöltött négyzet (raszter)
svg_teszt = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="10mm" viewBox="0 0 10 10">
  <path d="M0 0 L10 10" stroke="#0000ff" fill="none"/>
  <path d="M0 10 L10 0" stroke="#ff0000" fill="none"/>
  <path d="M1 1 L9 1 L9 9 L1 9 Z" stroke="#000000" fill="#000000"/>
</svg>
"""
b_len, r_len, t_rast, n_paths = elemez_svg(
    svg_teszt.encode("utf-8"), scaling=1.0, css_map={}, v_raster=300, scan_gap_mm=0.1
)
check("SVG: 3 útvonal találva", n_paths == 3, f"n={n_paths}")
check("SVG: kék hossz ~14.14mm", abs(b_len - 14.142) < 0.05, f"b_len={b_len:.3f}")
check("SVG: piros hossz ~14.14mm", abs(r_len - 14.142) < 0.05, f"r_len={r_len:.3f}")
check("SVG: raszter idő > 0", t_rast > 0, f"t_rast={t_rast:.4f} perc")

# scaling: width=20mm viewBox=10 -> 2x kellene, itt width=10mm -> scaling=1
# Ellenőrizzük a scaling számítást is a modul belső függvényével
from views.svg_idobecsl import _szamit_scaling

sc = _szamit_scaling('<svg width="20mm" viewBox="0 0 10 10"/>')
check("SVG: scaling 20mm/10egység = 2.0", abs(sc - 2.0) < 1e-9, f"scaling={sc}")
sc2 = _szamit_scaling('<svg width="5cm" viewBox="0 0 100 100"/>')
check("SVG: scaling 5cm=50mm/100 = 0.5", abs(sc2 - 0.5) < 1e-9, f"scaling={sc2}")

# --- 2) DXF elemzés ---
from views.dxf_idobecsl import elemez_dxf

import ezdxf

doc = ezdxf.new()
msp = doc.modelspace()
msp.add_line((0, 0), (10, 0), dxfattribs={"color": 1})   # piros: 10mm
msp.add_line((0, 0), (0, 5), dxfattribs={"color": 5})    # kék: 5mm
msp.add_line((0, 0), (3, 4), dxfattribs={"color": 7})    # fehér = raszter
buf = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False)
doc.saveas(buf.name)
with open(buf.name, "rb") as f:
    dxf_bajtok = f.read()
buf.close()
os.unlink(buf.name)

b2, r2, t2, n_ent = elemez_dxf(dxf_bajtok, v_raster=300, scan_gap_mm=0.1)
check("DXF: 3 entitás", n_ent == 3, f"n={n_ent}")
check("DXF: piros = 10mm", abs(r2 - 10.0) < 1e-6, f"r_len={r2}")
check("DXF: kék = 5mm", abs(b2 - 5.0) < 1e-6, f"b_len={b2}")
check("DXF: raszter idő > 0", t2 > 0, f"t_rast={t2:.6f} perc")

# --- 3) idokorlatos_futtatas ---
from views.kozos import idokorlatos_futtatas

t0 = time.perf_counter()
res = idokorlatos_futtatas(lambda x: x * 2, 21)
dt = time.perf_counter() - t0
check("Timeout-futtató: normál eredmény", res == 42, f"res={res}, {dt:.3f}s")

t0 = time.perf_counter()
res = idokorlatos_futtatas(lambda: time.sleep(5), max_mp=1)
dt = time.perf_counter() - t0
check("Timeout-futtató: timeout -> None", res is None)
check(
    "Timeout-futtató: NEM várja meg a szálat (max 2.5s)",
    dt < 2.5,
    f"eltelt={dt:.2f}s (a régi kód itt 5s-ig blokkolt volna)",
)

# --- 4) szamit_es_megjelenit matematikája (st stub) ---
# A st.success/caption/link_button hívásokat kigyűjtjük, hogy ellenőrizzük a számítást.
import views.kozos as kozos_mod

fogott = {}
kozos_mod.st.success = lambda msg: fogott.setdefault("success", msg)
kozos_mod.st.caption = lambda msg: fogott.setdefault("caption", msg)
kozos_mod.st.link_button = lambda label, url: fogott.setdefault("url", url)

seb = {"v_raster": 300, "dpi": 254, "scan_gap_mm": 0.1, "v_blue": 25, "v_red": 20}
total = kozos_mod.szamit_es_megjelenit(
    b_len=25 * 60 * 0.5,  # 25mm/s * 30s = 750mm -> (750/25)*1.15/60 = 0.575 perc
    r_len=20 * 60 * 0.5,  # -> 0.575 perc
    t_rast=0.25,
    seb=seb,
    idotartam_mp=1.234,
    debug_szoveg="3 útvonal",
)
varakozas = round((750 / 25) * 1.15 / 60 + (600 / 20) * 1.15 / 60 + 0.25, 2)
check("Számítás: total = vektor1 + vektor2 + raszter", abs(total - varakozas) < 1e-9,
      f"total={total}, várt={varakozas}")
check("Eredmény-siker üzenet", fogott.get("success") == f"Becsült idő: {total} perc",
      str(fogott.get("success")))
check("Caption debug szöveggel", "3 útvonal" in fogott.get("caption", ""),
      str(fogott.get("caption")))
check("Átvétel link a helyes gtime-tal", fogott.get("url") == f"/?gtime={total}",
      str(fogott.get("url")))

# --- Összegzés ---
print()
hiba = eredmenyek.count(False)
print(f"{'MINDEN TESZT SIKERES' if hiba == 0 else f'{hiba} TESZT HIBÁS'} ({len(eredmenyek)} ellenőrzés)")
sys.exit(0 if hiba == 0 else 1)
