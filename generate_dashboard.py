import pandas as pd
import json
import calendar
from datetime import datetime
from urllib.parse import quote
 
# ─── CAMBIA SOLO ESTO ─────────────────────────────────────────────────────
SHEET_ID = "1ox6Abqq3I6ElRwYc9a3lxes5n3AtspQLRskzBY90pxI"
SIGNALS  = ["Trend", "Momentum", "Reversal", "Cont.3M", "Cont.5M"]
# ──────────────────────────────────────────────────────────────────────────
 
def csv_url(name):
    return (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
            f"/gviz/tq?tqx=out:csv&sheet={quote(name)}")
 
EMPTY = pd.DataFrame(columns=["fecha","hora","tipoSenal","direccion","razon","pctTV","tradeId","win"])
 
def load_sheet(name):
    try:
        raw = pd.read_csv(csv_url(name), header=0)
        if raw.empty or len(raw.columns) == 0:
            return EMPTY.copy()
        cols = ["fecha","hora","tipoSenal","direccion","razon","pctTV","tradeId"]
        raw  = raw.iloc[:, :len(cols)]
        raw.columns = cols[:len(raw.columns)]
        for c in cols:
            if c not in raw.columns:
                raw[c] = None
        raw["fecha"] = pd.to_datetime(raw["fecha"], dayfirst=True, errors="coerce")
        raw["pctTV"] = pd.to_numeric(raw["pctTV"], errors="coerce").fillna(0)
        raw["win"]   = raw["razon"].astype(str).str.contains("Take Profit", na=False)
        return raw.dropna(subset=["fecha"])
    except Exception as ex:
        print(f"Cannot load '{name}': {ex}")
        return EMPTY.copy()
 
now    = datetime.utcnow()
dfs    = {n: load_sheet(n) for n in SIGNALS}
all_df = pd.concat(list(dfs.values()), ignore_index=True) \
         if any(not d.empty for d in dfs.values()) else EMPTY.copy()
 
def global_metrics(df):
    if df.empty or "win" not in df.columns:
        return dict(total=0, wins=0, losses=0, winrate=0, profitFactor=0, firstDate="No data yet", cumTV=0)
    total  = len(df)
    wins   = df[df["win"] == True]
    losses = df[df["win"] == False]
    grossP = wins["pctTV"].sum()        if len(wins)   > 0 else 0
    grossL = abs(losses["pctTV"].sum()) if len(losses) > 0 else 0
    cumTV  = round(float(df["pctTV"].sum()), 2)
    first  = df.sort_values("fecha")["fecha"].iloc[0].strftime("%d/%m/%Y") if total > 0 else "No data yet"
    return dict(
        total=total, wins=len(wins), losses=len(losses),
        winrate=round(len(wins)/total*100, 1) if total > 0 else 0,
        profitFactor=round(grossP/grossL, 2) if grossL > 0 else 0,
        firstDate=first, cumTV=cumTV
    )
 
def month_metrics(df):
    if df.empty:
        return dict(total=0, wins=0, losses=0, cumTV=0)
    cur = df[(df["fecha"].dt.month == now.month) & (df["fecha"].dt.year == now.year)]
    if cur.empty:
        return dict(total=0, wins=0, losses=0, cumTV=0)
    return dict(
        total=len(cur),
        wins=len(cur[cur["win"] == True]),
        losses=len(cur[cur["win"] == False]),
        cumTV=round(float(cur["pctTV"].sum()), 2)
    )
 
def per_signal_metrics(dfs):
    result = []
    for name, df in dfs.items():
        if df.empty:
            result.append(dict(name=name, total=0, wins=0, losses=0, winrate=0, cumTV=0))
            continue
        total  = len(df)
        wins   = df[df["win"] == True]
        losses = df[df["win"] == False]
        result.append(dict(
            name=name,
            total=total,
            wins=len(wins),
            losses=len(losses),
            winrate=round(len(wins)/total*100, 1) if total > 0 else 0,
            cumTV=round(float(df["pctTV"].sum()), 2)
        ))
    return result
 
