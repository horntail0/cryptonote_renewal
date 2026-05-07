import argparse
import os

from dotenv import load_dotenv

import Gateio_Reader


def print_asset_summary(assets):
    total_usdt = sum(asset.usdt_value for asset in assets.values())
    print("\n=== Gate.io 2 Asset Summary ===")
    print(f"Total: {total_usdt:.4f} USDT")

    for asset in sorted(assets.values(), key=lambda item: item.usdt_value, reverse=True):
        if asset.amount == 0 and asset.usdt_value == 0:
            continue
        print(f"{asset.symbol:12} amount={asset.amount:.8f} | usdt={asset.usdt_value:.4f}")


def create_gateio2_reader():
    api_key = os.getenv("GATEIO_API_KEY_2ND")
    api_secret = os.getenv("GATEIO_SECRET_KEY_2ND")

    if not api_key or not api_secret:
        raise RuntimeError("GATEIO_API_KEY_2ND/GATEIO_SECRET_KEY_2ND is required.")

    return Gateio_Reader.Gateio_Reader("gateio2", api_key, api_secret)


def main():
    parser = argparse.ArgumentParser(description="Load assets from Gate.io account 2 only.")
    parser.add_argument(
        "--symbol",
        help="Optional asset symbol to load, for example USDT or BTC.",
    )
    args = parser.parse_args()

    os.environ["MOBILE"] = "0"
    load_dotenv()

    reader = create_gateio2_reader()
    print("Loading assets from gateio2 only...")

    if args.symbol:
        assets = reader.load_symbol_assets(args.symbol.upper())
    else:
        assets = reader.load_assets()

    print_asset_summary(assets)
    return assets


if __name__ == "__main__":
    main()
