#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAY-TRADING BOT — Adim 1: COK-SINYALLI INTRADAY MOTOR (Secici + Dengeli)
=======================================================================
5 dakikalik barlar uzerinde cok sinyalli skorlama.
Mizac: SECICI — guclu firsat icin HEM hacim HEM volatilite teyidi sart.
Denge: kirilim / momentum / tepki alimi yollari esit agirlikta.

BIST acikken calistirmak en iyisi. Henuz islem yok (giris/cikis Adim 2).
"""

import sys
import subprocess


def _ensure(pkg, imp=None):
    imp = imp or pkg
    try:
        __import__(imp)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])


for _p, _i in [("pandas", "pandas"), ("numpy", "numpy"), ("yfinance", "yfinance")]:
    _ensure(_p, _i)

import numpy as np
import pandas as pd
import yfinance as yf

TAKIP = ["BIMAS", "ASELS", "THYAO", "EREGL", "TUPRS", "FROTO", "SISE", "TOASO"]
ARALIK = "5m"

# --- MIZAC AYARLARI: Secici + Dengeli (rahatca degistir) ---
RVOL_ESIK = 2.0     # hacim teyidi: ort. kac kati (yuksek = daha secici)
ATR_ESIK = 1.25     # volatilite: ATR ort.'nin kac kati genislesin
RSI_OS = 28         # asiri satim esigi (dusuk = daha secici)
ACILIS_BAR = 6      # acilis araligi = ilk 30 dk (6 x 5dk)
MIN_SKOR_IZLE = 3   # 'IZLE' icin minimum sinyal sayisi


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def analiz(kod):
    df = yf.Ticker(kod + ".IS").history(period="5d", interval=ARALIK)
    if df is None or len(df) < 30:
        return None
    df = df.dropna()

    df["EMA9"] = ema(df["Close"], 9)
    df["EMA21"] = ema(df["Close"], 21)
    df["RSI"] = rsi(df["Close"])
    df["ATR"] = atr(df)
    df["BB_mid"] = df["Close"].rolling(20).mean()
    df["BB_std"] = df["Close"].rolling(20).std()
    df["BB_alt"] = df["BB_mid"] - 2 * df["BB_std"]
    df["Don20"] = df["High"].rolling(20).max().shift(1)
    df["RVOL"] = df["Volume"] / df["Volume"].rolling(20).mean()

    son_gun = df.index[-1].date()
    seans = df[df.index.map(lambda t: t.date() == son_gun)]
    if len(seans) < 2:
        seans = df.tail(ACILIS_BAR + 2)

    tp = (seans["High"] + seans["Low"] + seans["Close"]) / 3
    vwap = float((tp * seans["Volume"]).cumsum().iloc[-1] /
                 seans["Volume"].cumsum().iloc[-1])
    orb_high = float(seans["High"].iloc[:ACILIS_BAR].max())
    gun_yuksek = float(seans["High"].max())
    gun_dusuk = float(seans["Low"].min())
    gun_acilis = float(seans["Open"].iloc[0])

    son = df.iloc[-1]
    fiyat = float(son["Close"])
    atr_now = float(son["ATR"])
    atr_ref = float(df["ATR"].rolling(50).mean().iloc[-1])
    rvol = float(son["RVOL"]) if not pd.isna(son["RVOL"]) else 0
    rsi_now = float(son["RSI"])

    sig = {
        "orb_break": fiyat > orb_high,
        "donchian": fiyat >= float(son["Don20"]) if not pd.isna(son["Don20"]) else False,
        "above_vwap": fiyat > vwap,
        "ema_up": son["EMA9"] > son["EMA21"],
        "rvol_high": rvol >= RVOL_ESIK,
        "atr_expand": atr_now > ATR_ESIK * atr_ref if atr_ref else False,
        "rsi_oversold": rsi_now < RSI_OS,
        "bb_alt": fiyat <= float(son["BB_alt"]) if not pd.isna(son["BB_alt"]) else False,
    }

    # Dengeli puan: her sinyal 1 puan
    puan, sebep = 0, []
    etiket = {
        "orb_break": "acilis araligi kirildi (ORB)",
        "donchian": "son 20 bar tepesi kirildi",
        "above_vwap": "VWAP ustunde",
        "ema_up": "EMA9>EMA21 (momentum)",
        "rvol_high": f"hacim {rvol:.1f}x (TEYIT)",
        "atr_expand": "volatilite genisliyor (TEYIT)",
    }
    for s in ["orb_break", "donchian", "above_vwap", "ema_up", "rvol_high", "atr_expand"]:
        if sig[s]:
            puan += 1
            sebep.append(etiket[s])

    rev_sebep = []
    if sig["rsi_oversold"]:
        rev_sebep.append(f"RSI {rsi_now:.0f} asiri satim")
    if sig["bb_alt"]:
        rev_sebep.append("Bollinger alt bandinda")

    # --- SECICI KARAR: guclu cagri icin HEM hacim HEM volatilite teyidi sart ---
    teyit = sig["rvol_high"] and sig["atr_expand"]
    breakout = sig["orb_break"] or sig["donchian"]
    momentum = sig["ema_up"] and sig["above_vwap"]
    reversion = sig["rsi_oversold"] and sig["bb_alt"]

    if breakout and teyit and (sig["above_vwap"] or sig["ema_up"]):
        kurulum, karar = "KIRILIM", "GUCLU FIRSAT (long)"
    elif momentum and teyit:
        kurulum, karar = "MOMENTUM", "FIRSAT (trend long)"
    elif reversion and sig["rvol_high"] and not sig["ema_up"]:
        kurulum, karar = "TEPKI ALIMI", "ADAY (mean-reversion)"
        sebep = rev_sebep + [f"hacim {rvol:.1f}x (TEYIT)"]
        puan = 2 + len(rev_sebep)
    elif puan >= MIN_SKOR_IZLE and (sig["rvol_high"] or sig["atr_expand"]):
        kurulum, karar = "OLUSUYOR", "IZLE"
    else:
        kurulum, karar = "-", "BEKLE"

    return {
        "kod": kod, "fiyat": fiyat, "skor": puan, "kurulum": kurulum,
        "karar": karar, "sebep": sebep, "vwap": round(vwap, 2),
        "rsi": round(rsi_now), "rvol": round(rvol, 1),
        "atr_pct": round(atr_now / fiyat * 100, 2),
        "gun_range_pct": round((gun_yuksek - gun_dusuk) / gun_acilis * 100, 1),
    }


if __name__ == "__main__":
    print("=" * 70)
    print(" INTRADAY MOTOR — Secici + Dengeli (5dk) ")
    print(f" RVOL>={RVOL_ESIK} · ATR>{ATR_ESIK}x · RSI<{RSI_OS} ")
    print("=" * 70)

    sonuc = []
    for k in TAKIP:
        try:
            r = analiz(k)
            if r:
                sonuc.append(r)
        except Exception as e:
            print(f"  {k}: hata {e!r}")

    sonuc.sort(key=lambda x: x["skor"], reverse=True)

    print("\nFIRSAT SIRALAMASI:")
    for r in sonuc:
        print(f"  {r['kod']:<7} skor {r['skor']:>2}  [{r['kurulum']:<11}] {r['karar']}")

    print("\n" + "-" * 70)
    print("DETAY")
    print("-" * 70)
    for r in sonuc:
        print(f"\n{r['kod']}  {r['fiyat']:.2f} TL  |  skor {r['skor']} -> {r['karar']}")
        print(f"   VWAP {r['vwap']} · RSI {r['rsi']} · RVOL {r['rvol']}x · "
              f"ATR %{r['atr_pct']} · gun araligi %{r['gun_range_pct']}")
        for s in r["sebep"]:
            print(f"   + {s}")
        if not r["sebep"]:
            print("   (belirgin sinyal yok)")
    print("\n" + "=" * 70)