def weekly_pnl(df):
    if df.empty:
        return []
    cur = df[(df["fecha"].dt.month == now.month) & (df["fecha"].dt.year == now.year)]
    dim = calendar.monthrange(now.year, now.month)[1]
    mn  = now.strftime("%b")
    result = []
    for i, (ws, we) in enumerate([(1,7),(8,14),(15,21),(22,28),(29,dim)]):
        if ws > dim:
            break
        we = min(we, dim)
        wt = cur[(cur["fecha"].dt.day >= ws) & (cur["fecha"].dt.day <= we)]
        result.append({
            "label":  f"Week {i+1}  ·  {mn} {ws}–{we}",
            "pnl":    round(float(wt["pctTV"].sum()), 2) if len(wt) > 0 else 0,
            "trades": len(wt),
            "wins":   len(wt[wt["win"] == True]) if len(wt) > 0 else 0
        })
    return result
 
def monthly_pnl(df):
    if df.empty:
        return []
    s = df.copy().dropna(subset=["fecha"])
    if s.empty:
        return []
    s["month"] = s["fecha"].dt.to_period("M")
    result = []
    for period, g in s.groupby("month"):
        result.append({
            "label":  period.strftime("%b %Y"),
            "pnl":    round(float(g["pctTV"].sum()), 2),
            "trades": len(g),
            "wins":   len(g[g["win"] == True])
        })
    return result
 
def annual_equity(df):
    mp  = monthly_pnl(df)
    cum = 0
    pts = []
    for m in mp:
        cum = round(cum + m["pnl"], 2)
        pts.append({"x": m["label"], "y": cum})
    return pts
 
gm  = global_metrics(all_df)
mm  = month_metrics(all_df)
wk  = weekly_pnl(all_df)
mp  = monthly_pnl(all_df)
eq  = annual_equity(all_df)
sig = per_signal_metrics(dfs)
 
data = {
    "updated":       now.strftime("%d/%m/%Y %H:%M UTC"),
    "globalMetrics": gm,
    "monthMetrics":  mm,
    "weekly":        wk,
    "monthly":       mp,
    "equity":        eq,
    "signals":       sig
}
J = json.dumps(data, ensure_ascii=False)
 
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Oracle Algo — Gold Oracle Scalper V1 · Live Backtest</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{
  --bg:#020409;--surface:#080c17;--surface2:#0d1220;--surface3:#111827;
  --border:rgba(255,255,255,0.07);--border-bright:rgba(99,179,237,0.18);
  --blue:#2d7dd2;--blue-mid:#1a5fb4;--blue-light:#63b3ed;
  --cyan:#22d3ee;--purple:#818cf8;--green:#34d399;--red:#f87171;--yellow:#fbbf24;
  --text:#eef4ff;--text-muted:#7a90b5;--text-dim:#3d4e6a;
  --font-d:'Outfit',sans-serif;--font-b:'DM Sans',sans-serif;--font-m:'JetBrains Mono',monospace;
  --r:12px;--rl:18px;
}}
html{{scroll-behavior:smooth;}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-b);font-size:16px;line-height:1.7;overflow-x:hidden;min-height:100vh;}}
 
/* AURORA */
.aurora{{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;}}
.aurora::before{{content:'';position:absolute;border-radius:50%;filter:blur(120px);opacity:0.35;width:900px;height:650px;background:radial-gradient(ellipse,rgba(18,72,196,0.9) 0%,transparent 70%);top:-220px;left:-80px;animation:adrift 26s ease-in-out infinite;}}
.aurora::after{{content:'';position:absolute;border-radius:50%;filter:blur(120px);opacity:0.3;width:750px;height:520px;background:radial-gradient(ellipse,rgba(90,30,190,0.65) 0%,transparent 70%);top:-80px;right:-160px;animation:adrift 20s ease-in-out infinite;animation-delay:-7s;}}
.ac{{content:'';position:absolute;border-radius:50%;filter:blur(100px);opacity:0.25;width:600px;height:400px;background:radial-gradient(ellipse,rgba(4,148,188,0.5) 0%,transparent 70%);top:40vh;left:15%;animation:adrift 30s ease-in-out infinite;animation-delay:-14s;}}
@keyframes adrift{{0%,100%{{transform:translate(0,0) scale(1)}}25%{{transform:translate(60px,-50px) scale(1.06)}}50%{{transform:translate(-50px,70px) scale(0.95)}}75%{{transform:translate(30px,30px) scale(1.03)}}}}
.aurora-veil{{position:fixed;inset:0;z-index:1;background:linear-gradient(to bottom,rgba(2,4,9,0.25) 0%,rgba(2,4,9,0.6) 55%,rgba(2,4,9,0.97) 100%);pointer-events:none;}}
 
