import pandas as pd
import json
import calendar
from datetime import datetime
from urllib.parse import quote
 
# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────
SHEET_ID = "1ox6Abqq3I6ElRwYc9a3lxes5n3AtspQLRskzBY90pxI"
SIGNALS  = ["Trend", "Momentum", "Reversal", "Cont.5M"]
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
 
def load_manual_pnl():
    try:
        raw = pd.read_csv(csv_url("TV DAILY P&L"), header=0)
        if raw.empty or len(raw.columns) == 0:
            return pd.DataFrame(columns=["fecha","pnlPct","notas"])
        raw = raw.iloc[:, :3]
        raw.columns = ["fecha","pnlPct","notas"][:len(raw.columns)]
        if "fecha"  not in raw.columns: raw["fecha"]  = None
        if "pnlPct" not in raw.columns: raw["pnlPct"] = 0
        raw["fecha"]  = pd.to_datetime(raw["fecha"], dayfirst=True, errors="coerce")
        raw["pnlPct"] = pd.to_numeric(raw["pnlPct"], errors="coerce").fillna(0)
        return raw.dropna(subset=["fecha"])
    except Exception as ex:
        print(f"Cannot load manual P&L: {ex}")
        return pd.DataFrame(columns=["fecha","pnlPct","notas"])
 
now       = datetime.utcnow()
dfs       = {n: load_sheet(n) for n in SIGNALS}
all_df    = pd.concat(list(dfs.values()), ignore_index=True) \
            if any(not d.empty for d in dfs.values()) else EMPTY.copy()
manual_df = load_manual_pnl()
 
def global_metrics(df):
    if df.empty or "win" not in df.columns:
        return dict(total=0, wins=0, losses=0, winrate=0, profitFactor="—", firstDate="No data yet")
    total  = len(df)
    wins   = df[df["win"] == True]
    losses = df[df["win"] == False]
    grossP = wins["pctTV"].sum()        if len(wins)   > 0 else 0
    grossL = abs(losses["pctTV"].sum()) if len(losses) > 0 else 0
    first  = df.sort_values("fecha")["fecha"].iloc[0].strftime("%d/%m/%Y") if total > 0 else "No data yet"
    pf     = "inf" if (grossL == 0 and total > 0) else (round(grossP/grossL, 2) if grossL > 0 else "—")
    return dict(
        total=total, wins=len(wins), losses=len(losses),
        winrate=round(len(wins)/total*100, 1) if total > 0 else 0,
        profitFactor=pf, firstDate=first
    )
 
def month_metrics(df):
    if df.empty:
        return dict(total=0, wins=0, losses=0, monthPct=0)
    cur = df[(df["fecha"].dt.month == now.month) & (df["fecha"].dt.year == now.year)]
    if cur.empty:
        return dict(total=0, wins=0, losses=0, monthPct=0)
    return dict(
        total=len(cur), wins=len(cur[cur["win"]==True]),
        losses=len(cur[cur["win"]==False]),
        monthPct=round(float(cur["pctTV"].sum()), 2)
    )
 
def today_manual_pnl(df):
    if df.empty: return None
    today_data = df[df["fecha"].dt.date == now.date()]
    if not today_data.empty:
        return round(float(today_data["pnlPct"].sum()), 2)
    if not df.empty:
        return round(float(df.sort_values("fecha").iloc[-1]["pnlPct"]), 2)
    return None
 
def weekly_tracked(df):
    if df.empty: return []
    cur = df[(df["fecha"].dt.month==now.month)&(df["fecha"].dt.year==now.year)]
    dim = calendar.monthrange(now.year, now.month)[1]
    mn  = now.strftime("%b")
    result = []
    for i,(ws,we) in enumerate([(1,7),(8,14),(15,21),(22,28),(29,dim)]):
        if ws > dim: break
        we = min(we, dim)
        wt = cur[(cur["fecha"].dt.day>=ws)&(cur["fecha"].dt.day<=we)]
        result.append({
            "label":   f"Week {i+1}  |  {mn} {ws}-{we}",
            "tracked": round(float(wt["pctTV"].sum()),2) if len(wt)>0 else 0,
            "trades":  len(wt),
            "wins":    len(wt[wt["win"]==True]) if len(wt)>0 else 0
        })
    return result
 
