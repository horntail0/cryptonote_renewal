import json
import os
import requests
from Reader import Reader


DEFAULT_EVM_CHAINS = {
    "ethereum": {
        "rpc_url": "https://ethereum.publicnode.com",
        "native_symbol": "ETH",
    },
    "bsc": {
        "rpc_url": "https://bsc-dataseed.binance.org",
        "native_symbol": "BNB",
    },
    "polygon": {
        "rpc_url": "https://polygon-bor.publicnode.com",
        "native_symbol": "MATIC",
    },
    "arbitrum": {
        "rpc_url": "https://arbitrum-one.publicnode.com",
        "native_symbol": "ETH",
    },
    "base": {
        "rpc_url": "https://base.publicnode.com",
        "native_symbol": "ETH",
    },
}

BINANCE_WEB3_CHAIN_IDS = {
    "bsc": "56",
    "bnb": "56",
    "bnbchain": "56",
    "base": "8453",
    "solana": "CT_501",
    "sol": "CT_501",
}

BINANCE_WEB3_ADDRESS_POSITIONS_URL = (
    "https://web3.binance.com/bapi/defi/v3/public/"
    "wallet-direct/buw/wallet/address/pnl/active-position-list/ai"
)

BINANCE_WEB3_HEADERS = {
    "clienttype": "web",
    "clientversion": "1.2.0",
    "Accept-Encoding": "identity",
    "User-Agent": "binance-web3/1.1 (Skill)",
}

