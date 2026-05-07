import argparse
import csv
import os
import sys

from dotenv import load_dotenv

import HistoryManager
import main
from CoinAsset import STABLE_ASSET
from CoinAsset import CoinAsset


def merge_trade_metrics(target_assets, source_assets):
    for symbol, source in source_assets.items():
        if symbol not in target_assets:
            target_assets[symbol] = CoinAsset(symbol, 0.0, source.usdt_price)
        target = target_assets[symbol]
        target.total_buy_qty += source.total_buy_qty
        target.total_buy_cost += source.total_buy_cost
        target.total_sell_qty += source.total_sell_qty
        target.total_sell_income += source.total_sell_income
        target.total_qty += source.total_qty
        target.total_cost += source.total_cost
        for fee_symbol, fee_amount in source.fee.items():
            target.fee[fee_symbol] = target.fee.get(fee_symbol, 0.0) + fee_amount


def finalize_trade_metrics(trade_assets):
    for asset in trade_assets.values():
        asset.get_avg_price()


def clone_current_assets(asset_dict):
    cloned = {}
    for symbol, asset in asset_dict.items():
        cloned[symbol] = CoinAsset(symbol, asset.amount, asset.usdt_price)
    return cloned


def accumulate_cached_history(reader, assets, symbol=None):
    history_files = HistoryManager.list_json_files("./history", reader.name)
    for asset_symbol in list(assets.keys()):
        if asset_symbol in STABLE_ASSET:
            continue
        if symbol and asset_symbol != symbol:
            continue

        for stable_symbol in STABLE_ASSET:
            if stable_symbol == "KRW":
                continue
            if "bithumb" in reader.name and stable_symbol != "USDT":
                continue
            if stable_symbol == "FDUSD" and "binance" not in reader.name:
                continue

            filename = f"{reader.name}_trades_{asset_symbol}{stable_symbol}.json"
            if filename not in history_files:
                continue

            currency_pair = asset_symbol + stable_symbol
            trades = HistoryManager.load_trades_from_file(currency_pair, filename)
            trades = [
                trade for trade in trades
                if trade.get(reader.id_indicator) != "DUMMY"
            ]
            if trades:
                reader.accumulate_trade_history(trades, assets, asset_symbol)


def populate_trade_history(cw, symbols=None, fetch=True):
    symbols = {item.upper() for item in symbols} if symbols else None
    trade_assets = {}
    for reader_name, reader in cw.readers.items():
        if reader is None or reader_name == "personal":
            continue

        exchange_assets = getattr(cw, "exchange_assets", {}).get(reader_name, {})
        if not exchange_assets:
            continue

        scoped_assets = clone_current_assets(exchange_assets)
        for asset_symbol in list(scoped_assets.keys()):
            if symbols and asset_symbol not in symbols:
                scoped_assets.pop(asset_symbol)

        if not scoped_assets:
            continue

        for asset_symbol in sorted(scoped_assets.keys()):
            if asset_symbol in STABLE_ASSET:
                continue

            if fetch:
                print(f"[{reader_name}] loading trade history for {asset_symbol}...")
                reader.get_trade_history(scoped_assets, asset_symbol)
            else:
                print(f"[{reader_name}] loading cached trade history for {asset_symbol} only...")
                accumulate_cached_history(reader, scoped_assets, asset_symbol)
        merge_trade_metrics(trade_assets, scoped_assets)
    finalize_trade_metrics(trade_assets)
    return trade_assets


