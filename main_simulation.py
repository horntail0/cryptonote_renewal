import argparse
import os
import webbrowser
from datetime import datetime

import main as main_module
import CoinWallet


def recalculate_wallet_totals(cw):
    cw.Total_Assets_value = 0.0
    cw.Stable_Assets_value = 0.0
    for asset in cw.assets.values():
        cw.Total_Assets_value += asset.usdt_value
        if asset.IsStable:
            cw.Stable_Assets_value += asset.usdt_value
    main_module.calculate_ratios(cw)


def recalculate_benefit_ratio(cw):
    current_krw_balance = cw.KRW_deposits - cw.KRW_withdrawals - cw.KRW_fees
    if current_krw_balance == 0:
        cw.Benefit_Ratio = 0.0
        return 0.0, current_krw_balance
    cw.Benefit_Ratio = ((cw.Total_Assets_value * cw.CurrentKRWUSDT) - current_krw_balance) / current_krw_balance * 100
    return cw.Benefit_Ratio, current_krw_balance


def simulate_btc_price(cw, target_btc_price):
    if "BTC" not in cw.assets:
        print("[Simulation] BTC asset not found in wallet.")
        return False, None

    btc_asset = cw.assets["BTC"]
    before_price = btc_asset.usdt_price
    before_value = btc_asset.usdt_value
    before_total = cw.Total_Assets_value
    before_benefit_ratio = cw.Benefit_Ratio

    btc_asset.usdt_price = target_btc_price
    btc_asset.usdt_value = btc_asset.amount * target_btc_price
    recalculate_wallet_totals(cw)
    after_benefit_ratio, current_krw_balance = recalculate_benefit_ratio(cw)

    after_value = btc_asset.usdt_value
    after_total = cw.Total_Assets_value
    total_delta = after_total - before_total
    btc_delta = after_value - before_value

    simulation_result = {
        "btc_assumed_price": target_btc_price,
        "btc_amount": btc_asset.amount,
        "before_price": before_price,
        "before_value": before_value,
        "before_total": before_total,
        "after_value": after_value,
        "after_total": after_total,
        "total_delta": total_delta,
        "btc_delta": btc_delta,
        "btc_ratio": btc_asset.ratio,
        "stable_ratio": cw.Stable_Assets_value / cw.Total_Assets_value * 100,
        "before_benefit_ratio": before_benefit_ratio,
        "after_benefit_ratio": after_benefit_ratio,
        "current_krw_balance": current_krw_balance,
    }
    return True, simulation_result


def write_simulation_html(cw, simulation_result, output_path):
    top_assets = sorted(cw.assets.values(), key=lambda a: a.usdt_value, reverse=True)[:30]
    rows = []
    for asset in top_assets:
        rows.append(
            f"<tr><td>{asset.symbol}</td><td>{asset.amount:.8f}</td><td>{asset.usdt_price:,.4f}</td><td>{asset.usdt_value:,.2f}</td><td>{asset.ratio:.2f}%</td></tr>"
        )
    rows_html = "\n".join(rows)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BTC Simulation Report</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background: #f5f7fb; color: #1a1a1a; }}
    .card {{ background: white; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }}
    h1 {{ margin: 0 0 12px 0; font-size: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }}
    .k {{ font-size: 12px; color: #666; }}
    .v {{ font-size: 18px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid #e9edf5; padding: 10px 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #eef3ff; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>BTC Price Simulation</h1>
    <div>Generated at: {generated_at}</div>
  </div>
  <div class="card grid">
    <div><div class="k">Assumed BTC Price</div><div class="v">{simulation_result["btc_assumed_price"]:,.2f} USDT</div></div>
    <div><div class="k">BTC Amount</div><div class="v">{simulation_result["btc_amount"]:.8f}</div></div>
    <div><div class="k">BTC Value Change</div><div class="v">{simulation_result["before_value"]:,.2f} ->{simulation_result["after_value"]:,.2f}</div></div>
    <div><div class="k">Total Assets Change</div><div class="v">{simulation_result["before_total"]:,.2f} ->{simulation_result["after_total"]:,.2f}</div></div>
    <div><div class="k">Total Delta</div><div class="v">{simulation_result["total_delta"]:,.2f} USDT</div></div>
    <div><div class="k">BTC Ratio</div><div class="v">{simulation_result["btc_ratio"]:.2f}%</div></div>
    <div><div class="k">Stable Ratio</div><div class="v">{simulation_result["stable_ratio"]:.2f}%</div></div>
    <div><div class="k">Benefit Ratio</div><div class="v">{simulation_result["before_benefit_ratio"]:.2f}% ->{simulation_result["after_benefit_ratio"]:.2f}%</div></div>
    <div><div class="k">KRW Principal</div><div class="v">{simulation_result["current_krw_balance"]:,.0f} KRW</div></div>
  </div>
  <table>
    <thead>
      <tr><th>Symbol</th><th>Amount</th><th>USDT Price</th><th>USDT Value</th><th>Ratio</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--btc-price", type=float, default=70000.0, help="Target BTC price in USDT")
    parser.add_argument("--output", type=str, default="simulation_report.html", help="Output HTML report path")
    args = parser.parse_args()

    print("[Simulation] Running base wallet load...")
    original_export = CoinWallet.CoinWallet.export_assets_to_excel
    CoinWallet.CoinWallet.export_assets_to_excel = lambda self, filename="assets.xlsx": None
    try:
        base_cw = main_module.main()
    finally:
        CoinWallet.CoinWallet.export_assets_to_excel = original_export
    simulated_cw = base_cw
    ok, simulation_result = simulate_btc_price(simulated_cw, args.btc_price)
    if not ok:
        return

    output_path = os.path.abspath(args.output)
    write_simulation_html(simulated_cw, simulation_result, output_path)
    webbrowser.open(f"file:///{output_path.replace(os.sep, '/')}")
    print(f"[Simulation] Opened report: {output_path}")


if __name__ == "__main__":
    main()

