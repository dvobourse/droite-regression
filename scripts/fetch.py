"""Historique hebdo (max dispo, 25 ans au plus) des valeurs de data/tickers.csv -> data/sbf120.json
Une valeur introduite il y a moins de 20 ans garde tout son historique depuis sa création."""
import csv, json, time, datetime as dt
import yfinance as yf

stocks, failed = {}, []
for row in csv.DictReader(open("data/tickers.csv", encoding="utf-8")):
    t, name = row["ticker"].strip(), row["name"].strip()
    h = None
    for attempt in range(3):
        try:
            h = yf.Ticker(t).history(period="max", interval="1wk", auto_adjust=False)
            if len(h) > 0:
                break
        except Exception as e:
            print(f"{t}: {e}")
        time.sleep(2)
    if h is None or len(h) < 52:
        failed.append(t); print(f"KO {t}"); continue
    col = "Adj Close" if "Adj Close" in h else "Close"
    h = h[[col]].dropna()
    h = h[h[col] > 0]
    cut = h.index[-1] - dt.timedelta(days=25 * 365)
    h = h[h.index >= cut]
    days = [int(i.tz_localize(None).timestamp() // 86400) if i.tzinfo else int(i.timestamp() // 86400) for i in h.index]
    stocks[t] = {"n": name, "d": days, "p": [round(float(v), 4) for v in h[col]]}
    print(f"OK {t:10s} {len(days):5d} pts depuis {h.index[0].date()}")
    time.sleep(0.4)

if len(stocks) < 20:
    raise SystemExit("Trop peu de valeurs récupérées, on ne remplace pas les données.")
json.dump({"updated": dt.date.today().isoformat(), "source": "Yahoo Finance (Adj Close, hebdo)", "failed": failed, "stocks": stocks},
          open("data/sbf120.json", "w"), separators=(",", ":"))
print(f"{len(stocks)} valeurs, {len(failed)} échecs: {failed}")
