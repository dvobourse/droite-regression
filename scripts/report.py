"""Rapport hebdo du screener : lit data/sbf120.json, calcule z-scores (même méthode que le dashboard),
envoie un mail HTML via Gmail SMTP. Sans mot de passe défini : écrit report.html (test à blanc)."""
import json, math, os, smtplib, ssl, sys, datetime as dt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

TO = os.environ.get("MAIL_TO", "dvobourse@gmail.com")
USER, PWD = os.environ.get("GMAIL_ADDRESS", ""), os.environ.get("GMAIL_APP_PASSWORD", "")
YEARS, R2_MIN = 20, float(os.environ.get("R2_MIN", "0.5"))
SITE = "https://dvobourse.github.io/droite-regression/"
ZN = [("Achat fort", "#15803d"), ("Zone d'achat", "#65a30d"), ("Neutre", "#6b7280"), ("Cher", "#ea580c"), ("Surévalué", "#b91c1c")]

# Garde-fou horaire : cron en UTC, on n'envoie qu'à 9h heure de Paris (hiver/été)
now = dt.datetime.now(ZoneInfo("Europe/Paris"))
if os.environ.get("FORCE") != "1" and now.hour != 9:
    print(f"Il est {now:%H:%M} à Paris : pas d'envoi."); sys.exit(0)

def zi(z): return 0 if z <= -2 else 1 if z <= -1 else 2 if z < 1 else 3 if z < 2 else 4

def fit(d, p):
    last = d[-1]; cut = last - YEARS * 365.25
    i0 = next(i for i, x in enumerate(d) if x >= cut)
    n = len(d) - i0
    if n < 52: return None
    X = [(d[i] - d[i0]) / 365.25 for i in range(i0, len(d))]
    Y = [math.log(p[i]) for i in range(i0, len(d))]
    mx, my = sum(X) / n, sum(Y) / n
    sxx = sum((x - mx) ** 2 for x in X); sxy = sum((x - mx) * (y - my) for x, y in zip(X, Y))
    syy = sum((y - my) ** 2 for y in Y)
    b = sxy / sxx; a = my - b * mx
    sse = sum((y - a - b * x) ** 2 for x, y in zip(X, Y))
    sd = math.sqrt(sse / (n - 2))
    return {"z": (Y[-1] - a - b * X[-1]) / sd, "r2": 1 - sse / syy, "yrs": (d[-1] - d[i0]) / 365.25,
            "short": d[0] > cut + 45, "px": p[-1]}

D = json.load(open("data/sbf120.json", encoding="utf-8"))
rows = []
for t, s in D["stocks"].items():
    f = fit(s["d"], s["p"])
    if not f or f["r2"] < R2_MIN: continue
    g = fit(s["d"][:-1], s["p"][:-1])          # situation la semaine précédente
    f.update(t=t, name=s["n"], zp=g["z"] if g else None, zone=zi(f["z"]))
    f["zonep"] = zi(g["z"]) if g else None
    rows.append(f)

cnt = [sum(1 for r in rows if r["zone"] == i) for i in range(5)]
last_day = dt.date(1970, 1, 1) + dt.timedelta(days=max(s["d"][-1] for s in D["stocks"].values()))

def tbl(title, rs, empty):
    h = f'<h3 style="margin:18px 0 6px">{title}</h3>'
    if not rs: return h + f'<p style="color:#6b7280">{empty}</p>'
    th = "".join(f'<th style="text-align:{"left" if i==0 else "right"};padding:5px 8px;border-bottom:2px solid #ddd;color:#6b7280;font-size:12px">{c}</th>'
                 for i, c in enumerate(["Valeur", "Cours €", "z", "z sem. préc.", "Zone", "R²", "Histor."]))
    body = ""
    for r in rs:
        zname, zcol = ZN[r["zone"]]
        zp = "–" if r["zp"] is None else f'{r["zp"]:+.2f}'
        td = 'style="padding:5px 8px;border-bottom:1px solid #eee;text-align:right"'
        body += (f'<tr><td style="padding:5px 8px;border-bottom:1px solid #eee">{r["name"]} <span style="color:#9ca3af;font-size:11px">{r["t"].replace(".PA","")}</span></td>'
                 f'<td {td}>{r["px"]:.2f}</td><td {td}><b>{r["z"]:+.2f}</b></td><td {td}>{zp}</td>'
                 f'<td {td}><span style="background:{zcol};color:#fff;border-radius:4px;padding:1px 6px;font-size:12px">{zname}</span></td>'
                 f'<td {td}>{r["r2"]:.2f}</td><td {td}>{r["yrs"]:.1f} ans{" ⚠" if r["short"] else ""}</td></tr>')
    return h + f'<table style="border-collapse:collapse;width:100%;font-size:13px"><tr>{th}</tr>{body}</table>'

buy = sorted([r for r in rows if r["z"] <= -1], key=lambda r: r["z"])
exp = sorted([r for r in rows if r["z"] >= 1], key=lambda r: -r["z"])
chg = sorted([r for r in rows if r["zonep"] is not None and r["zonep"] != r["zone"]], key=lambda r: r["z"])
entr = [r for r in chg if r["zone"] <= 1 and r["zonep"] > r["zone"]]

kp = "".join(f'<td style="padding:8px 12px;border-left:5px solid {c};background:#f6f7f9"><div style="font-size:11px;color:#6b7280">{n}</div><b style="font-size:20px">{cnt[i]}</b></td><td width="6"></td>'
             for i, (n, c) in enumerate(ZN))
html = f'''<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:760px;margin:auto;color:#1a1d21">
<h2 style="margin:0">Screener SBF 120 – régression log {YEARS} ans</h2>
<div style="color:#6b7280;font-size:13px;margin:2px 0 12px">Données au {last_day:%d/%m/%Y} · {len(rows)} valeurs analysées (R² ≥ {R2_MIN:g}) · mise à jour des données : {D["updated"]}</div>
<table style="border-collapse:collapse"><tr>{kp}</tr></table>
{tbl("Nouvelles entrées en zone d'achat cette semaine", entr, "Aucune valeur n'est entrée en zone d'achat cette semaine.")}
{tbl(f"Zone d'achat et achat fort (z ≤ −1) – {len(buy)} valeurs", buy[:30], "Aucune valeur.")}
{tbl(f"Cher et surévalué (z ≥ +1) – {len(exp)} valeurs", exp[:15], "Aucune valeur.")}
<p style="margin-top:18px"><a href="{SITE}">Ouvrir le dashboard</a> · ⚠ = historique plus court que {YEARS} ans · z = écart du cours à la droite de régression, en écarts-types.</p>
<p style="color:#9ca3af;font-size:11px">Valeurs en R² &lt; {R2_MIN:g} exclues : la tendance y explique mal le cours, le signal est peu fiable.</p></div>'''
subject = f"Screener SBF 120 {last_day:%d/%m} : {cnt[0]+cnt[1]} en zone d'achat, {cnt[4]} surévalués"

if not (USER and PWD):
    open("report.html", "w", encoding="utf-8").write(html); print("Pas d'identifiants : report.html écrit.", subject); sys.exit(0)
m = MIMEMultipart("alternative"); m["Subject"], m["From"], m["To"] = subject, USER, TO
m.attach(MIMEText(html, "html", "utf-8"))
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
    s.login(USER, PWD); s.sendmail(USER, [TO], m.as_string())
print("Mail envoyé :", subject)
