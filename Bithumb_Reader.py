from Reader import Reader
from CoinAsset import CoinAsset

import time
import jwt
import uuid
import requests
import os
import urllib.parse
import hashlib

from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

class Bithumb_Reader(Reader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mobile = int(os.environ.get("MOBILE", "0"))


        self.BASE_URL = "https://api.bithumb.com"

        # Trade History 관련 필드
        self.id_indicator = 'uuid'
        self.qty_indicator = 'executed_volume'
        self.price_indicator = 'price'
        self.time_indicator = 'created_at'
        self.fee_indicator = 'paid_fee'
        self.feeCurrency_indicator = None
    def check_buyer(self, trade):
        if trade['side'] == 'bid':
            return True
        elif trade['side'] == 'ask':
            return False

    def get_spot_balance(self, input_symbol=None):
        dict_spot = {}
        endpoint = "/v1/accounts"
        data = self.bithumb_request(endpoint)

        for item in data:
            symbol = item['currency'].upper()
            if input_symbol and symbol != input_symbol:
                continue
            amount = float(item['balance']) + float(item['locked'])
            if amount > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_spot, symbol, amount, usdt_price)
        return dict_spot
    
    def get_trade_history_from_reader(self, currency_pair, last_time = 0):
        payment_currency = 'KRW'
        market = payment_currency + "-" + (currency_pair.replace("USDT", ""))

        endpoint = '/v1/orders'
        all_trades = []
        offset = 0
        max_pages = 1

        while True:
            params = {
                'market': market,
                'state': 'done',  # 완료된 거래만 조회
                'page' : offset + 1,  # 페이지는 1부터 시작
                'limit': 50  # 한 페이지당 최대 50개 거래
            }

            try:
                trades = self.bithumb_request(endpoint, params)
            except Exception as e:
                print(f"[Bithumb] 거래내역 조회 오류: {e}, {market}")
                trades = []
                break
            if not trades:
                if offset == 0:
                    print(f"{market} 거래 내역이 없습니다.")
                break
            #trades = data.get('data', [])


            
            all_trades.extend(trades)
            print(f"page {offset+1} {len(trades)}건 수집됨")

            offset += 1
            time.sleep(0.2)  # 과호출 방지


        return all_trades, last_time
    
    def get_trade_history_from_dual_investment(self, Assetlist, input_symbol=None):
        return
    def get_trade_history_from_auto_invest(self, Assetlist, input_symbol=None):
        return
    def bithumb_request(self, endpoint, params=None):
        url = self.BASE_URL + endpoint
        params = params or {}
        
        # URL 인코딩
        query = urllib.parse.urlencode(params)
        query_hash = hashlib.sha512(query.encode()).hexdigest() if query else ''
        
        payload = {
            'access_key': self.API_KEY,
            'nonce': str(uuid.uuid4()),
            'timestamp': round(time.time() * 1000),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }
        jwt_token = jwt.encode(payload, self.API_SECRET)
        authorization_token = 'Bearer {}'.format(jwt_token)
        headers = {
            'Authorization': authorization_token
        }
        

        response = requests.get(url, headers=headers, params=params)
        # print(f"Request URL: {url}")
        # print(f"Request Headers: {headers}")
        # print(f"Response Status: {response.status_code}")
        # print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    

    def get_KRW_Currency(self, symbol):
        symbol = 'KRW-' + symbol
        endpoint = f"/v1/ticker?markets={symbol}"
        data = self.bithumb_request(endpoint)
        if data and isinstance(data, list) and len(data) > 0:
            return float(data[0]['trade_price'])
        return None

    def get_usdt_price(self, symbol):
        KRW_price = self.get_KRW_Currency(symbol) if symbol != 'KRW' else 1.0
        USDT_KRW_price = self.get_KRW_Currency('USDT')
        if KRW_price is not None and USDT_KRW_price is not None:
            return KRW_price / USDT_KRW_price
        
    def get_USDT_KRW_at(self, datestring, interval: str = '5m') -> float:
        endpoint = '/v1/candles/minutes/5'
        dt = datetime.fromisoformat(datestring)
        dt_utc = dt.astimezone(timezone.utc)
        z_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S")

        params = {
            'market': 'KRW-USDT',
            'to': z_str,   # 이 시각을 exclusive 기준으로 직전 캔들을 반환
            'count': 1      # 한 개만
        }
        trades = self.bithumb_request(endpoint, params)

        close_price = trades[0]['trade_price'] if trades and 'trade_price' in trades[0] else None
        return close_price if close_price is not None else 0.0
    

    
    def get_KRW_deposits(self):
        total_deposit = 0
        endpoint = "/v1/deposits/krw"
        data = self.bithumb_request(endpoint)
        for item in data:
            if (item['state'] == 'CANCELLED'):
                continue
            total_deposit += int(item['amount'])
        # print(f"total_deposit = {total_deposit}")
        total_deposit = round(total_deposit, 0)
        return total_deposit

    def get_KRW_withdrawals(self):
        total_withdraws = 0
        total_fee = 0
        endpoint = "/v1/withdraws/krw"
        data = self.bithumb_request(endpoint)
        for item in data:
            if (item['state'] == 'DONE'):
                total_withdraws += int(item['amount'])
                total_fee += int(item['fee'])
        # print(f"total_withdraws = {total_withdraws}")
        # print(f"total_fee = {total_fee}")
        total_withdraws = round(total_withdraws, 0)
        total_fee = round(total_fee, 2)
        return total_withdraws, total_fee
    


    def print_KRW_deposit_history(self):
        endpoint = "/v1/deposits/krw"
        data = self.bithumb_request(endpoint)
        print("=== KRW 입금 내역 ===")
        for item in data:
            print(f"시간: {item.get('created_at', 'N/A')}, 금액: {item.get('amount', 'N/A')}, 상태: {item.get('state', 'N/A')}, 입금자명: {item.get('sender', 'N/A')}")

    def print_KRW_withdrawal_history(self):
        endpoint = "/v1/withdraws/krw"
        data = self.bithumb_request(endpoint)
        print("=== KRW 출금 내역 ===")
        for item in data:
            print(f"시간: {item.get('created_at', 'N/A')}, 금액: {item.get('amount', 'N/A')}, 수수료: {item.get('fee', 'N/A')}, 상태: {item.get('state', 'N/A')}, 출금계좌: {item.get('bank', 'N/A')}")

