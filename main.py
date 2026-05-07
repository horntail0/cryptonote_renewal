import os
import subprocess
import time
import copy
import argparse
from datetime import datetime

import Binance_Reader
import Bithumb_Reader
import CoinWallet
import Gateio_Reader
import PersonalWallet_Reader
from CoinAsset import STABLE_ASSET
from dotenv import load_dotenv

os.environ["MOBILE"] = "0"
load_dotenv()


def create_personal_wallet_reader():
    wallet_file_path = os.getenv("PERSONAL_WALLET_FILE", "personal_wallet_assets.json")
    return PersonalWallet_Reader.PersonalWallet_Reader("personal", wallet_file_path)


def create_exchange_reader(exchange_name, reader_cls, *args):
    try:
        return reader_cls(*args)
    except Exception as e:
        print(f"[{exchange_name}] reader/client 생성 실패, skip: {e}")
        return None


def is_enabled(env_name, default=False):
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def start_time_service():
    print("[*] Windows Time service status check...")
    out, err, _ = run_cmd("sc query w32time")

    if "RUNNING" in out:
        print("[+] Windows Time service is already running.")
        return True

    print("[*] Windows Time service is not running. Trying to start...")
    out, err, code = run_cmd("net start w32time")

    if code == 0 and "started successfully" in out.lower():
        print("[+] Windows Time service started.")
        return True
    if "already been started" in out:
        print("[+] Windows Time service is already started.")
        return True

    print(f"[!] Failed to start Windows Time service: {err or out}")
    return False


def sync_time():
    print("[*] Running time sync...")
    out, err, code = run_cmd("w32tm /resync")
    if code == 0:
        message = out or "w32tm /resync succeeded."
        print(f"[+] Time sync success: {message}")
        return True, message
    else:
        message = err or out or "w32tm /resync failed."
        print(f"[!] Time sync failed: {message}")
        return False, message


def run_time_sync():
    status = {
        "service_ready": False,
        "resync_ok": False,
        "message": "",
    }

    if start_time_service():
        status["service_ready"] = True
        time.sleep(1)
        ok, message = sync_time()
        status["resync_ok"] = ok
        status["message"] = message
    else:
        status["message"] = "Windows Time service is not running."

    return status