def weekly_manual(df):
    if df.empty: return {}
    cur = df[(df["fecha"].dt.month==now.month)&(df["fecha"].dt.year==now.year)]
    dim = calendar.monthrange(now.year, now.month)[1]
    result = {}
    for i,(ws,we) in enumerate([(1,7),(8,14),(15,21),(22,28),(29,dim)]):
        if ws > dim: break
        we = min(we, dim)
        wt = cur[(cur["fecha"].dt.day>=ws)&(cur["fecha"].dt.day<=we)]
        result[str(i)] = round(float(wt["pnlPct"].sum()),2) if len(wt)>0 else None
    return result
 
def monthly_data(tracked_df, manual_df):
    result = {}
    if not tracked_df.empty:
        s = tracked_df.copy().dropna(subset=["fecha"])
        s["month"] = s["fecha"].dt.to_period("M")
        for period, g in s.groupby("month"):
            k = period.strftime("%b %Y")
            if k not in result: result[k] = {"tracked":0,"manual":None,"trades":0}
            result[k]["tracked"] = round(float(g["pctTV"].sum()),2)
            result[k]["trades"]  = len(g)
    if not manual_df.empty:
        s = manual_df.copy().dropna(subset=["fecha"])
        s["month"] = s["fecha"].dt.to_period("M")
        for period, g in s.groupby("month"):
            k = period.strftime("%b %Y")
            if k not in result: result[k] = {"tracked":0,"manual":None,"trades":0}
            result[k]["manual"] = round(float(g["pnlPct"].sum()),2)
    sorted_keys = sorted(result.keys(), key=lambda x: datetime.strptime("01 "+x, "%d %b %Y"))
    return [{"label":k, **result[k]} for k in sorted_keys]
 
def annual_equity(monthly_list):
    cum_t, cum_m = 0, 0
    pts = []
    has_manual = False
    for m in monthly_list:
        cum_t = round(cum_t + m["tracked"], 2)
        if m["manual"] is not None:
            cum_m = round(cum_m + m["manual"], 2)
            has_manual = True
        pts.append({"x":m["label"], "tracked":cum_t, "manual":cum_m if has_manual else None})
    return pts
 
gm      = global_metrics(all_df)
mm      = month_metrics(all_df)
wt      = weekly_tracked(all_df)
wm      = weekly_manual(manual_df)
mp      = monthly_data(all_df, manual_df)
eq      = annual_equity(mp)
dailyPL = today_manual_pnl(manual_df)
 
