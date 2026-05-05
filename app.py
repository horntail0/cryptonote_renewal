from datetime import datetime
import json
import os
import threading
import webbrowser

from flask import Flask, render_template_string

import main
from CoinAsset import CLUSTER_ASSET

app = Flask(__name__)


HTML_TEMPLATE = """<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Crypto Portfolio Live Dashboard</title>
  <style>
    :root {
      --bg-1: #0f172a;
      --bg-2: #1e293b;
      --card: rgba(15, 23, 42, 0.72);
      --line: rgba(148, 163, 184, 0.2);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #22d3ee;
      --accent-2: #38bdf8;
      --ok: #34d399;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: \"Segoe UI\", \"Pretendard\", sans-serif;
      background:
        radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.25), transparent 35%),
        radial-gradient(circle at 90% 10%, rgba(34, 211, 238, 0.2), transparent 28%),
        linear-gradient(120deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
      padding: 28px;
    }
    .container { max-width: 1200px; margin: 0 auto; display: grid; gap: 18px; }
    .panel { background: var(--card); backdrop-filter: blur(8px); border: 1px solid var(--line); border-radius: 16px; box-shadow: 0 12px 40px rgba(2, 8, 23, 0.35); }
    .hero { padding: 20px 22px; display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }
    .hero-left { flex: 1; }
    .title { margin: 0; font-size: 28px; letter-spacing: 0.2px; font-weight: 800; }
    .sub { margin-top: 8px; color: var(--muted); font-size: 13px; }
    .note { margin-top: 8px; color: #fda4af; font-size: 12px; font-weight: 600; }
    .total { text-align: right; }
    .total .label { color: var(--muted); font-size: 12px; }
    .total .value { color: var(--ok); font-size: 26px; font-weight: 800; margin-top: 4px; }
    .summary-grid { margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(165px, 1fr)); gap: 10px; }
    .summary-card { background: rgba(15, 23, 42, 0.85); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; }
    .summary-k { color: var(--muted); font-size: 11px; }
    .summary-v { margin-top: 5px; font-size: 16px; font-weight: 700; }
    .toolbar { padding: 14px 18px; display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
    .toggle-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .toolbar .k { color: var(--muted); font-size: 13px; margin-right: 4px; }
    .chip { border: 1px solid var(--line); background: rgba(15, 23, 42, 0.85); border-radius: 999px; padding: 6px 11px; display: inline-flex; align-items: center; gap: 7px; font-size: 13px; }
    .chip input[type=\"checkbox\"] { accent-color: var(--accent-2); width: 15px; height: 15px; }
    .table-wrap { overflow-x: auto; border-radius: 16px; }
    table { width: 100%; border-collapse: collapse; min-width: 720px; }
    th, td { padding: 12px 10px; border-bottom: 1px solid var(--line); font-size: 14px; }
    th { text-align: left; color: #cbd5e1; background: rgba(15, 23, 42, 0.9); position: sticky; top: 0; z-index: 1; }
    th.sortable { cursor: pointer; user-select: none; }
    th.sortable .sort-indicator { margin-left: 6px; color: var(--muted); font-size: 11px; }
    td.num { text-align: right; }
    tr:hover td { background: rgba(56, 189, 248, 0.08); transition: 0.2s ease; }
    .exchange { font-weight: 700; color: var(--accent); }
    .foot { padding: 12px 18px 18px; color: var(--muted); font-size: 12px; }
    @media (max-width: 720px) {
      body { padding: 14px; }
      .hero { flex-direction: column; align-items: flex-start; }
      .total { text-align: left; }
      .title { font-size: 23px; }
    }
  </style>
</head>
<body>
  <div class=\"container\">
    <section class=\"panel hero\">
      <div class=\"hero-left\">
        <h1 class=\"title\">Crypto Portfolio Live Dashboard</h1>
        <div class=\"sub\">생성 시각: {{ generated_at }}</div>
        <div class=\"note\">참고: 717702원은 사고로 유실되었습니다.</div>
        <div class=\"summary-grid\">
          <div class=\"summary-card\"><div class=\"summary-k\">Total Assets (KRW)</div><div class=\"summary-v\">{{ total_assets_krw_fmt }}</div></div>
          <div class=\"summary-card\"><div class=\"summary-k\">USDT/KRW</div><div class=\"summary-v\">{{ usdt_krw_fmt }}</div></div>
          <div class=\"summary-card\"><div class=\"summary-k\">Stable Ratio (%)</div><div class=\"summary-v\">{{ stable_ratio_fmt }}</div></div>
          <div class=\"summary-card\"><div class=\"summary-k\">KRW Principal</div><div class=\"summary-v\">{{ krw_principal_fmt }}</div></div>
          <div class=\"summary-card\"><div class=\"summary-k\">Benefit (KRW)</div><div class=\"summary-v\">{{ benefit_krw_fmt }}</div></div>
          <div class=\"summary-card\"><div class=\"summary-k\">Benefit Ratio (%)</div><div class=\"summary-v\">{{ benefit_ratio_fmt }}</div></div>
        </div>
      </div>
      <div class=\"total\">
        <div class=\"label\">표시 합계 (USDT)</div>
        <div class=\"value\" id=\"visible-total\">{{ total_usdt_fmt }}</div>
      </div>
    </section>

    <section class=\"panel toolbar\" id=\"toggle-zone\">
      <div class=\"toggle-row\">
        <span class=\"k\">모드</span>
        <label class=\"chip\">
          <input type=\"checkbox\" id=\"cluster-toggle\" checked />
          <span>Clustered</span>
        </label>
      </div>
      <div class=\"toggle-row\">
        <span class=\"k\">거래소</span>
        {% for exchange in exchanges %}
        <label class=\"chip\">
          <input type=\"checkbox\" class=\"exchange-toggle\" value=\"{{ exchange }}\" checked />
          <span>{{ exchange }}</span>
        </label>
        {% endfor %}
      </div>
    </section>

    <section class=\"panel table-wrap\">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th style=\"text-align:right\">Amount</th>
            <th class=\"sortable\" data-sort-key=\"price\" style=\"text-align:right\">USDT Price<span class=\"sort-indicator\">↕</span></th>
            <th class=\"sortable\" data-sort-key=\"value\" style=\"text-align:right\">USDT Value<span class=\"sort-indicator\">↓</span></th>
            <th style=\"text-align:right\">Ratio (%)</th>
          </tr>
        </thead>
        <tbody id=\"asset-body\">
          {% for row in rows %}
          <tr class=\"asset-row\" data-main=\"{{ row.main_symbol }}\" data-contrib='{{ row.contrib_json | safe }}'>
            <td class=\"exchange\">{{ row.symbol }}</td>
            <td class=\"num amount-cell\">{{ row.amount }}</td>
            <td class=\"num price-cell\">{{ row.usdt_price }}</td>
            <td class=\"num value-cell\">{{ row.usdt_value }}</td>
            <td class=\"num ratio-cell\">0.00</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <div class=\"foot\">Clustered ON: 메인 심볼 기준으로 합산 표시됩니다.</div>
    </section>
  </div>

  <script>
    const checkboxes = Array.from(document.querySelectorAll('.exchange-toggle'));
    const clusterToggle = document.getElementById('cluster-toggle');
    const tbody = document.getElementById('asset-body');
    const sortableHeaders = Array.from(document.querySelectorAll('th.sortable'));
    let sortKey = 'value';
    let sortDir = 'desc';
    const rows = Array.from(document.querySelectorAll('.asset-row')).map((row) => ({
      el: row,
      symbol: row.children[0].textContent,
      main: row.dataset.main,
      contrib: JSON.parse(row.dataset.contrib || '{}'),
      displayPrice: 0,
      displayValue: 0
    }));
    const totalEl = document.getElementById('visible-total');

    function formatUsdt(value) { return value.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }); }
    function formatAmount(value) { return value.toLocaleString(undefined, { minimumFractionDigits: 8, maximumFractionDigits: 8 }); }
    function formatPrice(value) { return value.toLocaleString(undefined, { minimumFractionDigits: 5, maximumFractionDigits: 5 }); }
    function formatRatio(value) { return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
    function updateSortIndicators() {
      sortableHeaders.forEach((th) => {
        const indicator = th.querySelector('.sort-indicator');
        const key = th.dataset.sortKey;
        indicator.textContent = key === sortKey ? (sortDir === 'asc' ? '↑' : '↓') : '↕';
      });
    }
    function sortVisibleRows() {
      const visibleRows = rows.filter((item) => item.el.style.display !== 'none');
      visibleRows.sort((a, b) => {
        const aVal = sortKey === 'price' ? a.displayPrice : a.displayValue;
        const bVal = sortKey === 'price' ? b.displayPrice : b.displayValue;
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      });
      visibleRows.forEach((item) => tbody.appendChild(item.el));
    }

    function applyFilter() {
      const visibleExchanges = new Set(checkboxes.filter((cb) => cb.checked).map((cb) => cb.value));
      const clusteredOn = clusterToggle.checked;

      rows.forEach((item) => {
        let amount = 0;
        let usdtValue = 0;
        Object.entries(item.contrib).forEach(([exchange, values]) => {
          if (!visibleExchanges.has(exchange)) {
            return;
          }
          amount += Number(values.amount || 0);
          usdtValue += Number(values.usdt_value || 0);
        });
        item.amount = amount;
        item.usdtValue = usdtValue;
      });

      let total = 0;
      if (clusteredOn) {
        const clusterTotals = {};
        const symbolPriceMap = {};

        rows.forEach((item) => {
          const itemPrice = item.amount === 0 ? 0 : item.usdtValue / item.amount;
          symbolPriceMap[item.symbol] = itemPrice;
          if (!clusterTotals[item.main]) {
            clusterTotals[item.main] = { usdtValue: 0 };
          }
          clusterTotals[item.main].usdtValue += item.usdtValue;
        });

        rows.forEach((item) => {
          if (item.symbol !== item.main) {
            item.el.style.display = 'none';
            return;
          }

          const summary = clusterTotals[item.main] || { usdtValue: 0 };
          const usdtValue = summary.usdtValue;
          let mainPrice = Number(symbolPriceMap[item.main] || 0);
          if (!(mainPrice > 0)) {
            const candidates = clusterPriceCandidates[item.main] || [];
            mainPrice = candidates.length > 0 ? Number(candidates[0]) : 0;
          }
          const amount = mainPrice > 0 ? usdtValue / mainPrice : 0;
          const usdtPrice = mainPrice > 0 ? mainPrice : 0;

          item.el.querySelector('.amount-cell').textContent = formatAmount(amount);
          item.el.querySelector('.price-cell').textContent = formatPrice(usdtPrice);
          item.el.querySelector('.value-cell').textContent = formatUsdt(usdtValue);
          item.displayPrice = usdtPrice;
          item.displayValue = usdtValue;

          if (amount === 0 && usdtValue === 0) {
            item.el.style.display = 'none';
          } else {
            item.el.style.display = '';
            total += usdtValue;
          }
        });
      } else {
        rows.forEach((item) => {
          const amount = item.amount;
          const usdtValue = item.usdtValue;
          const usdtPrice = amount === 0 ? 0 : usdtValue / amount;

          item.el.querySelector('.amount-cell').textContent = formatAmount(amount);
          item.el.querySelector('.price-cell').textContent = formatPrice(usdtPrice);
          item.el.querySelector('.value-cell').textContent = formatUsdt(usdtValue);
          item.displayPrice = usdtPrice;
          item.displayValue = usdtValue;

          if (amount === 0 && usdtValue === 0) {
            item.el.style.display = 'none';
          } else {
            item.el.style.display = '';
            total += usdtValue;
          }
        });
      }

      rows.forEach((item) => {
        const ratio = total > 0 && item.el.style.display !== 'none' ? (item.displayValue / total) * 100 : 0;
        item.el.querySelector('.ratio-cell').textContent = formatRatio(ratio);
      });

      sortVisibleRows();
      updateSortIndicators();
      totalEl.textContent = formatUsdt(total);
    }

    sortableHeaders.forEach((th) => {
      th.addEventListener('click', () => {
        const key = th.dataset.sortKey;
        if (sortKey === key) {
          sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          sortKey = key;
          sortDir = 'desc';
        }
        applyFilter();
      });
    });
    checkboxes.forEach((cb) => cb.addEventListener('change', applyFilter));
    clusterToggle.addEventListener('change', applyFilter);
    applyFilter();
  </script>
</body>
</html>
"""