BITCOIN_EXPLORER_BASE_URL = "https://blockstream.info/api"
ETHPLORER_BASE_URL = "https://api.ethplorer.io"
ETHPLORER_DEFAULT_API_KEY = "freekey"


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
        payload = self._load_wallet_payload()
        if payload is None:
            return asset_dict

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

        web3_assets = self._load_web3_wallet_assets(payload, input_symbol)
        self._merge_asset_dicts(asset_dict, web3_assets)
        return asset_dict

    def get_earn_balance(self, input_symbol=None):
        return {}

    def _load_wallet_payload(self):
        if not os.path.exists(self.wallet_file_path):
            print(f"[{self.name}] wallet file not found: {self.wallet_file_path}")
            return None

        with open(self.wallet_file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _load_web3_wallet_assets(self, payload, input_symbol=None):
        asset_dict = {}
        wallets = payload.get("web3_wallets", [])
        if not wallets:
            return asset_dict

        for wallet in wallets:
            if not wallet.get("enabled", True):
                continue

            chain_name = str(wallet.get("chain", "")).lower().strip()
            address = str(wallet.get("address", "")).strip()
            if not address:
                print(f"[{self.name}] skip web3 wallet: invalid address")
                continue

            if self._is_binance_web3_wallet(wallet):
                self._add_binance_web3_assets(asset_dict, wallet, input_symbol)
                continue

            if self._is_bitcoin_wallet(wallet):
                self._add_bitcoin_assets(asset_dict, wallet, input_symbol)
                continue

            if self._is_ethereum_explorer_wallet(wallet):
                self._add_ethereum_explorer_assets(asset_dict, wallet, input_symbol)
                continue

            chain_config = self._get_evm_chain_config(chain_name, wallet)
            if not chain_config:
                print(f"[{self.name}] skip web3 wallet: invalid chain or address")
                continue

            self._add_native_evm_asset(asset_dict, wallet, chain_config, input_symbol)
            self._add_erc20_assets(asset_dict, wallet, chain_config, input_symbol)

        return asset_dict

    def _is_binance_web3_wallet(self, wallet):
        provider = str(wallet.get("provider") or wallet.get("source") or "").lower().strip()
        return provider in {"binance_web3", "binance"}

    def _is_bitcoin_wallet(self, wallet):
        provider = str(wallet.get("provider") or wallet.get("source") or "").lower().strip()
        chain = str(wallet.get("chain", "")).lower().strip()
        return provider in {"bitcoin_explorer", "bitcoin"} or chain in {"bitcoin", "btc"}

    def _is_ethereum_explorer_wallet(self, wallet):
        provider = str(wallet.get("provider") or wallet.get("source") or "").lower().strip()
        return provider in {"ethereum_explorer", "ethplorer"}

    def _add_bitcoin_assets(self, asset_dict, wallet, input_symbol=None):
        if input_symbol and input_symbol != "BTC":
            return

        address = str(wallet.get("address", "")).strip()
        if not self._is_supported_bitcoin_address(address):
            print(f"[{self.name}] skip BTC wallet: unsupported Bitcoin address")
            return

        amount = self._get_bitcoin_address_balance(address, wallet)
        if amount is None:
            return

        self._add_priced_asset(asset_dict, "BTC", amount)

    def _is_supported_bitcoin_address(self, address):
        normalized = str(address).strip().lower()
        return normalized.startswith("bc1") or normalized.startswith("3")

    def _get_bitcoin_address_balance(self, address, wallet):
        base_url = (
            wallet.get("api_url")
            or os.getenv("BITCOIN_EXPLORER_API_URL")
            or BITCOIN_EXPLORER_BASE_URL
        ).rstrip("/")
        try:
            response = requests.get(f"{base_url}/address/{address}", timeout=15)
            response.raise_for_status()
            payload = response.json()
            chain_stats = payload.get("chain_stats", {})
            mempool_stats = payload.get("mempool_stats", {})
            funded = int(chain_stats.get("funded_txo_sum", 0)) + int(mempool_stats.get("funded_txo_sum", 0))
            spent = int(chain_stats.get("spent_txo_sum", 0)) + int(mempool_stats.get("spent_txo_sum", 0))
            return (funded - spent) / 100_000_000
        except Exception as e:
            print(f"[{self.name}] Bitcoin balance request failed: {e}")
            return None

    def _add_ethereum_explorer_assets(self, asset_dict, wallet, input_symbol=None):
        address = str(wallet.get("address", "")).strip()
        if not address.startswith(("0x", "0X")):
            print(f"[{self.name}] skip Ethereum wallet: invalid address")
            return

        payload = self._get_ethplorer_address_info(address, wallet)
        if not payload:
            return

        self._add_ethplorer_eth_asset(asset_dict, payload, input_symbol)
        self._add_ethplorer_token_assets(asset_dict, payload, input_symbol)

    def _get_ethplorer_address_info(self, address, wallet):
        base_url = (
            wallet.get("api_url")
            or os.getenv("ETHEREUM_EXPLORER_API_URL")
            or ETHPLORER_BASE_URL
        ).rstrip("/")
        api_key = (
            wallet.get("api_key")
            or os.getenv("ETHPLORER_API_KEY")
            or ETHPLORER_DEFAULT_API_KEY
        )
        try:
            response = requests.get(
                f"{base_url}/getAddressInfo/{address}",
                params={"apiKey": api_key},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                print(f"[{self.name}] Ethplorer API error: {payload}")
                return None
            return payload
        except Exception as e:
            print(f"[{self.name}] Ethereum explorer request failed: {e}")
            return None

    def _add_ethplorer_eth_asset(self, asset_dict, payload, input_symbol=None):
        if input_symbol and input_symbol != "ETH":
            return

        eth_info = payload.get("ETH") or {}
        amount = self._parse_optional_float(eth_info.get("balance"))
        if amount is None:
            return

        price = self._parse_optional_float((eth_info.get("price") or {}).get("rate"))
        if price is None or price <= 0:
            price = self.get_usdt_price("ETH")

        if amount <= 0 or price is None or price <= 0:
            return
        self.add_CoinAsset_to_dict(asset_dict, "ETH", amount, price)

    def _add_ethplorer_token_assets(self, asset_dict, payload, input_symbol=None):
        for token in payload.get("tokens", []) or []:
            token_info = token.get("tokenInfo") or {}
            symbol = str(token_info.get("symbol", "")).upper().strip()
            if not symbol:
                continue
            if input_symbol and symbol != input_symbol:
                continue

            amount = self._parse_ethplorer_token_amount(token, token_info)
            if amount is None or amount <= 0:
                continue

            price = self._parse_optional_float((token_info.get("price") or {}).get("rate"))
            if price is None or price <= 0:
                price = self.get_usdt_price(symbol)
            if price is None or price <= 0:
                print(f"[{self.name}] skip {symbol}: no price")
                continue

            self.add_CoinAsset_to_dict(asset_dict, symbol, amount, price)

    def _parse_ethplorer_token_amount(self, token, token_info):
        balance = self._parse_optional_float(token.get("balance"))
        if balance is None:
            return None

        decimals = token_info.get("decimals")
        try:
            decimals = int(decimals)
        except (TypeError, ValueError):
            decimals = 0

        return balance / 10**decimals

    def _get_evm_chain_config(self, chain_name, wallet):
        chain_config = dict(DEFAULT_EVM_CHAINS.get(chain_name, {}))
        rpc_url = wallet.get("rpc_url") or os.getenv(f"WEB3_{chain_name.upper()}_RPC_URL")
        if rpc_url:
            chain_config["rpc_url"] = rpc_url
        if wallet.get("native_symbol"):
            chain_config["native_symbol"] = wallet["native_symbol"]
        return chain_config

    def _add_binance_web3_assets(self, asset_dict, wallet, input_symbol=None):
        chain_id = self._get_binance_web3_chain_id(wallet)
        address = str(wallet.get("address", "")).strip()
        if not chain_id or not address:
            print(f"[{self.name}] skip Binance Web3 wallet: unsupported chain or address")
            return

        for position in self._fetch_binance_web3_positions(address, chain_id):
            symbol = str(position.get("symbol", "")).upper().strip()
            if not symbol:
                continue
            if input_symbol and symbol != input_symbol:
                continue

            try:
                amount = float(position.get("remainQty", 0) or 0)
            except (TypeError, ValueError):
                continue

            price = self._parse_optional_float(position.get("price"))
            if price is None or price <= 0:
                price = self.get_usdt_price(symbol)

            if amount <= 0 or price is None or price <= 0:
                print(f"[{self.name}] skip {symbol}: invalid amount or no price")
                continue

            self.add_CoinAsset_to_dict(asset_dict, symbol, amount, price)

    def _get_binance_web3_chain_id(self, wallet):
        if wallet.get("chain_id"):
            return str(wallet["chain_id"]).strip()

        chain_name = str(wallet.get("chain", "")).lower().replace("-", "").replace("_", "").strip()
        return BINANCE_WEB3_CHAIN_IDS.get(chain_name)

    def _fetch_binance_web3_positions(self, address, chain_id):
        positions = []
        seen_keys = set()
        offset = 0
        max_pages = 20

        for _ in range(max_pages):
            payload = self._request_binance_web3_positions(address, chain_id, offset)
            if not payload:
                break

            page_items = payload.get("list") or []
            if not page_items:
                break

            new_items = []
            for item in page_items:
                position_key = self._binance_web3_position_key(item)
                if position_key in seen_keys:
                    continue
                seen_keys.add(position_key)
                new_items.append(item)

            if not new_items:
                break

            positions.extend(new_items)
            next_offset = payload.get("offset")
            if next_offset is None:
                offset += len(page_items)
            else:
                try:
                    next_offset = int(next_offset)
                except (TypeError, ValueError):
                    next_offset = offset + len(page_items)

                if next_offset <= offset:
                    offset += len(page_items)
                else:
                    offset = next_offset

        return positions

    def _binance_web3_position_key(self, position):
        chain_id = str(position.get("chainId", "")).strip()
        contract = str(position.get("contractAddress", "")).lower().strip()
        symbol = str(position.get("symbol", "")).upper().strip()
        name = str(position.get("name", "")).lower().strip()

        if contract:
            return chain_id, contract
        return chain_id, symbol, name

    def _request_binance_web3_positions(self, address, chain_id, offset):
        try:
            response = requests.get(
                BINANCE_WEB3_ADDRESS_POSITIONS_URL,
                params={
                    "address": address,
                    "chainId": chain_id,
                    "offset": offset,
                },
                headers=BINANCE_WEB3_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != "000000" or not payload.get("success", False):
                print(f"[{self.name}] Binance Web3 API error: {payload}")
                return None
            return payload.get("data") or {}
        except Exception as e:
            print(f"[{self.name}] Binance Web3 request failed: {e}")
            return None

    def _parse_optional_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _add_native_evm_asset(self, asset_dict, wallet, chain_config, input_symbol=None):
        if wallet.get("include_native", True) is False:
            return

        symbol = str(chain_config.get("native_symbol", "")).upper().strip()
        if input_symbol and symbol != input_symbol:
            return

        balance_wei = self._eth_get_balance(chain_config["rpc_url"], wallet["address"])
        if balance_wei is None:
            return

        self._add_priced_asset(asset_dict, symbol, balance_wei / 10**18)

    def _add_erc20_assets(self, asset_dict, wallet, chain_config, input_symbol=None):
        rpc_url = chain_config["rpc_url"]
        wallet_address = wallet["address"]
        for token in wallet.get("tokens", []):
            symbol = str(token.get("symbol", "")).upper().strip()
            contract = str(token.get("contract", "")).strip()
            if not symbol or not contract:
                continue
            if input_symbol and symbol != input_symbol:
                continue

            decimals = token.get("decimals")
            if decimals is None:
                decimals = self._erc20_decimals(rpc_url, contract)
            try:
                decimals = int(decimals)
            except (TypeError, ValueError):
                print(f"[{self.name}] skip {symbol}: invalid decimals")
                continue

            raw_balance = self._erc20_balance_of(rpc_url, contract, wallet_address)
            if raw_balance is None:
                continue

            self._add_priced_asset(asset_dict, symbol, raw_balance / 10**decimals)

    def _add_priced_asset(self, asset_dict, symbol, amount):
        usdt_price = self.get_usdt_price(symbol)
        if amount <= 0 or usdt_price is None or usdt_price <= 0:
            print(f"[{self.name}] skip {symbol}: invalid amount or no price")
            return
        self.add_CoinAsset_to_dict(asset_dict, symbol, amount, usdt_price)

    def _merge_asset_dicts(self, target, source):
        for symbol, asset in source.items():
            if symbol in target:
                target[symbol].amount += asset.amount
                target[symbol].usdt_value += asset.usdt_value
            else:
                target[symbol] = asset

    def _eth_get_balance(self, rpc_url, address):
        result = self._rpc_call(rpc_url, "eth_getBalance", [address, "latest"])
        return self._hex_to_int(result)

    def _erc20_balance_of(self, rpc_url, contract, wallet_address):
        padded_address = self._strip_0x(wallet_address).rjust(64, "0")
        data = "0x70a08231" + padded_address
        result = self._rpc_call(
            rpc_url,
            "eth_call",
            [{"to": contract, "data": data}, "latest"],
        )
        return self._hex_to_int(result)

    def _erc20_decimals(self, rpc_url, contract):
        result = self._rpc_call(
            rpc_url,
            "eth_call",
            [{"to": contract, "data": "0x313ce567"}, "latest"],
        )
        return self._hex_to_int(result)

    def _rpc_call(self, rpc_url, method, params):
        try:
            response = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params,
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                print(f"[{self.name}] rpc error: {payload['error']}")
                return None
            return payload.get("result")
        except Exception as e:
            print(f"[{self.name}] rpc request failed: {e}")
            return None

    def _hex_to_int(self, value):
        if not value:
            return None
        try:
            return int(value, 16)
        except (TypeError, ValueError):
            return None

    def _strip_0x(self, value):
        value = str(value).strip()
        return value[2:] if value.startswith(("0x", "0X")) else value

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