data = {
    "updated":       now.strftime("%d/%m/%Y %H:%M UTC"),
    "globalMetrics": gm,
    "monthMetrics":  mm,
    "weeklyTracked": wt,
    "weeklyManual":  wm,
    "monthly":       mp,
    "equity":        eq,
    "dailyPL":       dailyPL
}
J = json.dumps(data, ensure_ascii=False)
 
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Oracle Algo — Gold Oracle Scalper V1 Backtest</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#020409;--sur:#080c17;--sur2:#0d1220;
  --brd:rgba(255,255,255,0.07);--brdb:rgba(99,179,237,0.22);
  --blue:#2d7dd2;--bm:#1a5fb4;--bl:#63b3ed;
  --cyan:#22d3ee;--pur:#818cf8;--grn:#34d399;--yel:#fbbf24;--red:#f87171;
  --txt:#eef4ff;--tm:#7a90b5;--td:#3d4e6a;
  --fd:'Outfit',sans-serif;--fb:'DM Sans',sans-serif
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:var(--fb);min-height:100vh;overflow-x:hidden}
.aurora{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
.aurora::before,.aurora::after{content:'';position:absolute;border-radius:50%;filter:blur(90px);opacity:.55;animation:adrift 24s ease-in-out infinite}
.aurora::before{width:900px;height:600px;background:radial-gradient(ellipse,rgba(18,72,196,.85) 0%,transparent 70%);top:-180px;left:-60px;animation-duration:26s}
.aurora::after{width:700px;height:480px;background:radial-gradient(ellipse,rgba(34,211,238,.25) 0%,transparent 70%);top:-60px;right:-120px;animation-duration:20s;animation-delay:-7s}
.veil{position:fixed;inset:0;z-index:1;background:linear-gradient(to bottom,rgba(2,4,9,.2) 0%,rgba(2,4,9,.72) 60%,rgba(2,4,9,.98) 100%);pointer-events:none}
@keyframes adrift{0%,100%{transform:translate(0,0) scale(1)}25%{transform:translate(60px,-45px) scale(1.05)}50%{transform:translate(-45px,65px) scale(.95)}75%{transform:translate(30px,30px) scale(1.03)}}
.page{position:relative;z-index:2}
header{padding:.9rem 2.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.8rem;border-bottom:1px solid var(--brd);background:rgba(2,4,9,0);backdrop-filter:blur(26px) saturate(1.5);position:sticky;top:0;z-index:100}
.logo{display:flex;align-items:center;gap:.9rem}
.lsvg{width:36px;height:36px;flex-shrink:0}
.ltxt h1{font-family:var(--fd);font-size:1.15rem;font-weight:800;letter-spacing:2px;line-height:1}
.ltxt h1 .o{color:#fff}.ltxt h1 .a{color:var(--cyan)}
.ltxt p{font-family:var(--fb);font-size:.6rem;color:var(--tm);letter-spacing:.06em;margin-top:.2rem}
.badge{font-family:var(--fd);font-size:.6rem;color:var(--tm);display:flex;align-items:center;gap:.4rem}
.dot{width:6px;height:6px;border-radius:50%;background:var(--grn);flex-shrink:0;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(52,211,153,.5)}50%{box-shadow:0 0 0 5px rgba(52,211,153,0)}}
main{max-width:1180px;margin:0 auto;padding:2.5rem 2rem}
.hero{text-align:center;margin-bottom:2.5rem;padding-bottom:1.8rem;border-bottom:1px solid var(--brd);position:relative}
.hero::after{content:'';position:absolute;bottom:-1px;left:50%;transform:translateX(-50%);width:80px;height:1px;background:linear-gradient(90deg,transparent,var(--cyan),transparent)}
.ht{font-family:var(--fd);font-size:clamp(1.3rem,3vw,2rem);font-weight:800;letter-spacing:-1px;line-height:1.1;margin-bottom:.5rem}
.ht .g{background:linear-gradient(120deg,#fff 0%,var(--bl) 38%,var(--cyan) 68%,#a78bfa 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hs{font-family:var(--fb);font-size:.68rem;color:var(--tm)}
.hs span{color:var(--txt)}
.kg{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:1rem;margin-bottom:2rem}
.kpi{background:var(--sur);border:1px solid var(--brd);border-radius:12px;padding:1.2rem 1.1rem;transition:border-color .2s,transform .15s;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--brdb),transparent)}
.kpi:hover{border-color:var(--brdb);transform:translateY(-1px)}
.kl{font-family:var(--fd);font-size:.58rem;color:var(--tm);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem}
.kv{font-family:var(--fd);font-size:1.5rem;font-weight:700;color:var(--txt);line-height:1}
.kv.cy{color:var(--cyan)}.kv.gn{color:var(--grn)}.kv.rd{color:var(--red)}.kv.bl{color:var(--bl)}
.kn{font-family:var(--fb);font-size:.55rem;color:var(--td);margin-top:.3rem;line-height:1.4}
.tc{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:2rem}
@media(max-width:700px){.tc{grid-template-columns:1fr}}
.card{background:var(--sur);border:1px solid var(--brd);border-radius:14px;padding:1.5rem;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--brdb),transparent)}
.ct{font-family:var(--fd);font-size:.65rem;font-weight:600;color:var(--tm);text-transform:uppercase;letter-spacing:.12em;margin-bottom:1.2rem;border-bottom:1px solid var(--brd);padding-bottom:.7rem}
.pr{display:flex;justify-content:space-between;align-items:flex-start;padding:.5rem 0;border-bottom:1px solid rgba(255,255,255,.04);font-family:var(--fd);font-size:.72rem}
.pr:last-child{border-bottom:none}
.pl{color:var(--tm);flex-shrink:0;padding-right:.5rem}
.pv{display:flex;flex-direction:column;align-items:flex-end;gap:.15rem}
.pt{font-weight:600;font-size:.78rem}
.pm{font-size:.65rem;opacity:.8}
.pb{font-size:.55rem;background:rgba(99,179,237,.1);border:1px solid rgba(99,179,237,.2);color:var(--bl);border-radius:4px;padding:1px 5px;margin-left:.3rem}
.pe{font-family:var(--fb);font-size:.7rem;color:var(--td);text-align:center;padding:1.5rem 0}
.ew{background:var(--sur);border:1px solid var(--brd);border-radius:14px;padding:1.5rem;margin-bottom:2rem;position:relative;overflow:hidden}
.ew::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--brdb),transparent)}
.eh{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.2rem}
.etit{font-family:var(--fd);font-size:.65rem;font-weight:600;color:var(--tm);text-transform:uppercase;letter-spacing:.12em}
.eleg{display:flex;gap:1rem}
.eli{display:flex;align-items:center;gap:.35rem;font-family:var(--fb);font-size:.62rem;color:var(--tm)}
.eld{width:8px;height:8px;border-radius:50%}
.ec{position:relative;height:240px}
footer{text-align:center;padding:2rem 1rem;border-top:1px solid var(--brd)}
.fl{font-family:var(--fd);font-size:.75rem;font-weight:800;letter-spacing:2px;color:var(--td);text-transform:uppercase;margin-bottom:.5rem}
.fl .fo{color:var(--tm)}.fl .fa{color:var(--cyan)}
.fc{font-family:var(--fb);font-size:.6rem;color:var(--td);line-height:1.8}
@media(max-width:560px){.kg{grid-template-columns:1fr 1fr}header{padding:.8rem 1rem}}
</style>
</head>
<body>
<div class="aurora"></div>
<div class="veil"></div>
<div class="page">
<header>
  <div class="logo">
    <svg class="lsvg" viewBox="0 0 36 36" fill="none">
      <circle cx="18" cy="18" r="17" stroke="url(#sg)" stroke-width="1" opacity=".6"/>
      <circle cx="18" cy="18" r="11" stroke="url(#sg)" stroke-width="1" opacity=".8"/>
      <path d="M18 4L21 10.5L18 9L15 10.5Z" fill="url(#sg)"/>
      <path d="M18 32L15 25.5L18 27L21 25.5Z" fill="url(#sg)" opacity=".6"/>
      <circle cx="18" cy="18" r="2.5" fill="url(#sg)"/>
      <circle cx="18" cy="18" r="5" stroke="url(#sg)" stroke-width=".5" opacity=".5"/>
      <line x1="18" y1="7" x2="18" y2="29" stroke="url(#sg)" stroke-width=".4" opacity=".3" stroke-dasharray="2 3"/>
      <line x1="7" y1="18" x2="29" y2="18" stroke="url(#sg)" stroke-width=".4" opacity=".3" stroke-dasharray="2 3"/>
      <defs>
        <linearGradient id="sg" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#22d3ee"/>
          <stop offset="100%" stop-color="#2d7dd2"/>
        </linearGradient>
      </defs>
    </svg>
    <div class="ltxt">
      <h1><span class="o">Oracle</span><span class="a">Algo</span></h1>
      <p>XAUUSD &middot; Gold Oracle Scalper V1 &middot; Live Backtest</p>
    </div>
  </div>
  <div class="badge">
    <span class="dot"></span>
    Live &middot; Updated: <span id="ts" style="color:var(--txt);margin-left:.3rem"></span>
  </div>
