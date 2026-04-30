import pandas as pd
import json
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN — edita solo estas líneas
# ─────────────────────────────────────────────
SHEET_ID = "1ox6Abqq3I6ElRwYc9a3lxes5n3AtspQLRskzBY90pxI"   # ID de tu Google Sheet (ver README)
SHEETS   = ["Tendencia", "Momentum", "Reversion", "Breakout"]
# ─────────────────────────────────────────────

def csv_url(sheet_name):
    return (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    )

def load_sheet(name):
    try:
        df = pd.read_csv(csv_url(name))
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["fecha","tipoSenal","resultado","razon","tradeId","win","signal"])
        # Tomar solo las primeras columnas sin importar cuántas haya
        cols_needed = min(5, len(df.columns))
        df = df.iloc[:, :cols_needed]
        col_names = ["fecha","tipoSenal","resultado","razon","tradeId"]
        df.columns = col_names[:cols_needed]
        for col in col_names:
            if col not in df.columns:
                df[col] = None
        df["fecha"]     = pd.to_datetime(df["fecha"], errors="coerce")
        df["resultado"] = pd.to_numeric(df["resultado"], errors="coerce").fillna(0)
        df["win"]       = df["resultado"] > 0
        df["signal"]    = name
        return df
    except Exception as e:
        print(f"⚠️  No se pudo cargar la hoja '{name}': {e}")
        return pd.DataFrame(columns=["fecha","tipoSenal","resultado","razon","tradeId","win","signal"])
def metrics(df):
    total   = len(df)
    if total == 0:
        return dict(total=0, wins=0, losses=0, winrate=0,
                    profit=0, profit_factor=0, avg_win=0, avg_loss=0, best=0, worst=0)
    wins    = df[df["win"]]
    losses  = df[~df["win"]]
    gross_p = wins["resultado"].sum()
    gross_l = abs(losses["resultado"].sum())
    return dict(
        total        = total,
        wins         = len(wins),
        losses       = len(losses),
        winrate      = round(len(wins) / total * 100, 1),
        profit       = round(df["resultado"].sum(), 2),
        profit_factor= round(gross_p / gross_l, 2) if gross_l > 0 else float("inf"),
        avg_win      = round(wins["resultado"].mean(), 2)   if len(wins)   > 0 else 0,
        avg_loss     = round(losses["resultado"].mean(), 2) if len(losses) > 0 else 0,
        best         = round(df["resultado"].max(), 2),
        worst        = round(df["resultado"].min(), 2),
    )

def equity_curve(df):
    if df.empty:
        return []
    s = df.sort_values("fecha")
    s["equity"] = s["resultado"].cumsum().round(2)
    return [{"x": str(r["fecha"].date()), "y": r["equity"]}
            for _, r in s.iterrows() if not pd.isnull(r["fecha"])]

def monthly(df):
    if df.empty:
        return []
    s = df.copy()
    s["month"] = s["fecha"].dt.to_period("M")
    g = s.groupby("month")["resultado"].sum().reset_index()
    return [{"x": str(r["month"]), "y": round(r["resultado"], 2)} for _, r in g.iterrows()]

# ── Cargar datos ──────────────────────────────
dfs      = {name: load_sheet(name) for name in SHEETS}
all_df   = pd.concat(dfs.values(), ignore_index=True)

# ── Calcular ──────────────────────────────────
data = {
    "updated": datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
    "global": {
        "metrics": metrics(all_df),
        "equity":  equity_curve(all_df),
        "monthly": monthly(all_df),
    },
    "signals": {}
}
for name, df in dfs.items():
    data["signals"][name] = {
        "metrics": metrics(df),
        "equity":  equity_curve(df),
        "monthly": monthly(df),
    }