def build_roi_rows(cw, trade_assets, symbols=None):
    symbols = {item.upper() for item in symbols} if symbols else None
    rows = []
    for asset in sorted(cw.assets.values(), key=lambda item: item.usdt_value, reverse=True):
        if symbols and asset.symbol not in symbols:
            continue

        trade_asset = trade_assets.get(asset.symbol)
        buy_cost = trade_asset.total_buy_cost if trade_asset else 0.0
        sell_income = trade_asset.total_sell_income if trade_asset else 0.0
        total_pnl = asset.usdt_value + sell_income - buy_cost
        roi = (total_pnl / buy_cost * 100) if buy_cost > 0 else None
        cost_basis_remaining = buy_cost - sell_income
        unrealized_pnl = asset.usdt_value - cost_basis_remaining

        rows.append({
            "symbol": asset.symbol,
            "current_amount": asset.amount,
            "current_value_usdt": asset.usdt_value,
            "buy_qty": trade_asset.total_buy_qty if trade_asset else 0.0,
            "buy_cost_usdt": buy_cost,
            "sell_qty": trade_asset.total_sell_qty if trade_asset else 0.0,
            "sell_income_usdt": sell_income,
            "cost_basis_remaining_usdt": cost_basis_remaining if buy_cost > 0 else None,
            "unrealized_pnl_usdt": unrealized_pnl if buy_cost > 0 else None,
            "total_pnl_usdt": total_pnl if buy_cost > 0 else None,
            "roi_percent": roi,
            "status": "OK" if buy_cost > 0 else "NO_TRADE_COST",
        })
    return rows


def format_optional(value, digits=3):
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}"


def print_roi_rows(rows):
    print("\n=== Coin ROI Report ===")
    print(
        "Symbol       Current USDT     Buy Cost     Sell Income     Total PnL     ROI %       Status"
    )
    for row in rows:
        print(
            f"{row['symbol']:12}"
            f"{format_optional(row['current_value_usdt']):>14}"
            f"{format_optional(row['buy_cost_usdt']):>13}"
            f"{format_optional(row['sell_income_usdt']):>16}"
            f"{format_optional(row['total_pnl_usdt']):>14}"
            f"{format_optional(row['roi_percent'], 2):>10}"
            f"  {row['status']}"
        )


def write_csv(rows, output_path):
    fieldnames = [
        "symbol",
        "current_amount",
        "current_value_usdt",
        "buy_qty",
        "buy_cost_usdt",
        "sell_qty",
        "sell_income_usdt",
        "cost_basis_remaining_usdt",
        "unrealized_pnl_usdt",
        "total_pnl_usdt",
        "roi_percent",
        "status",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported ROI report to {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate ROI report for currently held coins.")
    parser.add_argument(
        "--symbol",
        action="append",
        help="Optional held symbol to report. Repeat for multiple symbols, for example --symbol BTC --symbol ETH.",
    )
    parser.add_argument("--output", default="roi_report.csv", help="CSV output path.")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Use cached history files only, without requesting new exchange trade history.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Generate ROI even if one or more exchange readers failed to load.",
    )
    return parser.parse_args()


def main_cli():
    args = parse_args()
    os.environ["MOBILE"] = os.getenv("MOBILE", "0")
    load_dotenv()

    cw = main.main(output_format="none")
    failed_readers = getattr(cw, "failed_readers", [])
    if failed_readers and not args.allow_partial:
        print("ROI report aborted because one or more exchange readers failed:")
        for failure in failed_readers:
            print(f"- {failure}")
        print("Fix the exchange loading failure first, or use --allow-partial intentionally.")
        return 1

    held_symbols = {
        asset.symbol
        for asset in cw.assets.values()
        if asset.amount > 0 and asset.symbol not in STABLE_ASSET
    }
    if args.symbol:
        requested_symbols = {item.upper() for item in args.symbol}
        report_symbols = held_symbols & requested_symbols
        missing_symbols = sorted(requested_symbols - held_symbols)
        if missing_symbols:
            print(f"Skip non-held symbols: {', '.join(missing_symbols)}")
    else:
        report_symbols = held_symbols

    trade_assets = populate_trade_history(cw, symbols=report_symbols, fetch=not args.skip_fetch)
    rows = build_roi_rows(cw, trade_assets, symbols=report_symbols)
    print_roi_rows(rows)
    write_csv(rows, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
