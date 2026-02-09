"""
Embedded web dashboard for PolyBot.
Serves a single-page dark-themed dashboard with live health + session data.
"""

import asyncio
import sqlite3
import time
import logging

from aiohttp import web

from bot.config import DB_PATH

logger = logging.getLogger(__name__)

_START_TIME = time.time()


# ── API handlers ────────────────────────────────────────────────────────────

async def handle_health(request: web.Request) -> web.Response:
    pf = request.app["price_feed"]
    active = request.app["active_tasks"]

    price = pf.price
    ticks = pf.get_recent_ticks(60)

    data = {
        "btc_price": price,
        "price_available": pf.is_available,
        "ws_connected": pf.connected,
        "last_update_age_secs": round(pf.last_update_age, 2),
        "tick_count": pf.tick_count,
        "active_market_count": len(active),
        "active_market_ids": list(active.keys()),
        "uptime_secs": round(time.time() - _START_TIME, 1),
        "ticks": ticks,
    }
    return web.json_response(data)


async def handle_sessions(request: web.Request) -> web.Response:
    rows = await asyncio.to_thread(_query_today_sessions)
    return web.json_response(rows)


def _query_today_sessions() -> list[dict]:
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT market_slug, start_time, end_time, beat_price, "
                "decision, skip_reason, "
                "distance_at_decision, would_buy, actual_outcome, "
                "would_have_won, theoretical_pnl, logged_at "
                "FROM markets WHERE logged_at > datetime('now', '-1 day') "
                "ORDER BY logged_at DESC"
            )
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Dashboard DB query error: {e}")
        return []


async def handle_index(request: web.Request) -> web.Response:
    return web.Response(text=_HTML, content_type="text/html")


# ── App factory ─────────────────────────────────────────────────────────────

def create_dashboard_app(price_feed, active_tasks) -> web.Application:
    app = web.Application()
    app["price_feed"] = price_feed
    app["active_tasks"] = active_tasks
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/sessions", handle_sessions)
    return app


