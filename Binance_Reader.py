from Reader import Reader
from CoinAsset import CoinAsset
from CoinAsset import CLUSTER_ASSET, STABLE_ASSET
from binance.client import Client
import time
import hmac
import hashlib
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
load_dotenv()
class Binance_Reader(Reader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import API KEY
        mobile = int(os.environ.get("MOBILE", "0"))
        self.Temporary_Assets = {}

        self.BASE_URL = "https://api.binance.com"
        # Binance 클라이언트 생성
        self.client = Client(self.API_KEY, self.API_SECRET, requests_params={"timeout": 20})

        # Trade History 관련 필드
        self.id_indicator = 'id'
        self.time_indicator = 'time'
        self.qty_indicator = 'qty'
        self.price_indicator = 'price'
        self.fee_indicator = 'commission'
        self.feeCurrency_indicator = 'commissionAsset'


    def check_buyer(self, trade):
        if trade['isBuyer']:
            return True
        elif trade['isBuyer'] is False:
            return False
        
    def binance_manual_request(self, endpoint, params=None):
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}"

        signature = hmac.new(
            self.API_SECRET.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        url = f"{self.BASE_URL}{endpoint}?{query_string}&signature={signature}"
        headers = {
            "X-MBX-APIKEY": self.API_KEY
        }

        response = requests.get(url, headers=headers)

        try:
            data = response.json()
        except:
            print("JSON 파싱 실패:", response.text)
            return {}

        if response.status_code != 200:
            print("Binance 오류:", data)
            return {}
        return data   

        
    def get_spot_balance(self, input_symbol=None):
        balances = self.client.get_account()['balances']
        dict_spot = {}
        for b in balances:
            if input_symbol and b['asset'] != input_symbol:
                continue
            symbol = b['asset']
            total = float(b['free']) + float(b['locked'])
            if total > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_spot, symbol, total, usdt_price)
        return dict_spot


    def get_earn_balance(self, input_symbol=None):
        flexible_endpoint = "/sapi/v1/simple-earn/flexible/position"
        dual_endpoint = "/sapi/v1/dci/product/positions"
        flexible = self.binance_manual_request(flexible_endpoint)
        dual = self.binance_manual_request(dual_endpoint)

        dict_earn = {}
        # Flexible Earn
        for item in flexible.get('rows', []):
            symbol = item['asset']
            if input_symbol and symbol != input_symbol:
                continue
            amount = float(item['totalAmount'])
            if amount > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_earn, symbol, amount, usdt_price)

        # Dual Investment
        for item in dual['list']:
            if item['purchaseStatus'] != 'PURCHASE_SUCCESS':
                continue
            symbol = item['investCoin']
            if input_symbol and symbol != input_symbol:
                continue
            amount = float(item['subscriptionAmount'])
            if amount > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_earn, symbol, amount, usdt_price)
        for symbol in self.Temporary_Assets:
            if input_symbol and symbol != input_symbol:
                continue
            self.add_CoinAsset_to_dict(dict_earn, symbol, self.Temporary_Assets[symbol].amount, self.Temporary_Assets[symbol].usdt_price)
        
   
        return dict_earn


    def get_trade_history_from_reader(self, currency_pair, last_time):
        start = (datetime.now() - timedelta(days=1000))
        end = datetime.now()
        start_ts = max(int(start.timestamp() * 1000), last_time)
        end_ts = int(end.timestamp() * 1000)

        params = {
            'symbol': currency_pair,
            'startTime': start_ts,
            'limit': 1000
        }

        try:
            trades = self.client.get_my_trades(**params)
        except Exception as e:
            print(f"[Binance] 거래내역 조회 오류: {e}, {currency_pair}, {start_ts}")
            return None, end_ts
        return trades, end_ts
        
    def get_trade_history_from_dual_investment(self, Assetlist, input_symbol=None):
        dual_endpoint = "/sapi/v1/dci/product/positions"
        dual = self.binance_manual_request(dual_endpoint)
        for item in dual['list']:
            if item['purchaseStatus'] == 'SETTLED' and item['isExercised'] == True:
                if item['optionType'] == 'PUT': # buy
                    symbol = item['exercisedCoin']
                    if input_symbol and symbol != input_symbol:
                        continue
                    SymbolCoinAsset = Assetlist[symbol]
                    qty = float(item['settleAmount'])
                    usdt_value = float(item['subscriptionAmount'])
                    SymbolCoinAsset.total_buy_qty += qty
                    SymbolCoinAsset.total_buy_cost += usdt_value
                    SymbolCoinAsset.total_qty += qty
                    SymbolCoinAsset.total_cost += usdt_value
                else:
                    symbol = item['investCoin']
                    if input_symbol and symbol != input_symbol:
                        continue
                    SymbolCoinAsset = Assetlist[symbol]
                    qty = float(item['subscriptionAmount'])
                    usdt_value = float(item['settleAmount'])
                    SymbolCoinAsset.total_sell_qty += qty
                    SymbolCoinAsset.total_sell_income += usdt_value
                    SymbolCoinAsset.total_qty -= qty
                    SymbolCoinAsset.total_cost -= usdt_value
    def get_trade_history_from_auto_invest(self, Assetlist, input_symbol=None):
        return
    # Coin 에 대한 USDT 가격 알아오기.
    def get_usdt_price(self, symbol):
        if symbol == 'USDT':
            return 1.0
        symbol=symbol+'USDT'
        try:
            price_data = self.client.get_symbol_ticker(symbol=symbol)
            return float(price_data['price'])
        except:
            return None
    

