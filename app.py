from datetime import datetime
import json
import os
import threading
import webbrowser

from flask import Flask, render_template_string

import main

app = Flask(__name__)


HTML_TEMPLATE = """<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Crypto Portfolio Live Dashboard</title>
</head>
<body>
  <h1>Crypto Portfolio Live Dashboard</h1>
  <div>생성 시각: {{ generated_at }}</div>
  <div>표시 합계 (USDT): <span id=\"visible-total\">{{ total_usdt_fmt }}</span></div>

  <section id=\"toggle-zone\">
    <div>거래소</div>
    {% for exchange in exchanges %}
    <label>
      <input type=\"checkbox\" class=\"exchange-toggle\" value=\"{{ exchange }}\" checked />
      <span>{{ exchange }}</span>
    </label>
    {% endfor %}
  </section>

  <table>
    <thead>
      <tr>
        <th>Symbol</th>
        <th>Amount</th>
        <th>USDT Price</th>
        <th>USDT Value</th>
      </tr>
    </thead>
    <tbody id=\"asset-body\">
      {% for row in rows %}
      <tr class=\"asset-row\" data-contrib='{{ row.contrib_json | safe }}'>
        <td>{{ row.symbol }}</td>
        <td class=\"amount-cell\">{{ row.amount }}</td>
        <td class=\"price-cell\">{{ row.usdt_price }}</td>
        <td class=\"value-cell\">{{ row.usdt_value }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <script>
    const checkboxes = Array.from(document.querySelectorAll('.exchange-toggle'));
    const rows = Array.from(document.querySelectorAll('.asset-row')).map((row) => ({
      el: row,
      contrib: JSON.parse(row.dataset.contrib || '{}')
    }));
    const totalEl = document.getElementById('visible-total');

    function formatUsdt(value) {
      return value.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
    }

    function applyFilter() {
      const visibleExchanges = new Set(checkboxes.filter((cb) => cb.checked).map((cb) => cb.value));
      let total = 0;

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

        const price = amount === 0 ? 0 : usdtValue / amount;
        item.el.querySelector('.amount-cell').textContent = amount.toFixed(8);
        item.el.querySelector('.price-cell').textContent = price.toFixed(5);
        item.el.querySelector('.value-cell').textContent = usdtValue.toFixed(3);

        if (amount === 0 && usdtValue === 0) {
          item.el.style.display = 'none';
        } else {
          item.el.style.display = '';
          total += usdtValue;
        }
      });

      totalEl.textContent = formatUsdt(total);
    }

    checkboxes.forEach((cb) => cb.addEventListener('change', applyFilter));
    applyFilter();
  </script>
</body>
</html>
"""


def _build_symbol_rows(cw):
    exchange_assets = getattr(cw, "exchange_assets", {}) or {}
    symbol_map = {}

    for exchange, assets in exchange_assets.items():
        for asset in assets.values():
            if asset.amount == 0 and asset.usdt_value == 0:
                continue

            symbol = asset.symbol
            if symbol not in symbol_map:
                symbol_map[symbol] = {
                    "symbol": symbol,
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

    return render_template_string(
        HTML_TEMPLATE,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        exchanges=exchanges,
        rows=rows,
        total_usdt=total_usdt,
        total_usdt_fmt=f"{total_usdt:,.3f}",
    )


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    url = f"http://{host}:{port}"
    auto_open = os.getenv("AUTO_OPEN_BROWSER", "1") == "1"

    if auto_open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=True, use_reloader=False)
