"""
Day-trader cuzdani — paper bakiye, acik pozisyonlar, kapali islem gunlugu.
Pozisyon objeleri JSON'a dict olarak kaydedilir, geri yuklenir.
"""

import os
import json
import risk_motoru as RM

DURUM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "durum")
STATE = os.path.join(DURUM, "durum.json")
LOG = os.path.join(DURUM, "islemler.json")
BASLANGIC_NAKIT = 100_000


def _yaz(dosya, veri):
    os.makedirs(DURUM, exist_ok=True)
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(veri, f, indent=2, ensure_ascii=False)


def yukle():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"nakit": BASLANGIC_NAKIT, "acik": {}, "kapali": [],
            "gun": None, "bugun_islem": []}


def kaydet(state):
    _yaz(STATE, state)


def poz_to_dict(p):
    return dict(p.__dict__)


def poz_from_dict(d):
    p = RM.Pozisyon(d["kod"], d["giris"], d["lot"], d["atr"])
    p.__dict__.update(d)
    return p


def log_ekle(kayit):
    log = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as f:
            log = json.load(f)
    log.append(kayit)
    _yaz(LOG, log)