/* LAYOUT */
.wrap{{position:relative;z-index:2;}}
.container{{max-width:1160px;margin:0 auto;padding:0 24px;}}
 
/* HEADER */
header{{position:sticky;top:0;z-index:150;height:64px;padding:0 32px;
  background:rgba(2,4,9,0.0);backdrop-filter:blur(26px) saturate(1.5);
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid transparent;transition:background 0.3s,border-color 0.3s;}}
header.scrolled{{background:rgba(2,4,9,0.7);border-color:var(--border);}}
.brand{{display:flex;align-items:center;gap:10px;text-decoration:none;}}
.brand-text{{font-family:var(--font-d);font-weight:800;font-size:18px;letter-spacing:2px;
  background:linear-gradient(90deg,#fff,var(--blue-light));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.live-pill{{display:flex;align-items:center;gap:7px;background:rgba(52,211,153,0.08);
  border:1px solid rgba(52,211,153,0.2);border-radius:20px;padding:5px 12px;}}
.live-dot{{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;flex-shrink:0;}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 rgba(52,211,153,0.5)}}50%{{box-shadow:0 0 0 5px rgba(52,211,153,0)}}}}
.live-text{{font-family:var(--font-m);font-size:11px;color:var(--text-muted);letter-spacing:0.05em;}}
.live-text span{{color:var(--text);}}
 
/* HERO */
.hero{{padding:40px 24px 48px;text-align:center;}}
.hero-eyebrow{{display:none;}}
.hero h1{{font-family:var(--font-d);font-size:clamp(36px,6vw,72px);font-weight:700;
  line-height:1.08;letter-spacing:-2px;color:#fff;margin-bottom:16px;}}
.hero h1 .g{{background:linear-gradient(120deg,var(--blue-light) 0%,var(--cyan) 50%,#a78bfa 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.hero-sub{{font-size:clamp(14px,1.6vw,16px);color:var(--text-muted);max-width:500px;
  margin:0 auto 32px;font-weight:300;line-height:1.75;}}
.hero-meta{{display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap;
  font-family:var(--font-m);font-size:11px;color:var(--text-dim);}}
.hero-meta span{{color:var(--text-muted);}}
.hero-meta .sep{{color:var(--text-dim);}}
 
/* DIVIDER */
.sdivider{{height:1px;background:linear-gradient(90deg,transparent,var(--border-bright),transparent);margin:0 auto;max-width:860px;}}
 
/* SECTION */
.section{{padding:56px 0;}}
.section-label{{font-family:var(--font-d);font-size:11px;font-weight:600;
  color:var(--blue-light);text-transform:uppercase;letter-spacing:0.15em;margin-bottom:8px;text-align:center;}}
.section-title{{font-family:var(--font-d);font-size:clamp(22px,3vw,30px);font-weight:700;
  color:var(--text);margin-bottom:4px;text-align:center;}}
.section-sub{{font-size:14px;color:var(--text-muted);font-weight:300;text-align:center;}}
 
/* KPI GRID */
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px;margin-top:32px;}}
.kpi-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:20px 18px;position:relative;overflow:hidden;
  transition:border-color 0.2s,transform 0.15s;}}
.kpi-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(99,179,237,0.25),transparent);}}
.kpi-card:hover{{border-color:var(--border-bright);transform:translateY(-2px);}}
.kpi-label{{font-family:var(--font-m);font-size:10px;color:var(--text-dim);
  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;}}
.kpi-value{{font-family:var(--font-d);font-size:2rem;font-weight:700;line-height:1;color:var(--text);}}
.kpi-value.blue{{background:linear-gradient(120deg,var(--blue-light),var(--cyan));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.kpi-value.green{{color:var(--green);}}
.kpi-value.red{{color:var(--red);}}
.kpi-value.purple{{color:var(--purple);}}
.kpi-note{{font-family:var(--font-m);font-size:10px;color:var(--text-dim);margin-top:8px;}}
 
/* TWO COL */
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:32px;}}
@media(max-width:680px){{.two-col{{grid-template-columns:1fr;}}}}
 
/* CARD */
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:24px;}}
.card-title{{font-family:var(--font-d);font-size:12px;font-weight:600;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:0.12em;margin-bottom:20px;
  padding-bottom:12px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;}}