def _build_symbol_rows(cw):
    exchange_assets = getattr(cw, "exchange_assets", {}) or {}
    symbol_map = {}

    symbol_to_main = {}
    for cluster in CLUSTER_ASSET:
        main_symbol = cluster[0]
        for sym in cluster:
            symbol_to_main[sym] = main_symbol

    for exchange, assets in exchange_assets.items():
        for asset in assets.values():
            if asset.amount == 0 and asset.usdt_value == 0:
                continue
            symbol = asset.symbol
            main_symbol = symbol_to_main.get(symbol, symbol)
            if symbol not in symbol_map:
                symbol_map[symbol] = {
                    "symbol": symbol,
                    "main_symbol": main_symbol,
                    "amount_raw": 0.0,
                    "usdt_value_raw": 0.0,
                    "contrib": {},
                }

            symbol_map[symbol]["amount_raw"] += float(asset.amount)
            symbol_map[symbol]["usdt_value_raw"] += float(asset.usdt_value)
            symbol_map[symbol]["contrib"][exchange] = {
                "amount": float(asset.amount),
                "usdt_value": float(asset.usdt_value),
                "usdt_price": float(asset.usdt_price),
            }

    rows = []
    for row in symbol_map.values():
        amount_raw = row["amount_raw"]
        usdt_value_raw = row["usdt_value_raw"]
        usdt_price_raw = usdt_value_raw / amount_raw if amount_raw else 0.0
        rows.append(
            {
                "symbol": row["symbol"],
                "main_symbol": row["main_symbol"],
                "amount": f"{amount_raw:,.8f}",
                "usdt_price": f"{usdt_price_raw:,.5f}",
                "usdt_value": f"{usdt_value_raw:,.3f}",
                "usdt_value_raw": usdt_value_raw,
                "contrib_json": json.dumps(row["contrib"], ensure_ascii=True),
            }
        )

    rows.sort(key=lambda x: x["usdt_value_raw"], reverse=True)
    return rows


