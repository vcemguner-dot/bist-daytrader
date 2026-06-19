# BIST Intraday Paper-Trading Bot

A multi-signal **intraday** paper-trading bot for Borsa İstanbul (virtual money,
no broker). It runs as a continuous loop on your machine during market hours,
scores stocks on a rich set of intraday signals, opens positions on high-confirmation
setups, and manages each position with ATR-based stop-loss, take-profit and trailing
stop — closing everything before the bell.

## How it works

Every ~5 minutes while BIST is open (10:00–18:00 Istanbul, weekdays):
1. **Signals** (`sinyal_motoru.py`): on 5-minute bars, computes EMA/RSI/ATR/Bollinger,
   session VWAP, opening-range, Donchian high, relative volume and ATR-expansion, then
   classifies each stock (breakout / momentum / mean-reversion / wait). Selective: a
   "FIRSAT" requires both volume **and** volatility confirmation.
2. **Risk engine** (`risk_motoru.py`): position sizing risks a fixed % of capital per
   trade; exits via ATR-based stop-loss, take-profit, trailing stop, and end-of-day close.
3. **Loop** (`bot.py`): checks exits on open positions, then opens new high-conviction
   setups into free slots, logs every action with its reason, and persists state.

## Run

```bash
pip install -r requirements.txt
python bot.py          # continuous loop (run during market hours, Ctrl+C to stop)
python bot.py once     # single cycle (for testing)
```

State and trade log are written to `durum/` (durum.json, islemler.json).

## Tuning

- Signal thresholds (selectivity): top of `sinyal_motoru.py` — `RVOL_ESIK`, `ATR_ESIK`, `RSI_OS`.
- Risk parameters: top of `risk_motoru.py` — `STOP_ATR`, `HEDEF_ATR`, `TRAIL_ATR`, `RISK_PCT`, `MAX_POZISYON`.
- Watchlist: `TAKIP` in `sinyal_motoru.py` (banks/holdings excluded — non-standard statements).

## Important notes

- **Paper trading only.** Virtual balance, no real orders, no broker. Not investment advice.
- Free intraday data (yfinance) is **~15 minutes delayed** and limited — this is a
  simulation / learning platform, not a real-time trading edge.
- Day trading is, after costs, one of the hardest strategies to make profitable. Treat
  this as an engineering and learning project.
- The bot only runs while your machine is on; it closes all positions before the close.