# ── Generar HTML ──────────────────────────────
json_blob = json.dumps(data)

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gold Oracle Scalper — Live Results</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg:       #0a0a0f;
    --surface:  #111118;
    --border:   #1e1e2e;
    --gold:     #f0c040;
    --gold2:    #d4a017;
    --green:    #22c55e;
    --red:      #ef4444;
    --muted:    #6b7280;
    --text:     #e8e8f0;
    --subtext:  #9ca3af;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
  }}

  /* ─ Header ─ */
  header {{
    border-bottom: 1px solid var(--border);
    padding: 1.5rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    background: linear-gradient(135deg, #0a0a0f 0%, #12100a 100%);
  }}
  .logo {{ display: flex; align-items: center; gap: .75rem; }}
  .logo-icon {{
    width: 38px; height: 38px;
    background: var(--gold);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
  }}
  .logo-text h1 {{ font-size: 1.1rem; font-weight: 800; letter-spacing: -.02em; }}
  .logo-text span {{ font-size: .75rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; }}
  .updated {{ font-family: 'JetBrains Mono', monospace; font-size: .7rem; color: var(--muted); }}
  .live-dot {{
    display: inline-block; width: 6px; height: 6px;
    background: var(--green); border-radius: 50%;
    margin-right: .4rem; animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%,100% {{ opacity:1; }} 50% {{ opacity:.3; }}
  }}

  /* ─ Tabs ─ */
  .tabs {{
    padding: 1.5rem 2rem 0;
    display: flex; gap: .5rem; flex-wrap: wrap;
    border-bottom: 1px solid var(--border);
  }}
  .tab {{
    padding: .5rem 1.2rem;
    border-radius: 6px 6px 0 0;
    background: transparent;
    border: 1px solid transparent;
    border-bottom: none;
    color: var(--muted);
    font-family: 'Syne', sans-serif;
    font-size: .85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all .2s;
    position: relative;
    bottom: -1px;
  }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{
    background: var(--surface);
    border-color: var(--border);
    color: var(--gold);
    border-bottom-color: var(--surface);
  }}

  /* ─ Main ─ */
  main {{ padding: 2rem; max-width: 1400px; margin: 0 auto; }}
  .panel {{ display: none; }}
  .panel.active {{ display: block; }}

  /* ─ KPI Grid ─ */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .kpi {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1rem;
    transition: border-color .2s;
  }}
  .kpi:hover {{ border-color: var(--gold2); }}
  .kpi-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: .5rem;
  }}
  .kpi-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    line-height: 1;
  }}
  .kpi-value.gold  {{ color: var(--gold); }}
  .kpi-value.green {{ color: var(--green); }}
  .kpi-value.red   {{ color: var(--red); }}
  .kpi-value.auto  {{ /* colored by JS */ }}

  /* ─ Charts ─ */
  .charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }}
  @media(max-width:768px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
  }}
  .chart-title {{
    font-size: .8rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: 1.2rem;
  }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* ─ Signals summary ─ */
  .signals-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1rem;
  }}
  .sig-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem;
    transition: border-color .2s;
  }}
  .sig-card:hover {{ border-color: var(--gold2); }}
  .sig-name {{
    font-weight: 800;
    font-size: 1rem;
    margin-bottom: .8rem;
    display: flex; align-items: center; gap: .5rem;
  }}
  .sig-dot {{
    width: 8px; height: 8px; border-radius: 50%;
  }}
  .sig-row {{
    display: flex; justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: .78rem;
    padding: .2rem 0;
    border-bottom: 1px solid var(--border);
  }}
  .sig-row:last-child {{ border-bottom: none; }}
  .sig-row span:first-child {{ color: var(--muted); }}

  /* ─ Footer ─ */
  footer {{
    text-align: center;
    padding: 2rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div class="logo-text">
      <h1>Gold Oracle Scalper</h1>
      <span>XAUUSD · Live Performance</span>
    </div>
  </div>
  <div class="updated">
    <span class="live-dot"></span>
    Actualizado: <span id="ts"></span>
  </div>
</header>

<div class="tabs">
  <button class="tab active" data-tab="global">Global</button>
  <button class="tab" data-tab="Tendencia">Tendencia</button>
  <button class="tab" data-tab="Momentum">Momentum</button>
  <button class="tab" data-tab="Reversion">Reversión</button>
  <button class="tab" data-tab="Breakout">Breakout</button>
</div>

<main>
  <div id="global" class="panel active"></div>
  <div id="Tendencia" class="panel"></div>
  <div id="Momentum" class="panel"></div>
  <div id="Reversion" class="panel"></div>
  <div id="Breakout" class="panel"></div>
</main>

<footer>Gold Oracle Scalper · Resultados en tiempo real · Datos desde Google Sheets</footer>

<script>
const DATA = {json_blob};
const COLORS = {{
  Tendencia: '#f0c040',
  Momentum:  '#818cf8',
  Reversion: '#34d399',
  Breakout:  '#fb923c',
}};

document.getElementById('ts').textContent = DATA.updated;

// ─ Tab switching ─
document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab, .panel').forEach(el => el.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  }});
}});