# ── HTML template ───────────────────────────────────────────────────────────

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PolyBot Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    background: #0d1117; color: #c9d1d9; padding: 20px;
  }
  h1 { font-size: 1.3rem; color: #58a6ff; margin-bottom: 16px; }
  h2 { font-size: 1rem; color: #8b949e; margin: 18px 0 8px; }

  .health-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 10px; margin-bottom: 18px;
  }
  .health-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px; text-align: center;
  }
  .health-card .label { font-size: 0.7rem; color: #8b949e; text-transform: uppercase; }
  .health-card .value { font-size: 1.3rem; color: #58a6ff; margin-top: 4px; }
  .health-card .value.ok { color: #3fb950; }
  .health-card .value.warn { color: #d29922; }
  .health-card .value.bad { color: #f85149; }

  #chart-container {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px; margin-bottom: 18px;
  }
  canvas { width: 100%; height: 180px; display: block; }

  table {
    width: 100%; border-collapse: collapse; font-size: 0.8rem;
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    overflow: hidden;
  }
  th {
    background: #1c2128; color: #8b949e; text-transform: uppercase;
    font-size: 0.65rem; padding: 8px 6px; text-align: left;
  }
  td { padding: 6px; border-top: 1px solid #21262d; }
  tr:hover { background: #1c2128; }
  .win { color: #3fb950; } .loss { color: #f85149; } .skip { color: #8b949e; }

  .summary-row {
    display: flex; gap: 20px; margin-top: 10px; font-size: 0.85rem;
    color: #8b949e;
  }
  .summary-row span { color: #c9d1d9; }

  .stale-banner {
    display: none; background: #f8514933; border: 1px solid #f85149;
    border-radius: 6px; padding: 8px 14px; margin-bottom: 14px;
    color: #f85149; font-size: 0.85rem;
  }
</style>
</head>
<body>

<h1>PolyBot Dashboard</h1>
<div class="stale-banner" id="stale-banner">Dashboard data stale — API unreachable</div>

<div class="health-grid" id="health-grid"></div>

<h2>BTC/USD — 60s Tick Chart</h2>
<div id="chart-container"><canvas id="chart"></canvas></div>

<h2>Sessions (last 24h)</h2>
<table>
  <thead>
    <tr>
      <th>Session</th><th>Beat</th><th>Decision</th><th>Reason/Side</th>
      <th>Dist</th><th>Outcome</th><th>Result</th><th>P&amp;L</th>
    </tr>
  </thead>
  <tbody id="sessions-body"></tbody>
</table>
<div class="summary-row" id="summary-row"></div>

<script>
(function() {
  let lastHealthOk = 0;

  function esc(s) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  function fmtSession(startStr, endStr) {
    if (!startStr || !endStr) return '—';
    const s = new Date(startStr), e = new Date(endStr);
    if (isNaN(s) || isNaN(e)) return '—';
    const et = {timeZone:'America/New_York'};
    const mo = s.toLocaleString('en-US',{...et,month:'short'});
    const day = s.toLocaleString('en-US',{...et,day:'numeric'});
    const sh = s.toLocaleString('en-US',{...et,hour:'numeric',minute:'2-digit',hour12:true}).replace(' ','');
    const eh = e.toLocaleString('en-US',{...et,hour:'numeric',minute:'2-digit',hour12:true}).replace(' ','');
    return mo + ' ' + day + ', ' + sh + '-' + eh + ' ET';
  }

  // ── Health polling ──────────────────────────────────────
  async function fetchHealth() {
    try {
      const r = await fetch('/api/health');
      const d = await r.json();
      lastHealthOk = Date.now();
      document.getElementById('stale-banner').style.display = 'none';
      renderHealth(d);
      renderChart(d.ticks || []);
    } catch(e) {
      if (Date.now() - lastHealthOk > 15000)
        document.getElementById('stale-banner').style.display = 'block';
    }
  }

  function renderHealth(d) {
    const fmt = (v) => v != null ? '$' + Number(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}) : '—';
    const age = d.last_update_age_secs;
    const ageCls = age < 5 ? 'ok' : age < 15 ? 'warn' : 'bad';
    const wsCls = d.ws_connected ? 'ok' : 'bad';
    const upH = (d.uptime_secs / 3600).toFixed(1);

    const cards = [
      {label:'BTC/USD', value: fmt(d.btc_price), cls: d.price_available ? 'ok' : 'warn'},
      {label:'Feed', value: d.price_available ? 'LIVE' : 'STALE', cls: d.price_available ? 'ok' : 'bad'},
      {label:'WebSocket', value: d.ws_connected ? 'CONNECTED' : 'DOWN', cls: wsCls},
      {label:'Last Update', value: age < 999 ? age.toFixed(1) + 's' : '∞', cls: ageCls},
      {label:'Active Markets', value: d.active_market_count, cls: ''},
      {label:'Tick Buffer', value: d.tick_count, cls: ''},
      {label:'Uptime', value: upH + 'h', cls: ''},
    ];

    const el = document.getElementById('health-grid');
    el.innerHTML = cards.map(c =>
      '<div class="health-card"><div class="label">' + c.label +
      '</div><div class="value ' + c.cls + '">' + c.value + '</div></div>'
    ).join('');
  }

  // ── Tick chart ──────────────────────────────────────────
  function renderChart(ticks) {
    const canvas = document.getElementById('chart');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    const W = rect.width - 24;
    const H = 180;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    ctx.fillStyle = '#161b22'; ctx.fillRect(0, 0, W, H);

    if (ticks.length < 2) {
      ctx.fillStyle = '#8b949e'; ctx.font = '13px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Waiting for ticks...', W/2, H/2);
      return;
    }

    const prices = ticks.map(t => t.price);
    const times  = ticks.map(t => t.ts);
    const minP = Math.min(...prices), maxP = Math.max(...prices);
    const pad = 30;
    const range = maxP - minP || 1;

    const x = (i) => pad + (i / (ticks.length - 1)) * (W - pad * 2);
    const y = (p) => H - pad - ((p - minP) / range) * (H - pad * 2);

    // grid lines
    ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const gy = pad + i * (H - pad*2) / 4;
      ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(W - pad, gy); ctx.stroke();
    }

    // price line
    ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 2;
    ctx.beginPath();
    ticks.forEach((t, i) => {
      i === 0 ? ctx.moveTo(x(i), y(t.price)) : ctx.lineTo(x(i), y(t.price));
    });
    ctx.stroke();

    // labels
    ctx.fillStyle = '#8b949e'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText('$' + maxP.toFixed(2), pad - 4, pad + 4);
    ctx.fillText('$' + minP.toFixed(2), pad - 4, H - pad + 4);

    // current price label
    const last = prices[prices.length - 1];
    ctx.fillStyle = '#58a6ff'; ctx.textAlign = 'left';
    ctx.fillText('$' + last.toFixed(2), x(ticks.length - 1) + 4, y(last) + 4);
  }

  // ── Sessions polling ────────────────────────────────────
  async function fetchSessions() {
    try {
      const r = await fetch('/api/sessions');
      const rows = await r.json();
      renderSessions(rows);
    } catch(e) {}
  }

  function renderSessions(rows) {
    const tbody = document.getElementById('sessions-body');
    let wins = 0, losses = 0, active = 0, netPnl = 0;

    tbody.innerHTML = rows.map(r => {
      const dec = r.decision || '?';
      const isActive = dec === 'ACTIVE';
      const won = r.would_have_won;
      const pnl = r.theoretical_pnl;

      if (isActive) active++;
      if (won === 1) wins++;
      if (won === 0 && isActive) losses++;
      if (pnl != null) netPnl += pnl;

      const result = won === 1 ? '<span class="win">WIN</span>'
        : won === 0 ? '<span class="loss">LOSS</span>'
        : '—';
      const pnlStr = pnl != null
        ? '<span class="' + (pnl >= 0 ? 'win' : 'loss') + '">$' + pnl.toFixed(2) + '</span>'
        : '—';
      const decCls = isActive ? 'win' : 'skip';
      const reasonOrSide = isActive ? (r.would_buy || '—') : (r.skip_reason || '—');
      const dist = r.distance_at_decision != null ? r.distance_at_decision.toFixed(0) : '—';
      const beat = r.beat_price != null ? '$' + Number(r.beat_price).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}) : '—';
      const session = fmtSession(r.start_time, r.end_time);

      const slug = r.market_slug || '';
      const href = slug ? 'https://polymarket.com/event/' + encodeURIComponent(slug) : '';

      return '<tr>' +
        '<td>' + (href ? '<a href="' + href + '" target="_blank" style="color:#58a6ff;text-decoration:none">' + esc(session) + '</a>' : esc(session)) + '</td>' +
        '<td>' + beat + '</td>' +
        '<td class="' + decCls + '">' + esc(dec) + '</td>' +
        '<td>' + esc(reasonOrSide) + '</td>' +
        '<td>' + dist + '</td>' +
        '<td>' + esc(r.actual_outcome || '—') + '</td>' +
        '<td>' + result + '</td>' +
        '<td>' + pnlStr + '</td>' +
        '</tr>';
    }).join('');

    const total = rows.length;
    const wr = (wins + losses) > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : '—';
    document.getElementById('summary-row').innerHTML =
      'Total: <span>' + total + '</span> &nbsp;|&nbsp; ' +
      'Active: <span>' + active + '</span> &nbsp;|&nbsp; ' +
      'Wins: <span class="win">' + wins + '</span> &nbsp;|&nbsp; ' +
      'Losses: <span class="loss">' + losses + '</span> &nbsp;|&nbsp; ' +
      'Win Rate: <span>' + wr + '%</span> &nbsp;|&nbsp; ' +
      'Net P&L: <span class="' + (netPnl >= 0 ? 'win' : 'loss') + '">$' + netPnl.toFixed(2) + '</span>';
  }

  // ── Kick off polling ────────────────────────────────────
  fetchHealth();
  fetchSessions();
  setInterval(fetchHealth, 5000);
  setInterval(fetchSessions, 15000);
})();
</script>
</body>
</html>
"""