.card-title .ct-icon{{font-size:14px;}}
 
/* PNL ROWS */
.pnl-row{{display:flex;justify-content:space-between;align-items:center;
  padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.03);}}
.pnl-row:last-child{{border-bottom:none;padding-bottom:0;}}
.pnl-label{{font-family:var(--font-m);font-size:11px;color:var(--text-muted);}}
.pnl-right{{display:flex;align-items:center;gap:10px;}}
.pnl-val{{font-family:var(--font-m);font-size:13px;font-weight:600;}}
.pnl-meta{{font-family:var(--font-m);font-size:10px;color:var(--text-dim);}}
.pnl-empty{{font-family:var(--font-m);font-size:12px;color:var(--text-dim);
  text-align:center;padding:24px 0;}}
 
/* EQUITY CHART */
.chart-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:24px;margin-top:16px;}}
.chart-header{{display:flex;align-items:flex-start;justify-content:space-between;
  margin-bottom:20px;flex-wrap:wrap;gap:12px;}}
.chart-canvas{{position:relative;height:260px;}}
 
/* SIGNAL BREAKDOWN */
.sig-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:32px;}}
.sig-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:20px;transition:border-color 0.2s,transform 0.15s;position:relative;overflow:hidden;}}
.sig-card::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--blue),var(--cyan));opacity:0;transition:opacity 0.2s;}}
.sig-card:hover{{border-color:var(--border-bright);transform:translateY(-2px);}}
.sig-card:hover::after{{opacity:1;}}
.sig-name{{font-family:var(--font-d);font-size:13px;font-weight:700;color:var(--text);margin-bottom:14px;
  display:flex;align-items:center;gap:8px;}}