// ─ KPI helpers ─
function fmtMoney(v) {{
  const s = (v >= 0 ? '+' : '') + v.toFixed(2) + ' $';
  return s;
}}
function colorClass(v) {{
  return v > 0 ? 'green' : v < 0 ? 'red' : '';
}}

function renderKPIs(m, container) {{
  const pf = m.profit_factor === Infinity ? '∞' : m.profit_factor;
  container.innerHTML += `
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">Beneficio Total</div>
      <div class="kpi-value ${{colorClass(m.profit)}}">${{fmtMoney(m.profit)}}</div></div>
    <div class="kpi"><div class="kpi-label">Win Rate</div>
      <div class="kpi-value gold">${{m.winrate}}%</div></div>
    <div class="kpi"><div class="kpi-label">Profit Factor</div>
      <div class="kpi-value gold">${{pf}}</div></div>
    <div class="kpi"><div class="kpi-label">Total Trades</div>
      <div class="kpi-value">${{m.total}}</div></div>
    <div class="kpi"><div class="kpi-label">Ganadoras</div>
      <div class="kpi-value green">${{m.wins}}</div></div>
    <div class="kpi"><div class="kpi-label">Perdedoras</div>
      <div class="kpi-value red">${{m.losses}}</div></div>
    <div class="kpi"><div class="kpi-label">Media Ganadora</div>
      <div class="kpi-value green">${{m.avg_win}} $</div></div>
    <div class="kpi"><div class="kpi-label">Media Perdedora</div>
      <div class="kpi-value red">${{m.avg_loss}} $</div></div>
  </div>`;
}}

// ─ Charts ─
let chartInstances = {{}};
function destroyChart(id) {{
  if (chartInstances[id]) {{ chartInstances[id].destroy(); delete chartInstances[id]; }}
}}

