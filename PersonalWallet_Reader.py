import json
import os
import requests
from Reader import Reader


class PersonalWallet_Reader(Reader):
    def __init__(self, name, wallet_file_path):
        super().__init__(name, "", "")
        self.wallet_file_path = wallet_file_path
        self.price_cache = {"USDT": 1.0, "USDC": 1.0, "FDUSD": 1.0}
        self.coingecko_id_cache = {}
        self.coingecko_symbol_map = {
            "JITOSOL": "jito-staked-sol",
            "SLISBNB": "synclub-staked-bnb",
        }

    def load_assets(self):
        return self.get_spot_balance()

    def get_spot_balance(self, input_symbol=None):
        asset_dict = {}
        if not os.path.exists(self.wallet_file_path):
            print(f"[{self.name}] wallet file not found: {self.wallet_file_path}")
            return asset_dict

        with open(self.wallet_file_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        assets = payload.get("assets", [])
        for item in assets:
            symbol = str(item.get("symbol", "")).upper().strip()
            if not symbol:
                continue
            if input_symbol and symbol != input_symbol:
                continue

            amount = float(item.get("amount", 0))
            usdt_price = self.get_usdt_price(symbol)
            if amount <= 0 or usdt_price is None or usdt_price <= 0:
                print(f"[{self.name}] skip {symbol}: invalid amount or no price")
                continue

            self.add_CoinAsset_to_dict(asset_dict, symbol, amount, usdt_price)

        return asset_dict

    def get_earn_balance(self, input_symbol=None):
        return {}

    def get_usdt_price(self, symbol):
        normalized_symbol = str(symbol).upper().strip()
        if normalized_symbol in self.price_cache:
            return self.price_cache[normalized_symbol]

        price = self._get_binance_public_price(normalized_symbol)
        if price is None:
            price = self._get_gate_public_price(normalized_symbol)
        if price is None:
            price = self._get_coingecko_usd_price(normalized_symbol)

        if price is not None:
            self.price_cache[normalized_symbol] = price
        return price

    def _get_binance_public_price(self, symbol):
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            response = requests.get(url, params={"symbol": f"{symbol}USDT"}, timeout=10)
            response.raise_for_status()
            payload = response.json()
            return float(payload["price"])
        except Exception:
            return None

    def _get_gate_public_price(self, symbol):
        try:
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            response = requests.get(url, params={"currency_pair": f"{symbol}_USDT"}, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and payload:
                return float(payload[0]["last"])
        except Exception:
            return None
        return None

    def _get_coingecko_usd_price(self, symbol):
        coin_id = self.coingecko_symbol_map.get(symbol) or self._search_coingecko_coin_id(symbol)
        if not coin_id:
            return None

        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            response = requests.get(url, params={"ids": coin_id, "vs_currencies": "usd"}, timeout=10)
            response.raise_for_status()
            payload = response.json()
            usd_price = payload.get(coin_id, {}).get("usd")
            if usd_price is None:
                return None
            return float(usd_price)
        except Exception:
            return None

    def _search_coingecko_coin_id(self, symbol):
        if symbol in self.coingecko_id_cache:
            return self.coingecko_id_cache[symbol]

        try:
            url = "https://api.coingecko.com/api/v3/search"
            response = requests.get(url, params={"query": symbol}, timeout=10)
            response.raise_for_status()
            payload = response.json()
            for coin in payload.get("coins", []):
                if str(coin.get("symbol", "")).upper() == symbol:
                    coin_id = coin.get("id")
                    if coin_id:
                        self.coingecko_id_cache[symbol] = coin_id
                        return coin_id
        except Exception:
            return None
        return None

    def get_trade_history_from_reader(self, currency_pair, last_time):
        return [], last_time

    def get_trade_history_from_dual_investment(self, Assetlist, input_symbol=None):
        return

    def get_trade_history_from_auto_invest(self, Assetlist, input_symbol=None):
        return
