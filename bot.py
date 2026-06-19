"""
DAY-TRADING BOT — Adim 3: SUREKLI DONGU (paper)
===============================================
Sinyal motoru + risk motoru + cuzdani birlestirir.
Piyasa acikken her PERIYOT'ta: cikislari kontrol et -> gun sonu kapat ->
yeni firsatlara gir -> logla -> kaydet.

Calistir:
    python bot.py          # surekli dongu (BIST saatlerinde calisir)
    python bot.py once     # tek tur (test icin)
"""

import sys
import time
from datetime import datetime, time as dtime

import sinyal_motoru as SM
import risk_motoru as RM
import cuzdan as C

BIST_ACILIS = dtime(10, 0)
BIST_KAPANIS = dtime(18, 0)
GUNSONU_ESIK = dtime(17, 50)   # son 10 dk: yeni giris yok, kapanisa hazirlan
PERIYOT_SN = 300               # 5 dakika


def piyasa_acik(now):
    return now.weekday() < 5 and BIST_ACILIS <= now.time() <= BIST_KAPANIS


def tur(state):
    now = datetime.now()
    zaman = now.strftime("%Y-%m-%d %H:%M")
    gun_sonu = now.time() >= GUNSONU_ESIK

    # Yeni gun: 'bugun islem yapilan semboller' listesini sifirla
    bugun = now.strftime("%Y-%m-%d")
    if state.get("gun") != bugun:
        state["gun"] = bugun
        state["bugun_islem"] = []

    # Sinyalleri topla
    sinyaller = {}
    for kod in SM.TAKIP:
        try:
            r = SM.analiz(kod)
            if r:
                sinyaller[kod] = r
        except Exception:
            pass

    olaylar = []

    # 1) Acik pozisyonlarin cikis kontrolu
    for kod in list(state["acik"]):
        p = C.poz_from_dict(state["acik"][kod])
        fiyat = sinyaller.get(kod, {}).get("fiyat", p.giris)
        aksiyon, sebep = p.kontrol(fiyat, gun_sonu=gun_sonu)
        state["acik"][kod] = C.poz_to_dict(p)   # guncel zirve/trailing'i yaz
        if aksiyon != "TUT":
            kz = p.kz(fiyat)
            state["nakit"] += p.lot * fiyat
            kayit = {"zaman": zaman, "kod": kod, "aksiyon": "SAT", "tip": aksiyon,
                     "fiyat": round(fiyat, 2), "lot": p.lot,
                     "kz_pct": round(kz, 2), "sebep": sebep}
            state["kapali"].append(kayit)
            C.log_ekle(kayit)
            del state["acik"][kod]
            olaylar.append(f"[SAT/{aksiyon}] {kod} @ {fiyat:.2f} (K/Z %{kz:+.1f}) — {sebep}")

    # 2) Yeni girisler (gun sonu degil + bos slot var)
    if not gun_sonu:
        for kod, r in sinyaller.items():
            if len(state["acik"]) >= RM.MAX_POZISYON:
                break
            if kod in state["acik"] or kod in state.get("bugun_islem", []):
                continue
            if "FIRSAT" in r["karar"]:           # GUCLU FIRSAT / FIRSAT
                fiyat = r["fiyat"]
                atr_abs = r["atr_pct"] / 100 * fiyat
                lot = RM.lot_hesapla(state["nakit"], fiyat, atr_abs)
                if lot > 0:
                    state["nakit"] -= lot * fiyat
                    p = RM.Pozisyon(kod, fiyat, lot, atr_abs)
                    state["acik"][kod] = C.poz_to_dict(p)
                    state.setdefault("bugun_islem", []).append(kod)
                    sebep = "; ".join(r["sebep"])
                    kayit = {"zaman": zaman, "kod": kod, "aksiyon": "AL",
                             "fiyat": round(fiyat, 2), "lot": lot,
                             "stop": round(p.stop, 2), "hedef": round(p.hedef, 2),
                             "sebep": f"{r['karar']} — {sebep}"}
                    C.log_ekle(kayit)
                    olaylar.append(f"[AL] {kod} @ {fiyat:.2f} x{lot} "
                                   f"(stop {p.stop:.2f}, hedef {p.hedef:.2f}) — {r['karar']}")

    C.kaydet(state)

    # Ozet
    acik_deger = sum(d["lot"] * sinyaller.get(k, {}).get("fiyat", d["giris"])
                     for k, d in state["acik"].items())
    toplam = state["nakit"] + acik_deger
    ozet = (f"[{zaman}] {'GUN SONU' if gun_sonu else 'aktif'} | "
            f"nakit {state['nakit']:,.0f} | acik {len(state['acik'])} | "
            f"toplam {toplam:,.0f} TL")
    if olaylar:
        ozet += "\n  " + "\n  ".join(olaylar)
    else:
        ozet += "\n  (yeni islem yok)"
    return state, ozet


def main():
    tek = len(sys.argv) > 1 and sys.argv[1] == "once"
    state = C.yukle()
    print("Day-trading bot basladi." + (" (tek tur)" if tek else ""))

    while True:
        now = datetime.now()
        if piyasa_acik(now):
            state, ozet = tur(state)
            print(ozet)
        else:
            print(f"[{now:%H:%M}] piyasa kapali — bekleniyor.")
        if tek:
            break
        time.sleep(PERIYOT_SN)


if __name__ == "__main__":
    main()
