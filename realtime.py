"""
Valós idejű Firestore szinkronizáció.

Működés:
- Az on_snapshot listenerek egy háttérszálon futnak, és minden változásnál
  (bárki bármelyik eszközön ment) automatikusan lefutnak.
- A kapott adatot egy folyamat-szintű (process-wide), lock-kal védett
  memóriában tároljuk - NEM st.session_state-ben, mert a listener callback
  nem egy adott felhasználói session kontextusában fut.
- A start_listeners() @st.cache_resource-szal van dekorálva, így az egész
  app életciklusa alatt csak EGYSZER indul el (nem session-önként) -
  ez elengedhetetlen, különben minden újranyitott böngészőfül saját
  listenert indítana, és feleslegesen sok Firestore olvasást generálna.
- A Streamlit oldalak a get_gepek() / get_kalkulaciok() függvényekkel
  olvassák ki a legfrissebb, már memóriában lévő adatot - ez NEM jár
  Firestore olvasási költséggel, csak a helyi cache-t adja vissza.
"""

import threading
from google.cloud import firestore

_lock = threading.Lock()
_state = {
    "gepek": None,       # dict: a "beallitasok/gepek" dokumentum tartalma
    "kalkulaciok": [],   # list[dict]: a "kalkulaciok" kollekció (max 100, dátum szerint csökkenő)
}


def _on_gepek_snapshot(doc_snapshot, changes, read_time):
    with _lock:
        for doc in doc_snapshot:
            if doc.exists:
                _state["gepek"] = doc.to_dict()


def _on_kalkulaciok_snapshot(col_snapshot, changes, read_time):
    items = []
    for doc in col_snapshot:
        v = doc.to_dict()
        v["id"] = doc.id
        items.append(v)
    with _lock:
        _state["kalkulaciok"] = items


import streamlit as st


@st.cache_resource
def start_listeners(_db):
    """
    _db: a Firestore kliens (aláhúzással kezdődő paraméternév kell,
    hogy Streamlit ne próbálja meg hash-elni - a kliens nem hashelhető).
    Visszatér True-val, hogy a cache_resource egyszerűen jelölhesse "kész" állapotúnak.
    """
    if _db is None:
        return False

    _db.collection("beallitasok").document("gepek").on_snapshot(_on_gepek_snapshot)

    (
        _db.collection("kalkulaciok")
        .order_by("datum", direction=firestore.Query.DESCENDING)
        .limit(100)
        .on_snapshot(_on_kalkulaciok_snapshot)
    )

    return True


def get_gepek():
    """A gépek beállításainak legfrissebb, memóriában cache-elt állapota (vagy None, ha még nem érkezett adat)."""
    with _lock:
        return dict(_state["gepek"]) if _state["gepek"] is not None else None


def get_kalkulaciok():
    """Az archívum legfrissebb, memóriában cache-elt listája (max 100 elem, dátum szerint csökkenő)."""
    with _lock:
        return list(_state["kalkulaciok"])
