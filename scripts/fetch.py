"""Télécharge l'historique hebdo de TTE.PA (Yahoo Finance, repli Stooq) -> data/tte.csv + data/meta.json"""
import io, json, sys, datetime as dt
import pandas as pd

TICKER, STOOQ = "TTE.PA", "tte.fr"

def yahoo():
    import yfinance as yf
    h = yf.Ticker(TICKER).history(period="max", interval="1wk", auto_adjust=False)
    h = h.reset_index()
    h["Date"] = pd.to_datetime(h["Date"]).dt.strftime("%Y-%m-%d")
    return h[["Date", "Adj Close", "Close"]].dropna(), "Yahoo Finance"

def stooq():
    import requests
    r = requests.get(f"https://stooq.com/q/d/l/?s={STOOQ}&i=w", timeout=30)
    r.raise_for_status()
    h = pd.read_csv(io.StringIO(r.text))
    h["Adj Close"] = h["Close"]
    return h[["Date", "Adj Close", "Close"]].dropna(), "Stooq (non ajusté)"

df = src = None
for fn in (yahoo, stooq):
    try:
        df, src = fn()
        if len(df) > 500:
            break
    except Exception as e:
        print(f"{fn.__name__} KO: {e}", file=sys.stderr)
if df is None or len(df) < 500:
    sys.exit("Aucune source exploitable")

df.to_csv("data/tte.csv", index=False)
json.dump({"updated": dt.date.today().isoformat(), "rows": len(df), "source": src,
           "first": df["Date"].iloc[0], "last": df["Date"].iloc[-1]},
          open("data/meta.json", "w"))
print(f"{len(df)} lignes ({src}) {df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}")