function renderCharts(equity, monthly, prefix, accentColor) {{
  const eqId  = prefix + '_eq';
  const moId  = prefix + '_mo';
  const wrap  = document.getElementById(prefix + '_charts');
  wrap.innerHTML = `
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-title">Curva de Equity</div>
      <div class="chart-wrap"><canvas id="${{eqId}}"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Beneficio Mensual</div>
      <div class="chart-wrap"><canvas id="${{moId}}"></canvas></div>
    </div>
  </div>`;

  // Equity
  destroyChart(eqId);
  const eqCtx = document.getElementById(eqId).getContext('2d');
  const grad  = eqCtx.createLinearGradient(0,0,0,220);
  grad.addColorStop(0, accentColor + '40');
  grad.addColorStop(1, accentColor + '00');
  chartInstances[eqId] = new Chart(eqCtx, {{
    type: 'line',
    data: {{
      labels:   equity.map(p => p.x),
      datasets: [{{ label: 'Equity', data: equity.map(p => p.y),
        borderColor: accentColor, borderWidth: 2,
        backgroundColor: grad, fill: true,
        pointRadius: 0, tension: .4 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color:'#6b7280', maxTicksLimit:6 }}, grid: {{ color:'#1e1e2e' }} }},
        y: {{ ticks: {{ color:'#6b7280' }}, grid: {{ color:'#1e1e2e' }} }}
      }}
    }}
  }});

  // Monthly bars
  destroyChart(moId);
  const moCtx = document.getElementById(moId).getContext('2d');
  chartInstances[moId] = new Chart(moCtx, {{
    type: 'bar',
    data: {{
      labels:   monthly.map(p => p.x),
      datasets: [{{ label: 'Beneficio', data: monthly.map(p => p.y),
        backgroundColor: monthly.map(p => p.y >= 0 ? '#22c55e80' : '#ef444480'),
        borderColor:     monthly.map(p => p.y >= 0 ? '#22c55e'   : '#ef4444'),
        borderWidth: 1, borderRadius: 4 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color:'#6b7280' }}, grid: {{ color:'#1e1e2e' }} }},
        y: {{ ticks: {{ color:'#6b7280' }}, grid: {{ color:'#1e1e2e' }} }}
      }}
    }}
  }});
}}

function renderSignalCards(container) {{
  let html = '<div class="signals-grid">';
  for (const [name, d] of Object.entries(DATA.signals)) {{
    const m   = d.metrics;
    const col = COLORS[name] || '#888';
    const pf  = m.profit_factor === Infinity ? '∞' : m.profit_factor;
    html += `
    <div class="sig-card">
      <div class="sig-name">
        <span class="sig-dot" style="background:${{col}}"></span>${{name}}
      </div>
      <div class="sig-row"><span>Beneficio</span><span style="color:${{m.profit>=0?'#22c55e':'#ef4444'}}">${{fmtMoney(m.profit)}}</span></div>
      <div class="sig-row"><span>Win Rate</span><span style="color:${{col}}">${{m.winrate}}%</span></div>
      <div class="sig-row"><span>Profit Factor</span><span>${{pf}}</span></div>
      <div class="sig-row"><span>Trades</span><span>${{m.total}}</span></div>
    </div>`;
  }}
  html += '</div>';
  container.innerHTML += html;
}}

// ─ Build panels ─
function buildPanel(panelId, title, mdata, eq, mo, color, showSigCards) {{
  const p = document.getElementById(panelId);
  renderKPIs(mdata, p);
  p.innerHTML += `<div id="${{panelId}}_charts"></div>`;
  renderCharts(eq, mo, panelId, color);
  if (showSigCards) renderSignalCards(p);
}}

buildPanel('global',    'Global',    DATA.global.metrics,               DATA.global.equity,               DATA.global.monthly,              '#f0c040', true);
buildPanel('Tendencia', 'Tendencia', DATA.signals.Tendencia.metrics,    DATA.signals.Tendencia.equity,    DATA.signals.Tendencia.monthly,   COLORS.Tendencia, false);
buildPanel('Momentum',  'Momentum',  DATA.signals.Momentum.metrics,     DATA.signals.Momentum.equity,     DATA.signals.Momentum.monthly,    COLORS.Momentum,  false);
buildPanel('Reversion', 'Reversión', DATA.signals.Reversion.metrics,    DATA.signals.Reversion.equity,    DATA.signals.Reversion.monthly,   COLORS.Reversion, false);
buildPanel('Breakout',  'Breakout',  DATA.signals.Breakout.metrics,     DATA.signals.Breakout.equity,     DATA.signals.Breakout.monthly,    COLORS.Breakout,  false);
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ index.html generado correctamente.")
print(f"   Trades totales: {data['global']['metrics']['total']}")
print(f"   Win Rate:       {data['global']['metrics']['winrate']}%")
print(f"   Beneficio:      {data['global']['metrics']['profit']} $")