@app.route("/")
def index():
    cw = main.main(output_format="none")
    rows = _build_symbol_rows(cw)
    exchanges = list(getattr(cw, "exchange_assets", {}).keys())
    total_usdt = sum(row["usdt_value_raw"] for row in rows)
    stable_ratio = (cw.Stable_Assets_value / cw.Total_Assets_value * 100) if cw.Total_Assets_value else 0.0
    krw_principal = cw.KRW_deposits - cw.KRW_withdrawals - cw.KRW_fees
    benefit_krw = (cw.Total_Assets_value * cw.CurrentKRWUSDT) - krw_principal
    total_assets_krw = cw.Total_Assets_value * cw.CurrentKRWUSDT

    return render_template_string(
        HTML_TEMPLATE,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        exchanges=exchanges,
        rows=rows,
        total_usdt=total_usdt,
        total_usdt_fmt=f"{total_usdt:,.3f}",
        total_assets_krw_fmt=f"{total_assets_krw:,.0f}",
        usdt_krw_fmt=f"{cw.CurrentKRWUSDT:,.5f}",
        stable_ratio_fmt=f"{stable_ratio:.2f}",
        krw_principal_fmt=f"{krw_principal:,.0f}",
        benefit_krw_fmt=f"{benefit_krw:,.0f}",
        benefit_ratio_fmt=f"{cw.Benefit_Ratio:.2f}",
    )


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    url = f"http://{host}:{port}"
    auto_open = os.getenv("AUTO_OPEN_BROWSER", "1") == "1"

    if auto_open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=True, use_reloader=False)