</header>
<main>
  <div class="hero">
    <div class="ht"><span class="g">Gold Oracle Scalper V1</span> Backtest</div>
    <div class="hs">Tracking since <span id="since"></span> &nbsp;&middot;&nbsp; All signals combined &nbsp;&middot;&nbsp; Starting May 2026</div>
  </div>
  <div class="kg" id="kpis"></div>
  <div class="tc">
    <div class="card"><div class="ct">&#9889; Weekly P&amp;L &mdash; Current Month</div><div id="wc"></div></div>
    <div class="card"><div class="ct">&#128197; Monthly P&amp;L History</div><div id="mc"></div></div>
  </div>
  <div class="ew">
    <div class="eh">
      <div class="etit">&#128200; Annual Equity Curve &mdash; Cumulative Performance</div>
      <div class="eleg">
        <div class="eli"><div class="eld" style="background:#63b3ed"></div>Tracked TP/SL%</div>
        <div class="eli"><div class="eld" style="background:#22d3ee"></div>Manual TV%</div>
      </div>
    </div>
    <div class="ec"><canvas id="eq"></canvas></div>
  </div>
</main>
<footer>
  <div class="fl"><span class="fo">Oracle</span><span class="fa">Algo</span></div>
  <div class="fc">
    &copy; 2025&ndash;2026 Oracle Algo &middot; oraclealgo.com &middot; All rights reserved.<br>
    Gold Oracle Scalper V1 &middot; XAUUSD &middot; Real-time tracking from May 2026<br>
    Past results do not guarantee future performance. For informational purposes only.
  </div>
