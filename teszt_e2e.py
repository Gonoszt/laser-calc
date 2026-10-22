"""End-to-end teszt: minden oldal betölt az új views/ modulokból, hiba nélkül.

Futtatás: python teszt_e2e.py
A fájl-feldolgozás logikáját a teszt_views.py fedi le (valódi SVG/DXF fájlokkal);
itt az oldalak renderelését ellenőrizzük Streamlit AppTest-tel.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1250 konzol miatt

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("arkalkulator.py", default_timeout=30)

# --- 1. Kalkulátor oldal ---
at.run()
assert not at.exception, f"Főoldal hiba: {at.exception}"
cimek = [t.value for t in at.title]
assert any("Kalkulátor" in c for c in cimek), f"Kalkulátor oldal címe hiányzik: {cimek}"
print("✓ Kalkulátor oldal betölt, cím megjelenik")

# --- 2. SVG Időbecslő ---
at.radio[0].set_value("SVG Időbecslő").run()
assert not at.exception, f"SVG oldal hiba: {at.exception}"
cimek = [t.value for t in at.title]
assert any("SVG" in c for c in cimek), f"SVG oldal címe hiányzik: {cimek}"
feltoltok = at.get("file_uploader")
assert len(feltoltok) == 1, "SVG oldalon nincs fájl-feltöltő widget"
sebessegek = [ni.value for ni in at.number_input]
assert sebessegek == [300, 254, 25, 20], f"Sebesség-értékek eltérnek: {sebessegek}"
print("✓ SVG oldal betölt: feltöltő + 4 widget (raszter 300, DPI 254, kék 25, piros 20)")

# --- 3. DXF Időbecslő ---
at.radio[0].set_value("DXF Időbecslő").run()
assert not at.exception, f"DXF oldal hiba: {at.exception}"
cimek = [t.value for t in at.title]
assert any("DXF" in c for c in cimek), f"DXF oldal címe hiányzik: {cimek}"
feltoltok = at.get("file_uploader")
assert len(feltoltok) == 1, "DXF oldalon nincs fájl-feltöltő widget"
sebessegek = [ni.value for ni in at.number_input]
assert sebessegek == [300, 254, 25, 20], f"Sebesség-értékek eltérnek: {sebessegek}"
print("✓ DXF oldal betölt: feltöltő + 4 widget (raszter 300, DPI 254, kék 25, piros 20)")

# --- 4. Archívum oldal (admin menübelépés session_state-tel) ---
at.session_state.logged_in = True
at.run()  # újrafuttatás, hogy a menüben megjelenjen az Archívum opció
assert not at.exception, f"Hiba az admin belépés után: {at.exception}"
assert "Archívum" in at.radio[0].options, (
    f"Archívum opció hiányzik a menüben: {at.radio[0].options}")
at.radio[0].set_value("Archívum").run()
assert not at.exception, f"Archívum oldal hiba: {at.exception}"
print("✓ Archívum oldal betölt (Firestore-figyelmeztetés várt secrets nélkül)")

print("\nMinden e2e teszt sikeres! ✔")
sys.exit(0)