def main(output_format="excel", excel_path="assets.xlsx", html_path="assets.html"):
    time_sync_status = run_time_sync()
    if os.environ["MOBILE"] == "0":
        binance_reader = create_exchange_reader(
            "binance",
            Binance_Reader.Binance_Reader,
            "binance",
            os.getenv("BINANCE_API_KEY"),
            os.getenv("BINANCE_SECRET_KEY"),
        )
        bithumb_reader = create_exchange_reader(
            "bithumb",
            Bithumb_Reader.Bithumb_Reader,
            "bithumb",
            os.getenv("BITHUMB_API_KEY"),
            os.getenv("BITHUMB_SECRET_KEY"),
        )
        if is_enabled("GATEIO1_ENABLED", default=False):
            gateio1_reader = create_exchange_reader(
                "gateio1",
                Gateio_Reader.Gateio_Reader,
                "gateio1",
                os.getenv("GATEIO_API_KEY"),
                os.getenv("GATEIO_SECRET_KEY"),
            )
        else:
            print("[gateio1] disabled by GATEIO1_ENABLED, skip reader creation.")
            gateio1_reader = None
        gateio2_reader = create_exchange_reader(
            "gateio2",
            Gateio_Reader.Gateio_Reader,
            "gateio2",
            os.getenv("GATEIO_API_KEY_2ND"),
            os.getenv("GATEIO_SECRET_KEY_2ND"),
        )
        CW = CoinWallet.CoinWallet(
            binance_reader=binance_reader,
            bithumb_reader=bithumb_reader,
            gateio1_reader=gateio1_reader,
            gateio2_reader=gateio2_reader,
            personal_reader=create_personal_wallet_reader(),
        )
    else:
        binance_reader = create_exchange_reader(
            "binance_mobile",
            Binance_Reader.Binance_Reader,
            "binance_mobile",
            os.getenv("BINANCE_API_KEY_MOBILE"),
            os.getenv("BINANCE_SECRET_KEY_MOBILE"),
        )
        bithumb_reader = create_exchange_reader(
            "bithumb_mobile",
            Bithumb_Reader.Bithumb_Reader,
            "bithumb_mobile",
            os.getenv("BITHUMB_API_KEY_V1"),
            os.getenv("BITHUMB_SECRET_KEY_V1"),
        )
        if is_enabled("GATEIO1_ENABLED", default=False):
            gateio1_reader = create_exchange_reader(
                "gateio1_mobile",
                Gateio_Reader.Gateio_Reader,
                "gateio1_mobile",
                os.getenv("GATEIO_API_KEY"),
                os.getenv("GATEIO_SECRET_KEY"),
            )
        else:
            print("[gateio1_mobile] disabled by GATEIO1_ENABLED, skip reader creation.")
            gateio1_reader = None
        gateio2_reader = create_exchange_reader(
            "gateio2_mobile",
            Gateio_Reader.Gateio_Reader,
            "gateio2_mobile",
            os.getenv("GATEIO_API_KEY_2ND"),
            os.getenv("GATEIO_SECRET_KEY_2ND"),
        )
        CW = CoinWallet.CoinWallet(
            binance_reader=binance_reader,
            bithumb_reader=bithumb_reader,
            gateio1_reader=gateio1_reader,
            gateio2_reader=gateio2_reader,
            personal_reader=create_personal_wallet_reader(),
        )

    CW.time_sync_status = time_sync_status

    exchange_assets = {}
    for reader_name, reader in CW.readers.items():
        if reader is None:
            continue
        print(f"Loading assets from {reader_name}...")
        try:
            if reader_name == "binance":
                assets = load_binance_assets_with_breakdown(reader, CW)
            else:
                assets = reader.load_assets()
        except Exception as e:
            print(f"[{reader_name}] 자산 로딩 실패, skip: {e}")
            continue
        temp_assets = CW.get_temporary_assets_dict(reader_name)
        if temp_assets:
            assets = merge_coinasset_dicts(assets, temp_assets)
        exchange_assets[reader_name] = assets
        CW.assets = merge_coinasset_dicts(CW.assets, assets)

    CW.exchange_assets = exchange_assets

    print("All assets loaded and merged successfully.")
    print("CoinWallet initialized with readers:", CW.readers.keys())
    print_exchange_asset_details(exchange_assets)

    for asset in CW.assets.values():
        CW.Total_Assets_value += asset.usdt_value
        if asset.IsStable:
            CW.Stable_Assets_value += asset.usdt_value

    calculate_ratios(CW)

    bithumb_reader = CW.readers.get("bithumb")
    if bithumb_reader is not None:
        try:
            CW.KRW_deposits = bithumb_reader.get_KRW_deposits()
            CW.KRW_withdrawals, CW.KRW_fees = bithumb_reader.get_KRW_withdrawals()
            CW.CurrentKRWUSDT = bithumb_reader.get_KRW_Currency("USDT")
            CW.Benefit_Ratio = calculate_benefit_ratio(CW)
        except Exception as e:
            print(f"[bithumb] KRW 입출금/수수료 조회 실패, skip: {e}")
    else:
        print("[bithumb] reader가 없어 KRW 입출금/수수료 조회를 skip합니다.")

    print(f"Total assets value: {CW.Total_Assets_value:.2f} USDT")
    print(f"Total stable assets value: {CW.Stable_Assets_value:.2f} USDT")
    stable_ratio = CW.Stable_Assets_value / CW.Total_Assets_value * 100 if CW.Total_Assets_value else 0.0
    print(f"Stable Coin Ratio: {stable_ratio:.2f}%")
    print(f"KRWUSDT current rate: {CW.CurrentKRWUSDT:.5f}")
    print(f"Benefit Ratio: {CW.Benefit_Ratio:.2f}%")

    if output_format in ("excel", "both"):
        CW.export_assets_to_excel(excel_path)
    if output_format in ("html", "both"):
        export_assets_to_html(CW, html_path)
    print(f"Data Type of assets: {type(CW.assets)}")
    print("참고: 717702자산은 별도로 유지해두었습니다.")
    return CW