</footer>
</div>
<script>
const D=JSON_DATA;
const mm=D.monthMetrics,gm=D.globalMetrics;
document.getElementById("ts").textContent=D.updated;
document.getElementById("since").textContent=gm.firstDate;
function pct(v){return(v>=0?"+":"")+Number(v).toFixed(2)+"%"}
function cc(v){return Number(v)>0?"gn":Number(v)<0?"rd":""}
const dv=D.dailyPL!==null&&D.dailyPL!==undefined?D.dailyPL:null;
const dd=dv!==null?pct(dv):"—";
const dc=dv!==null?cc(dv):"";
const pf=gm.profitFactor==="inf"?"∞":(gm.profitFactor||"—");
const kd=[
  {l:"Win Rate",v:gm.winrate+"%",c:"cy",n:"All signals · All time"},
  {l:"Profit Factor",v:pf,c:"cy",n:"All signals · All time"},
  {l:"Daily P&L",v:dd,c:dc,n:"Manual · Latest TV strategy P&L"},
  {l:"Monthly Trades",v:mm.total,c:"",n:"Current month total"},
  {l:"Monthly Wins",v:mm.wins,c:"gn",n:"Current month"},
  {l:"Monthly Losses",v:mm.losses,c:"rd",n:"Current month"},
  {l:"Month TP/SL %",v:pct(mm.monthPct),c:cc(mm.monthPct),n:"Monthly cumul. TP/SL %"},
];
const kr=document.getElementById("kpis");
kd.forEach(k=>{kr.innerHTML+=`<div class="kpi"><div class="kl">${k.l}</div><div class="kv ${k.c}">${k.v}</div><div class="kn">${k.n}</div></div>`;});
const wEl=document.getElementById("wc");
const wt=D.weeklyTracked||[],wm=D.weeklyManual||{};
const hasW=wt.some(w=>w.trades>0)||Object.values(wm).some(v=>v!==null&&v!==0);
if(!hasW){wEl.innerHTML='<div class="pe">No trades this month yet</div>';}
else{wt.forEach((w,i)=>{
  const mv=wm[String(i)]!==undefined?wm[String(i)]:null;
  if(w.trades===0&&(mv===null||mv===0))return;
  const tc=w.tracked>=0?"#34d399":"#f87171";
  const mc=mv!==null?(mv>=0?"#22d3ee":"#f87171"):null;
  wEl.innerHTML+=`<div class="pr"><span class="pl">${w.label}</span><div class="pv">
    ${w.trades>0?`<span class="pt" style="color:${tc}">${pct(w.tracked)}<span class="pb">${w.trades}T·${w.wins}W</span></span>`:""}
    ${mv!==null?`<span class="pm" style="color:${mc}">TV: ${pct(mv)}</span>`:""}
  </div></div>`;
});}
const mEl=document.getElementById("mc");
if(!D.monthly||D.monthly.length===0){mEl.innerHTML='<div class="pe">No history yet</div>';}
else{[...D.monthly].reverse().forEach(m=>{
  const tc=m.tracked>=0?"#34d399":"#f87171";
  const mc=m.manual!==null?(m.manual>=0?"#22d3ee":"#f87171"):null;
  mEl.innerHTML+=`<div class="pr"><span class="pl">${m.label}</span><div class="pv">
    ${m.trades>0?`<span class="pt" style="color:${tc}">${pct(m.tracked)}<span class="pb">${m.trades}T</span></span>`:""}
    ${m.manual!==null?`<span class="pm" style="color:${mc}">TV: ${pct(m.manual)}</span>`:""}
  </div></div>`;
});}
const eq=D.equity||[];
const ctx=document.getElementById("eq").getContext("2d");
const gT=ctx.createLinearGradient(0,0,0,240);gT.addColorStop(0,"rgba(99,179,237,.22)");gT.addColorStop(1,"rgba(99,179,237,0)");
const gM=ctx.createLinearGradient(0,0,0,240);gM.addColorStop(0,"rgba(34,211,238,.18)");gM.addColorStop(1,"rgba(34,211,238,0)");
const dsets=[{label:"Tracked TP/SL%",data:eq.map(p=>p.tracked),borderColor:"#63b3ed",borderWidth:2,backgroundColor:gT,fill:true,pointRadius:eq.length<15?5:2,pointBackgroundColor:"#63b3ed",tension:.35}];
if(eq.some(p=>p.manual!==null))dsets.push({label:"Manual TV%",data:eq.map(p=>p.manual),borderColor:"#22d3ee",borderWidth:2,backgroundColor:gM,fill:true,pointRadius:eq.length<15?5:2,pointBackgroundColor:"#22d3ee",tension:.35,borderDash:[4,3]});
new Chart(ctx,{type:"line",data:{labels:eq.map(p=>p.x),datasets:dsets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+(c.parsed.y>=0?"+":"")+c.parsed.y.toFixed(2)+"%"}}},scales:{x:{ticks:{color:"#3d4e6a",font:{family:"DM Sans",size:10}},grid:{color:"rgba(255,255,255,.04)"}},y:{ticks:{color:"#3d4e6a",font:{family:"DM Sans",size:10},callback:v=>v+"%"},grid:{color:"rgba(255,255,255,.04)"}}}}});
</script>
</body>
</html>"""
 
html_out = HTML_TEMPLATE.replace("JSON_DATA", J)
 
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)
 
print("Oracle Algo Dashboard generated.")
print(f"  Win Rate     : {gm['winrate']}%")
print(f"  Month TP/SL% : {mm['monthPct']}%")
print(f"  Daily P&L    : {dailyPL}")
print(f"  Total Trades : {gm['total']}")