.sig-dot{{width:7px;height:7px;border-radius:50%;background:linear-gradient(135deg,var(--blue-light),var(--cyan));flex-shrink:0;}}
.sig-stats{{display:grid;grid-template-columns:1fr 1fr;gap:8px;}}
.sig-stat-label{{font-family:var(--font-m);font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;}}
.sig-stat-val{{font-family:var(--font-m);font-size:14px;font-weight:600;color:var(--text);}}
.sig-stat-val.g{{color:var(--green);}}.sig-stat-val.b{{background:linear-gradient(90deg,var(--blue-light),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
 
/* WIN RATE BAR */
.wr-bar-wrap{{margin-top:14px;}}
.wr-bar-track{{height:3px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;}}
.wr-bar-fill{{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--blue),var(--cyan));transition:width 1s ease;}}
.wr-bar-label{{font-family:var(--font-m);font-size:10px;color:var(--text-muted);margin-top:5px;display:flex;justify-content:space-between;}}
 
/* FOOTER */
footer{{border-top:1px solid var(--border);padding:40px 24px;text-align:center;margin-top:80px;}}
.footer-brand{{font-family:var(--font-d);font-weight:800;font-size:20px;letter-spacing:2px;
  background:linear-gradient(90deg,#fff,var(--blue-light));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px;}}
.footer-text{{font-family:var(--font-m);font-size:11px;color:var(--text-dim);line-height:2;max-width:600px;margin:0 auto;}}
.footer-text a{{color:var(--text-muted);text-decoration:none;}}
.footer-text a:hover{{color:var(--blue-light);}}
 
/* RESPONSIVE */
@media(max-width:560px){{
  .kpi-grid{{grid-template-columns:1fr 1fr;}}
  header{{padding:0 16px;}}
  .hero{{padding:60px 16px 40px;}}
}}
</style>
</head>
<body>
 
<div class="aurora"><div class="ac"></div></div>
<div class="aurora-veil"></div>
 
<div class="wrap">
 
<!-- HEADER -->
<header id="mainHeader">
  <a class="brand" href="#">
    <svg width="32" height="32" viewBox="0 0 34 34" fill="none">
      <defs><linearGradient id="lg1" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#ffffff"/>
        <stop offset="35%" stop-color="#63b3ed"/>
        <stop offset="65%" stop-color="#22d3ee"/>
        <stop offset="100%" stop-color="#a78bfa"/>
      </linearGradient></defs>
      <circle cx="17" cy="17" r="15.2" stroke="url(#lg1)" stroke-width="2" fill="none"/>
      <path d="M17 7.5L25 26.5H9L17 7.5Z" stroke="url(#lg1)" stroke-width="1.8" fill="none" stroke-linejoin="round"/>
      <line x1="12" y1="21" x2="22" y2="21" stroke="url(#lg1)" stroke-width="1.8" stroke-linecap="round"/>
    </svg>
    <span class="brand-text">Oracle Algo</span>
  </a>
  <div class="live-pill">
    <span class="live-dot"></span>
    <span class="live-text">Live · <span id="ts"></span></span>
  </div>
</header>
 
<!-- HERO -->
<section class="hero">
  <div class="hero-eyebrow">⚡ Live Backtest Results</div>
  <h1>Gold Oracle Scalper <span class="g">V1</span></h1>
  <p class="hero-sub">Real-time signal tracking on XAUUSD. Every trade logged, every result verified. No cherry-picking.</p>
  <div class="hero-meta">
    <span>Tracking since <span id="since">—</span></span>
    <span class="sep">·</span>
    <span>XAUUSD · All signals combined</span>
    <span class="sep">·</span>
    <span>Starting May 2026</span>
  </div>
</section>
 
<div class="sdivider"></div>
 
<main class="container">
 
  <!-- KPIs -->
  <section class="section">
    <div class="kpi-grid" id="kpis"></div>
  </section>
 
  <div class="sdivider"></div>
 
  <!-- WEEKLY + MONTHLY -->
  <section class="section">
    <div class="section-label">P&amp;L Breakdown</div>
    <div class="section-title">Weekly &amp; Monthly Results</div>
    <div class="section-sub">Current month and historical performance</div>
    <div class="two-col">
      <div class="card">
        <div class="card-title"><span class="ct-icon">⚡</span>Weekly P&amp;L — Current Month</div>
        <div id="weekly-content"></div>
      </div>
      <div class="card">
        <div class="card-title"><span class="ct-icon">📅</span>Monthly P&amp;L History</div>
        <div id="monthly-content"></div>
      </div>
    </div>
  </section>
 
  <div class="sdivider"></div>
 
  <!-- EQUITY CURVE -->
  <section class="section">
    <div class="section-label">Equity Curve</div>
    <div class="section-title">Annual Equity Curve</div>
    <div class="section-sub">Cumulative performance month by month</div>
    <div class="chart-wrap" style="margin-top:32px;">
      <div class="chart-canvas"><canvas id="eqChart"></canvas></div>
    </div>
  </section>
 
</main>
 
<!-- FOOTER -->
<footer>
  <div class="footer-brand">Oracle Algo</div>
  <div class="footer-text">
    © 2025–2026 Oracle Algo · <a href="https://oraclealgo.com">oraclealgo.com</a> · All rights reserved.<br>
    Gold Oracle Scalper V1 · XAUUSD · Real-time tracking from May 2026<br>
    Past results do not guarantee future performance. For informational purposes only.
  </div>
</footer>
 
</div><!-- /wrap -->
 
<script>
const D = {J};
 
document.getElementById("ts").textContent    = D.updated;
document.getElementById("since").textContent = D.globalMetrics.firstDate;
 
const gm = D.globalMetrics;
const mm = D.monthMetrics;
 
function pct(v) {{ return (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%" }}
function clr(v) {{ return v > 0 ? "var(--green)" : v < 0 ? "var(--red)" : "var(--text-muted)" }}
 
// ── KPIs ──────────────────────────────────────────────────────────────────
const kpiData = [
  {{ label:"Win Rate",         val: gm.winrate + "%",              cls:"blue",   note:"All time · All signals" }},
  {{ label:"Profit Factor",    val: gm.profitFactor || "—",        cls:"purple", note:"All time · All signals" }},
  {{ label:"Total TV%",        val: pct(gm.cumTV || 0),            cls: (gm.cumTV||0) >= 0 ? "green" : "red", note:"Cumulative TV%" }},
  {{ label:"Total Trades",     val: gm.total,                      cls:"",       note:"Since tracking started" }},
  {{ label:"Month Trades",     val: mm.total,                      cls:"",       note:"Current month" }},
  {{ label:"Month TV%",        val: pct(mm.cumTV || 0),            cls: (mm.cumTV||0) >= 0 ? "green" : "red", note:"Current month TV%" }},
];
const kRow = document.getElementById("kpis");
kpiData.forEach(k => {{
  kRow.innerHTML += `
  <div class="kpi-card">
    <div class="kpi-label">${{k.label}}</div>
    <div class="kpi-value ${{k.cls}}">${{k.val}}</div>
    <div class="kpi-note">${{k.note}}</div>
  </div>`;
}});
 
// ── Weekly P&L ──────────────────────────────────────────────────────────────
const wEl = document.getElementById("weekly-content");
const activeWeeks = D.weekly ? D.weekly.filter(w => w.trades > 0) : [];
if (activeWeeks.length === 0) {{
  wEl.innerHTML = `<div class="pnl-empty">No trades this month yet</div>`;
}} else {{
  D.weekly.forEach(w => {{
    if (w.trades === 0) return;
    wEl.innerHTML += `
    <div class="pnl-row">
      <span class="pnl-label">${{w.label}}</span>
      <div class="pnl-right">
        <span class="pnl-val" style="color:${{clr(w.pnl)}}">${{pct(w.pnl)}}</span>
        <span class="pnl-meta">${{w.trades}}T · ${{w.wins}}W</span>
      </div>
    </div>`;
  }});
}}
 
// ── Monthly P&L ──────────────────────────────────────────────────────────────
const mEl = document.getElementById("monthly-content");
if (!D.monthly || D.monthly.length === 0) {{
  mEl.innerHTML = `<div class="pnl-empty">No history yet</div>`;
}} else {{
  [...D.monthly].reverse().forEach(m => {{
    mEl.innerHTML += `
    <div class="pnl-row">
      <span class="pnl-label">${{m.label}}</span>
      <div class="pnl-right">
        <span class="pnl-val" style="color:${{clr(m.pnl)}}">${{pct(m.pnl)}}</span>
        <span class="pnl-meta">${{m.trades}}T</span>
      </div>
    </div>`;
  }});
}}
 
// ── Equity Chart ──────────────────────────────────────────────────────────────
const eq  = D.equity || [];
const ctx = document.getElementById("eqChart").getContext("2d");
const g1  = ctx.createLinearGradient(0, 0, 0, 260);
g1.addColorStop(0, "rgba(99,179,237,0.2)");
g1.addColorStop(1, "rgba(99,179,237,0.0)");
new Chart(ctx, {{
  type: "line",
  data: {{
    labels: eq.map(p => p.x),
    datasets: [{{
      data: eq.map(p => p.y),
      borderColor: "#63b3ed",
      borderWidth: 2,
      backgroundColor: g1,
      fill: true,
      pointRadius: eq.length < 15 ? 5 : 3,
      pointBackgroundColor: "#63b3ed",
      pointBorderColor: "#020409",
      pointBorderWidth: 2,
      tension: .35
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        backgroundColor: "rgba(8,12,23,0.95)",
        borderColor: "rgba(99,179,237,0.2)",
        borderWidth: 1,
        titleFont: {{ family: "JetBrains Mono", size: 10 }},
        bodyFont:  {{ family: "JetBrains Mono", size: 12 }},
        callbacks: {{
          label: c => " " + (c.parsed.y >= 0 ? "+" : "") + c.parsed.y.toFixed(2) + "%"
        }}
      }}
    }},
    scales: {{
      x: {{
        ticks: {{ color:"#3d4e6a", font:{{ family:"JetBrains Mono", size:10 }} }},
        grid:  {{ color:"rgba(255,255,255,0.03)" }}
      }},
      y: {{
        ticks: {{
          color:"#3d4e6a",
          font:{{ family:"JetBrains Mono", size:10 }},
          callback: v => v + "%"
        }},
        grid: {{ color:"rgba(255,255,255,0.03)" }}
      }}
    }}
  }}
}});
 
// ── Scroll header ──────────────────────────────────────────────────────────────
window.addEventListener("scroll", () =>
  document.getElementById("mainHeader").classList.toggle("scrolled", window.scrollY > 50)
);
</script>
</body>
</html>"""
 
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
 
print("Dashboard generated — Gold Oracle Scalper V1")
print(f"  Signals tracked : Trend, Momentum, Reversal, Cont.3M, Cont.5M")
print(f"  Win Rate        : {gm['winrate']}%")
print(f"  Profit Factor   : {gm['profitFactor']}")
print(f"  Total Trades    : {gm['total']}")
print(f"  Since           : {gm['firstDate']}")
 