def merge_coinasset_dicts(dict1, dict2):
    result = {symbol: copy.deepcopy(asset) for symbol, asset in dict1.items()}
    for symbol, asset in dict2.items():
        if symbol in result:
            result[symbol].amount += asset.amount
            result[symbol].usdt_value += asset.usdt_value
        else:
            result[symbol] = copy.deepcopy(asset)
    return result


def print_exchange_asset_details(exchange_assets):
    print("\n=== Exchange Asset Details (Amount / USDT Value) ===")
    for exchange_name, assets in exchange_assets.items():
        print(f"\n[{exchange_name}]")
        if not assets:
            print("  (no assets)")
            continue

        total_usdt = 0.0
        sorted_assets = sorted(
            assets.values(),
            key=lambda a: a.usdt_value,
            reverse=True,
        )
        for asset in sorted_assets:
            if asset.amount == 0 and asset.usdt_value == 0:
                continue
            print(f"  {asset.symbol:12} amount={asset.amount:.8f} | usdt={asset.usdt_value:.4f}")
            total_usdt += asset.usdt_value
        print(f"  Total ({exchange_name}): {total_usdt:.4f} USDT")


def load_binance_assets_with_breakdown(binance_reader, coin_wallet):
    spot_assets = binance_reader.get_spot_balance()
    earn_assets = binance_reader.get_earn_balance()
    temp_assets = coin_wallet.get_temporary_assets_dict("binance")

    print_binance_asset_sources(spot_assets, earn_assets, temp_assets)

    return merge_coinasset_dicts(spot_assets, earn_assets)


def print_binance_asset_sources(spot_assets, earn_assets, temp_assets):
    print("\n=== Binance Asset Source Breakdown ===")
    print_asset_source_section("binance/spot", spot_assets)
    print_asset_source_section("binance/earn", earn_assets)
    print_asset_source_section("binance/temporary", temp_assets)

    combined = {}
    for source_name, source_assets in [
        ("spot", spot_assets),
        ("earn", earn_assets),
        ("temporary", temp_assets),
    ]:
        for symbol, asset in source_assets.items():
            if symbol not in combined:
                combined[symbol] = []
            combined[symbol].append((source_name, asset.amount, asset.usdt_value))

    print("\n[binance/combined by symbol]")
    for symbol in sorted(combined.keys()):
        details = combined[symbol]
        total_amount = sum(item[1] for item in details)
        total_usdt = sum(item[2] for item in details)
        source_parts = ", ".join(
            f"{src}:amount={amt:.8f}/usdt={val:.4f}" for src, amt, val in details
        )
        print(
            f"  {symbol:12} total_amount={total_amount:.8f} | total_usdt={total_usdt:.4f} | {source_parts}"
        )


def print_asset_source_section(section_name, assets):
    print(f"\n[{section_name}]")
    if not assets:
        print("  (no assets)")
        return
    total_usdt = 0.0
    for asset in sorted(assets.values(), key=lambda a: a.usdt_value, reverse=True):
        if asset.amount == 0 and asset.usdt_value == 0:
            continue
        print(f"  {asset.symbol:12} amount={asset.amount:.8f} | usdt={asset.usdt_value:.4f}")
        total_usdt += asset.usdt_value
    print(f"  Total ({section_name}): {total_usdt:.4f} USDT")


def calculate_benefit_ratio(cw):
    current_krw_balance = cw.KRW_deposits - cw.KRW_withdrawals - cw.KRW_fees
    if current_krw_balance == 0:
        return 0.0
    return ((cw.Total_Assets_value * cw.CurrentKRWUSDT) - current_krw_balance) / current_krw_balance * 100


