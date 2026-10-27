"""Score qualité /7 des valeurs de data/tickers.csv (fondamentaux annuels Yahoo Finance) -> data/quality.json.
Grille adaptée du webinaire #71 (seuils modifiables dans TH). Les fondamentaux changent peu : exécution hebdomadaire."""
import csv, json, time, datetime as dt
import pandas as pd

TH = dict(growth=0.08, margin=0.10, roce=0.15, nd_ebitda=1.0, fcf=0.05, dil=0.03)
LABELS = ["Croissance CA ≥ 8 %/an", "Marge EBITDA ≥ 10 %", "Marge EBITDA en hausse", "ROCE ≥ 15 %",
          "Dette nette < 1× EBITDA", "Marge FCF ≥ 5 %", "Pas de dilution (≤ +3 %)"]

def srow(df, names):
    if df is None or getattr(df, "empty", True): return None
    for n in names:
        if n in df.index:
            s = pd.to_numeric(df.loc[n], errors="coerce").dropna()
            if len(s): return s.sort_index()
    return None

def last(s): return float(s.iloc[-1]) if s is not None and len(s) else None

def compute(inc, bs, cf, info):
    info = info or {}
    rev = srow(inc, ["Total Revenue", "Operating Revenue"]); ebitda = srow(inc, ["EBITDA", "Normalized EBITDA"])
    ebit = srow(inc, ["EBIT", "Operating Income"]); assets = srow(bs, ["Total Assets"])
    cl = srow(bs, ["Current Liabilities", "Total Current Liabilities"]); debt = srow(bs, ["Total Debt"])
    cash = srow(bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
    nd = srow(bs, ["Net Debt"]); shares = srow(bs, ["Ordinary Shares Number", "Share Issued"]); fcf = srow(cf, ["Free Cash Flow"])
    fin = info.get("sector") == "Financial Services"
    m = [None] * 7
    if rev is not None and len(rev) >= 3 and rev.iloc[0] > 0 and rev.iloc[-1] > 0:
        m[0] = (rev.iloc[-1] / rev.iloc[0]) ** (1 / (len(rev) - 1)) - 1
    if rev is not None and ebitda is not None:
        mg = (ebitda / rev).dropna()
        if len(mg): m[1] = float(mg.iloc[-1])
        if len(mg) >= 2: m[2] = float(mg.iloc[-1] - mg.iloc[0])
    e, a, l = last(ebit), last(assets), last(cl)
    if None not in (e, a, l) and a - l > 0: m[3] = e / (a - l)
    ndv = last(nd) if nd is not None else (last(debt) - last(cash) if debt is not None and cash is not None else None)
    eb = last(ebitda)
    if ndv is not None and eb is not None and eb > 0: m[4] = ndv / eb
    if fcf is not None and rev is not None and last(rev): m[5] = last(fcf) / last(rev)
    if shares is not None and len(shares) >= 2 and shares.iloc[0] > 0: m[6] = float(shares.iloc[-1] / shares.iloc[0] - 1)
    c = [None if m[0] is None else m[0] >= TH["growth"], None if m[1] is None else m[1] >= TH["margin"],
         None if m[2] is None else m[2] >= 0, None if m[3] is None else m[3] >= TH["roce"],
         None if m[4] is None else m[4] < TH["nd_ebitda"], None if m[5] is None else m[5] >= TH["fcf"],
         None if m[6] is None else m[6] <= TH["dil"]]
    if fin: c[1] = c[2] = c[3] = c[4] = c[5] = None      # marges EBITDA, ROCE, dette, FCF non pertinents pour banques/assurances
    c = [None if x is None else bool(x) for x in c]
    of = sum(x is not None for x in c); s = sum(bool(x) for x in c)
    rd = lambda v, k=4: None if v is None or v != v else round(float(v), k)
    return {"s": s if of >= 5 else None, "of": of, "c": c, "m": [rd(v) for v in m], "fin": fin, "sec": info.get("sector"),
            "ev": rd(info.get("enterpriseToEbitda"), 2), "pe": rd(info.get("trailingPE"), 2), "mc": info.get("marketCap")}

if __name__ == "__main__":
    import yfinance as yf
    out, failed = {}, []
    for row in csv.DictReader(open("data/tickers.csv", encoding="utf-8")):
        t = row["ticker"].strip(); res = None
        for _ in range(3):
            try:
                tk = yf.Ticker(t); inc = tk.financials
                if inc is None or inc.empty: raise ValueError("pas d'états financiers")
                try: info = tk.info
                except Exception: info = {}
                res = compute(inc, tk.balance_sheet, tk.cashflow, info); break
            except Exception as e:
                print(f"{t}: {e}"); time.sleep(3)
        if res is None: failed.append(t); print("KO", t); continue
        out[t] = res; print(f"OK {t:10s} score {res['s']}/{res['of']}"); time.sleep(1)
    if len(out) < 20: raise SystemExit("Trop peu de valeurs, fichier non remplacé.")
    json.dump({"updated": dt.date.today().isoformat(), "source": "Yahoo Finance (états annuels)", "labels": LABELS, "failed": failed, "q": out},
              open("data/quality.json", "w"), separators=(",", ":"))
    print(len(out), "valeurs,", len(failed), "échecs:", failed)
