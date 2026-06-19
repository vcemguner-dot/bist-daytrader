#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAY-TRADING BOT — Adim 2: GIRIS/CIKIS + RISK MOTORU
===================================================
Pozisyon yonetiminin kalbi. ATR tabanli stop-loss, take-profit,
trailing stop ve gun sonu kapanis. Risk-bazli pozisyon buyuklugu.

Bu dosya cikis mantigini SENTETIK fiyat yollariyla test eder —
boylece piyasa kapali olsa bile her mekanizmanin calistigi gorulur.
"""

# --- RISK AYARLARI (rahatca degistir) ---
STOP_ATR = 1.5      # stop = giris - 1.5*ATR
HEDEF_ATR = 2.5     # hedef = giris + 2.5*ATR  (risk/odul ~1.67)
TRAIL_ATR = 1.5     # zirveden 1.5*ATR geri cekilince cik
RISK_PCT = 0.01     # her islemde sermayenin %1'i riske
MAX_POZISYON = 3    # ayni anda en fazla pozisyon


class Pozisyon:
    """Acik bir paper pozisyonu — kendi stop/hedef/trailing seviyeleriyle."""

    def __init__(self, kod, giris, lot, atr):
        self.kod = kod
        self.giris = giris
        self.lot = lot
        self.atr = atr
        self.stop = giris - STOP_ATR * atr
        self.hedef = giris + HEDEF_ATR * atr
        self.trail_mesafe = TRAIL_ATR * atr
        self.zirve = giris
        self.trailing_stop = giris - self.trail_mesafe

    def kontrol(self, fiyat, gun_sonu=False):
        """Fiyati guncelle, cikis gerekiyor mu karar ver. (aksiyon, sebep)."""
        # Trailing'i yukari tasi (fiyat yeni zirve yaptiysa)
        if fiyat > self.zirve:
            self.zirve = fiyat
            self.trailing_stop = self.zirve - self.trail_mesafe

        if fiyat <= self.stop:
            return "STOP", f"stop-loss {self.stop:.2f} kirildi (zarari kes)"
        if fiyat >= self.hedef:
            return "HEDEF", f"hedef {self.hedef:.2f} ulasildi (kari al)"
        if fiyat <= self.trailing_stop:
            return "TRAILING", (f"trailing stop {self.trailing_stop:.2f} "
                                f"(zirve {self.zirve:.2f}'den geri cekildi)")
        if gun_sonu:
            return "GUNSONU", "gun sonu — pozisyon kapatildi (gece tasinmaz)"
        return "TUT", None

    def kz(self, fiyat):
        return (fiyat / self.giris - 1) * 100


def lot_hesapla(sermaye, fiyat, atr):
    """Risk-bazli lot: sermayenin %RISK_PCT'i, stop mesafesine bolunur."""
    risk_tl = sermaye * RISK_PCT
    stop_mesafe = STOP_ATR * atr
    if stop_mesafe <= 0 or fiyat <= 0:
        return 0
    lot = int(risk_tl / stop_mesafe)
    lot = min(lot, int(sermaye / fiyat))   # nakitten fazlasini alma
    return max(lot, 0)


# ====================================================================
#  TEST: sentetik fiyat yollariyla cikis mantigini dogrula
# ====================================================================
def senaryo(ad, giris, atr, yol, gun_sonu_son=False):
    print(f"\n--- SENARYO: {ad} ---")
    sermaye = 100_000
    lot = lot_hesapla(sermaye, giris, atr)
    p = Pozisyon("TEST", giris, lot, atr)
    print(f"  Giris {giris:.2f} · Lot {lot} · Stop {p.stop:.2f} · "
          f"Hedef {p.hedef:.2f} · Trail mesafe {p.trail_mesafe:.2f}")
    for i, f in enumerate(yol):
        son = gun_sonu_son and i == len(yol) - 1
        aksiyon, sebep = p.kontrol(f, gun_sonu=son)
        if aksiyon == "TUT":
            print(f"  fiyat {f:6.2f} -> TUT   (zirve {p.zirve:.2f}, "
                  f"trailing {p.trailing_stop:.2f})")
        else:
            print(f"  fiyat {f:6.2f} -> {aksiyon}: {sebep}  |  K/Z %{p.kz(f):+.1f}")
            break


if __name__ == "__main__":
    print("=" * 66)
    print(" RISK MOTORU TESTI — ATR=2.00 ornegi ")
    print(f" Stop {STOP_ATR}xATR · Hedef {HEDEF_ATR}xATR · Trail {TRAIL_ATR}xATR · "
          f"risk %{RISK_PCT*100:.0f}")
    print("=" * 66)

    # ATR=2 -> stop 97, hedef 105, trail mesafe 3
    senaryo("Hedef (take-profit)", 100, 2, [100, 101, 103, 104, 106])
    senaryo("Trailing stop (kari korur)", 100, 2, [100, 102, 104, 103.5, 101])
    senaryo("Stop-loss (zarari keser)", 100, 2, [100, 99, 98, 96.5])
    senaryo("Gun sonu kapanis", 100, 2, [100, 100.5, 101], gun_sonu_son=True)

    print("\n" + "=" * 66)
    print(" Cikis mantigi calisiyor. Adim 3'te sinyal motoruyla birlesip ")
    print(" surekli dongude paper islem yapacak. ")
    print("=" * 66)