def export_assets_to_html(cw, filename="assets.html"):
    sorted_assets = sorted(cw.assets.values(), key=lambda a: a.ratio_clustered, reverse=True)
    rows = []
    for asset in sorted_assets:
        rows.append(
            f"<tr><td>{asset.symbol}</td><td>{asset.amount:.8f}</td><td>{asset.usdt_price:,.5f}</td><td>{asset.usdt_value:,.3f}</td><td>{asset.ratio:.2f}%</td><td>{asset.ratio_nonstable:.2f}%</td><td>{asset.ratio_clustered:.2f}%</td><td>{asset.ratio_clustered_nonstable:.2f}%</td></tr>"
        )
    rows_html = "\n".join(rows)
    stable_ratio = (cw.Stable_Assets_value / cw.Total_Assets_value * 100) if cw.Total_Assets_value else 0.0
    current_krw_balance = cw.KRW_deposits - cw.KRW_withdrawals - cw.KRW_fees
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Crypto Asset Report</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background: #f5f7fb; color: #1a1a1a; }}
    .card {{ background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }}
    .k {{ font-size: 12px; color: #666; }}
    .v {{ font-size: 18px; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 10px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid #e9edf5; padding: 9px 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #eef3ff; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Crypto Asset Report</h1>
    <div>Generated at: {generated_at}</div>
  </div>
  <div class="card grid">
    <div><div class="k">Total Assets (USDT)</div><div class="v">{cw.Total_Assets_value:,.3f}</div></div>
    <div><div class="k">Stable Assets (USDT)</div><div class="v">{cw.Stable_Assets_value:,.3f}</div></div>
    <div><div class="k">Stable Ratio</div><div class="v">{stable_ratio:.2f}%</div></div>
    <div><div class="k">KRW-USDT Rate</div><div class="v">{cw.CurrentKRWUSDT:,.5f}</div></div>
    <div><div class="k">KRW Deposits</div><div class="v">{cw.KRW_deposits:,.0f}</div></div>
    <div><div class="k">KRW Withdrawals</div><div class="v">{cw.KRW_withdrawals:,.0f}</div></div>
    <div><div class="k">KRW Fees</div><div class="v">{cw.KRW_fees:,.0f}</div></div>
    <div><div class="k">KRW Principal</div><div class="v">{current_krw_balance:,.0f}</div></div>
    <div><div class="k">Benefit Ratio</div><div class="v">{cw.Benefit_Ratio:.2f}%</div></div>
  </div>
  <table>
    <thead>
      <tr><th>Symbol</th><th>Amount</th><th>USDT Price</th><th>USDT Value</th><th>Ratio</th><th>Non-Stable</th><th>Clustered</th><th>Clustered Non-Stable</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Exported assets to {filename}")


def get_stable_asset_list(coin_wallet_assets):
    stable_assets = []
    for asset in coin_wallet_assets.values():
        if asset.symbol in STABLE_ASSET:
            if hasattr(asset, "MainCoin") and asset.MainCoin == asset.symbol:
                stable_assets.insert(0, asset)
            else:
                stable_assets.append(asset)
    return stable_assets


def calculate_ratios(CW):
    if CW.Total_Assets_value == 0:
        return

    nonstable_assets_value = CW.Total_Assets_value - CW.Stable_Assets_value
    for coinasset in CW.assets.values():
        coinasset.ratio = coinasset.usdt_value / CW.Total_Assets_value * 100
        if coinasset.IsStable:
            coinasset.ratio_nonstable = 0.0
        else:
            coinasset.ratio_nonstable = coinasset.usdt_value / nonstable_assets_value * 100 if nonstable_assets_value else 0.0

        if coinasset.NeedCluster:
            if coinasset.MainCoin == coinasset.symbol:
                clustered_assets = [asset for asset in CW.assets.values() if asset.symbol in coinasset.Cluster]
                total_clustered_value = sum(asset.usdt_value for asset in clustered_assets)
                coinasset.ratio_clustered = total_clustered_value / CW.Total_Assets_value * 100
                if not coinasset.IsStable:
                    coinasset.ratio_clustered_nonstable = total_clustered_value / nonstable_assets_value * 100 if nonstable_assets_value else 0.0
                else:
                    coinasset.ratio_clustered_nonstable = 0.0
            else:
                coinasset.ratio_clustered = 0.0
                coinasset.ratio_clustered_nonstable = 0.0
        else:
            coinasset.ratio_clustered = coinasset.ratio
            coinasset.ratio_clustered_nonstable = coinasset.ratio_nonstable


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-format", choices=["excel", "html", "both"], default="excel")
    parser.add_argument("--excel-path", default="assets.xlsx")
    parser.add_argument("--html-path", default="assets.html")
    args = parser.parse_args()
    main(output_format=args.output_format, excel_path=args.excel_path, html_path=args.html_path)

