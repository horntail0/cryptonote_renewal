from Reader import Reader
from CoinAsset import CoinAsset, STABLE_ASSET
import os
import time
import hmac
import hashlib
import requests
import json
import HistoryManager
import base64

from datetime import datetime
from dotenv import load_dotenv
from GateioV2API import GateWs
import random

load_dotenv()
class Gateio_Reader(Reader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import API KEY
        mobile = int(os.environ.get("MOBILE", "0"))

        self.BASE_URL = "https://api.gateio.ws"
        self.BASE_URL_V2 = "https://www.gate.com/apiw/v2"
        # Trade History 관련 필드
        self.id_indicator = 'id'
        self.time_indicator = 'create_time'
        self.qty_indicator = 'amount'
        self.price_indicator = 'price'
        self.fee_indicator = 'fee'
        self.feeCurrency_indicator = 'fee_currency'
        self.gateV2=GateWs("wss://ws.gate.io/v3/", "your key", "your secret.")



    def check_buyer(self, trade):
        if trade['side'] == 'buy':
            return True
        elif trade['side'] == 'sell':
            return False

    def get_spot_balance(self, input_symbol=None):
        dict_spot = {}
        endpoint = "/spot/accounts"

        try:
            data = self.gateio_request("GET", endpoint)
        except Exception as e:
            print(f"[Gate.io] Spot 잔고 조회 실패: {e}")
            raise e

        for item in data:
            symbol = item['currency']
            if input_symbol and symbol != input_symbol:
                continue
            total = float(item['available']) + float(item['locked'])
            if total > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_spot, symbol, total, usdt_price)
        return dict_spot

    def get_earn_balance(self, input_symbol=None):
        dict_earn = {}
        # Flexible Earn 잔고 조회
        endpoint = "/earn/uni/lends"

        
        simpleearnvalue = 0.0
        try:
            data = self.gateio_request("GET", endpoint)

        except Exception as e:
            print(f"[Gate.io] Earn 잔고 조회 실패: {e}")
            raise e

        for item in data:
            symbol = item['currency']
            if input_symbol and symbol != input_symbol:
                continue
            amount = float(item['amount'])
            if amount > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_earn, symbol, amount, usdt_price)
                simpleearnvalue += amount * usdt_price


        # Dual Investment 잔고 조회
        endpoint = "/earn/dual/orders"

        dualinvestvalue = 0.0
        try:
            data = self.gateio_request("GET", endpoint)

        except Exception as e:
            print(f"[Gate.io] Earn 잔고 조회 실패: {e}")
            raise e
        
        for item in data:
            if item['status'] != 'PROCESSING':
                continue
            symbol = item['invest_currency']
            if input_symbol and symbol != input_symbol:
                continue
            amount = float(item['invest_amount'])
            if amount > 0:
                usdt_price = self.get_usdt_price(symbol)
                if usdt_price is None:
                    continue
                self.add_CoinAsset_to_dict(dict_earn, symbol, amount, usdt_price)
                dualinvestvalue += amount * usdt_price

        # TODO: Get auto invest assets

        return dict_earn
    
    def get_auto_invest(self):
        endpoint = "autoinvest/orders"
        params = {
            "record_id": 14340377,
            "id": 132136,
            "money": "USDT"
        }

        try:
            data = self.gateio_V2_request(0, "GET", endpoint, params=params)
        except Exception as e:
            print(f"[Gate.io] Auto Invest 잔고 조회 실패: {e}, ")


        for item in data:
            print(item)
            
    def get_staking_balance(self):
        # 요청 정보
        
        url = "https://www.gate.com/apiw/v2/earn/staking/balances"
        MYCOOKIE = "exchange_rate_switch=1; _fbp=fb.1.1749180509207.574521500532428330; curr_fiat=USD; _dx_uzZo5y=147b2731907e2d5bd1823e134488c0095db64c359a1113ea1c8a61550ce5808c0106393c; afUserId=14d3cd04-baee-4d2d-83d7-d19e8dbf6adb-p; b_notify=1; show_zero_funds=0; hide_zero_negative=0; show_zero_funds_wallet=1; defaultBuyCryptoFiat=USD; AF_SYNC=1753981410287; not_gate_refer=1; g_state={\"i_l\":0}; _ga_SNPLSCMNGD=GS2.1.s1754007980$o5$g1$t1754008682$j25$l0$h0; _ga_CF71BLYRCR=GS2.1.s1754007980$o5$g1$t1754008682$j25$l0$h0; _ga=GA1.2.3287240.1749180510; _gid=GA1.2.1763875018.1754353093; finger_print=68914dc5mz8wg19i7ii6q7HZfScthCEhyiTGu0l1; lang=en; login_notice_check=%2F; t_token=83e09e4dfc56b46416f2a645477f4fec; uid=27921228; nickname=01048131860; is_on=1; pver_ws=c16b9f6a685af0f42a684d19a79ccf99; csrftoken=4654526372476c38587855546d4737652f33324e4e716769692b3672566e694f4c30345a31624f3861746f66344572787771783466546c5951674e32517a526d; token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTQzNTMzNTQsImlwIjoiZ2l3UWJ5KzM3RjZwMTQ2R0lwVENmRVhoQnl6RUVLZmZlUDl1VDFhRlVUK2k4eUV2eVRFRVNkcz0iLCJpcFJlc3RyaWN0IjoiQkVuYVVtcTJOYzJNZ0tuV01lTk5QWkd2OHl3bkhkQ1A2TWRneVd3PSIsImRldmljZVR5cGUiOiIrUVQ2RytRTDA1TjZxQ05uVE9yQ1lndGR5enNkLy8raVgveHo2Zk09IiwiZGV2aWNlSWQiOiJ3ZXBpeVVRTXZUZkIrRGdRVUxDOHJ5VHR3YzRIY25jOXBtZmZyQT09IiwidWlkIjoiVnRMNkhNTUl6ZDRmRWJRK214K2Urdmt5MmxtdXUvWEtnZUtUOTFmSFlTR3VCZENSIn0.MNZoKqMWc_N4HGrP2DnB35xTivqp28RFA-sDBpJ0ris; token_type=Bearer; lasturl=%2Fmyaccount%2Ffunds%2Ffinance%2Fstaking; RT=\"z=1&dm=www.gate.com&si=fbae0c6a-1873-4910-a488-5c3966959e58&ss=mdxsj8eu&sl=d&tt=1oe&obo=c&rl=1\"; _ga_JNHPQJS9Q4=GS2.2.s1754353093$o7$g1$t1754353402$j32$l0$h0; token_type=Bearer; lasturl=%2Fmyaccount%2Ffunds%2Ffinance%2Fstaking"
        headers = {
            "authority": "www.gate.com",
            "method": "GET",
            "accept": "application/json, text/plain, */*",
            "referer": "https://www.gate.com/myaccount/funds/finance/staking",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36 Edg/138.0.0.0",
            "cookie": MYCOOKIE
        }

        response = requests.get(url, headers=headers)

        print(response.status_code)
        try:
            print(response.json())
        except Exception as e:
            print(response.text)

    def get_auto_invest_history(self):
        record_id = 15464191
        id = 154487
        url = f"https://www.gate.com/apiw/v2/autoinvest/orders?record_id={record_id}&id={id}&money=USDT"
        print(url)
        MYCOOKIE = "exchange_rate_switch=1; _fbp=fb.1.1749180509207.574521500532428330; curr_fiat=USD; _dx_uzZo5y=147b2731907e2d5bd1823e134488c0095db64c359a1113ea1c8a61550ce5808c0106393c; afUserId=14d3cd04-baee-4d2d-83d7-d19e8dbf6adb-p; b_notify=1; show_zero_funds=0; hide_zero_negative=0; show_zero_funds_wallet=1; defaultBuyCryptoFiat=USD; AF_SYNC=1753981410287; not_gate_refer=1; g_state={\"i_l\":0}; _ga_SNPLSCMNGD=GS2.1.s1754007980$o5$g1$t1754008682$j25$l0$h0; _ga_CF71BLYRCR=GS2.1.s1754007980$o5$g1$t1754008682$j25$l0$h0; _ga=GA1.2.3287240.1749180510; _gid=GA1.2.1763875018.1754353093; finger_print=68914dc5mz8wg19i7ii6q7HZfScthCEhyiTGu0l1; lang=en; login_notice_check=%2F; uid=27921228; nickname=01048131860; is_on=1; pver_ws=c16b9f6a685af0f42a684d19a79ccf99; csrftoken=4654526372476c38587855546d4737652f33324e4e716769692b3672566e694f4c30345a31624f3861746f66344572787771783466546c5951674e32517a526d; token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTQzNTMzNTQsImlwIjoiZ2l3UWJ5KzM3RjZwMTQ2R0lwVENmRVhoQnl6RUVLZmZlUDl1VDFhRlVUK2k4eUV2eVRFRVNkcz0iLCJpcFJlc3RyaWN0IjoiQkVuYVVtcTJOYzJNZ0tuV01lTk5QWkd2OHl3bkhkQ1A2TWRneVd3PSIsImRldmljZVR5cGUiOiIrUVQ2RytRTDA1TjZxQ05uVE9yQ1lndGR5enNkLy8raVgveHo2Zk09IiwiZGV2aWNlSWQiOiJ3ZXBpeVVRTXZUZkIrRGdRVUxDOHJ5VHR3YzRIY25jOXBtZmZyQT09IiwidWlkIjoiVnRMNkhNTUl6ZDRmRWJRK214K2Urdmt5MmxtdXUvWEtnZUtUOTFmSFlTR3VCZENSIn0.MNZoKqMWc_N4HGrP2DnB35xTivqp28RFA-sDBpJ0ris; token_type=Bearer; RT=\"z=1&dm=www.gate.com&si=fbae0c6a-1873-4910-a488-5c3966959e58&ss=mdxsj8eu&sl=e&tt=1oe&obo=d&rl=1\"; _gat_UA-1833997-40=1; lasturl=%2Fauto-investment; _ga_JNHPQJS9Q4=GS2.2.s1754353093$o7$g1$t1754354693$j47$l0$h0"
        headers = {
            "authority": "www.gate.com",
            "method": "GET",
            "accept": "application/json, text/plain, */*",
            "referer": f"https://www.gate.com/auto-investment/{id}",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36 Edg/138.0.0.0",
            "cookie": MYCOOKIE
        }
        response = requests.get(url, headers=headers)

        print(response.status_code)
        try:
            print(response.json())
        except Exception as e:
            print(response.text)
            
    def get_trade_history_from_dual_investment(self, Assetlist, input_symbol=None):
        endpoint = "/earn/dual/orders"
        try:
            data = self.gateio_request("GET", endpoint)

        except Exception as e:
            print(f"[Gate.io] Earn 잔고 조회 실패: {e}")
            raise e
        
        for item in data:
            if item['status'] != 'SETTLEMENT_SUCCESS':
                continue
            if item['invest_currency'] in STABLE_ASSET: # Buy low
                symbol = item['exercise_currency']
                if input_symbol and symbol != input_symbol:
                    continue
                if float(item['exercise_price']) > float(item['settlement_price']):
                    amount = float(item['settlement_amount'])
                    usdt_value = float(item['invest_amount'])
                    if symbol not in Assetlist:
                        Assetlist[symbol] = CoinAsset(symbol, 0, 0)
                    SymbolCoinAsset = Assetlist[symbol]
                    SymbolCoinAsset.total_buy_qty += amount
                    SymbolCoinAsset.total_buy_cost += usdt_value
                    SymbolCoinAsset.total_qty += amount
                    SymbolCoinAsset.total_cost += usdt_value
            else: # Sell high
                symbol = item['invest_currency']
                if input_symbol and symbol != input_symbol:
                    continue
                if float(item['exercise_price']) < float(item['settlement_price']):
                    amount = float(item['invest_amount'])
                    usdt_value = float(item['settlement_amount'])
                    if symbol not in Assetlist:
                        Assetlist[symbol] = CoinAsset(symbol, 0, 0)
                    SymbolCoinAsset = Assetlist[symbol]
                    SymbolCoinAsset.total_sell_qty += amount
                    SymbolCoinAsset.total_sell_income += usdt_value
                    SymbolCoinAsset.total_qty -= amount
                    SymbolCoinAsset.total_cost -= usdt_value


    def get_trade_history_from_auto_invest(self, Assetlist, input_symbol=None):
        autoinvesthistoryList = HistoryManager.list_json_files("./autoinvest")
        for autoinvesthistory in autoinvesthistoryList:
            
            filepath = os.path.join("autoinvest", autoinvesthistory)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            autoinvest_list = data['list']
            for investitem in autoinvest_list:
                symbol = investitem['asset']
                if input_symbol and symbol != input_symbol:
                    continue
                amount = float(investitem['cum_invest'])
                usdt_price = float(investitem['avg_price'])
                usdt_value = amount * usdt_price

                SymbolCoinAsset = Assetlist[symbol]
                SymbolCoinAsset.total_buy_qty += amount
                SymbolCoinAsset.total_buy_cost += usdt_value
                SymbolCoinAsset.total_qty += amount
                SymbolCoinAsset.total_cost += usdt_value
        



    def get_unified_balance(self):
        dict_staking = {}
        endpoint = "/unified/accounts"
        
        try:
            data = self.gateio_request("GET", endpoint)

        except Exception as e:
            print(f"[Gate.io] 잔고 조회 실패: {e}")
            raise e
        
        for item in data.items():
            print(item)



    def get_usdt_price(self, symbol):
        if symbol == "USDT":
            return 1.0
        if symbol.endswith("2"):
                symbol = symbol[:-1]
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol}_USDT"
            response = requests.get(url)
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                #print(symbol, data[0]['last'])
                return float(data[0]['last'])
        except:
            pass
        return None
    
    def get_trade_history_from_reader(self, currency_pair, last_time):
        days_back=730
        now = int(time.time())
        one_day = 86400
        start = max(now - one_day * days_back, last_time)
        start_backup = start
        end = now
        day_gap = 30
        trades = []
        if currency_pair.endswith("USDT") and not currency_pair.endswith("_USDT"):
            currency_pair = currency_pair.replace("USDT", "_USDT")
        if currency_pair.endswith("USDC") and not currency_pair.endswith("_USDC"):
            currency_pair = currency_pair.replace("USDC", "_USDC")

        print(f"[Gate.io] 거래내역 조회, {currency_pair}")
        start = start_backup
        while start < end:

            params = {
                "currency_pair": currency_pair,
                "from": start,
                "to": start + one_day * day_gap,  # n일 간격으로 쪼개서 요청
                "limit": 1000
            }
            try:
                data = self.gateio_request("GET", "/spot/my_trades", params)
            except Exception as e:
                print(f"[Gate.io] 거래내역 조회 오류: {e}, {currency_pair}, {start}")
                break
            for item in data:
                print(item)
            if isinstance(data, list) and len(data) > 0:
                trades.extend(data)

            if not trades:
                start += one_day * day_gap
                continue

            start += one_day * day_gap
            time.sleep(0.3)  # rate limit 회피
        return trades, end

    def gateio_request(self, method, endpoint, params=None):
        path = endpoint  # 시그니처용 경로는 '/spot/accounts' 형태
        url = self.BASE_URL + "/api/v4" + endpoint
        query_string = ''
        body = params if method == 'POST' else None

        if method == 'GET' and params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url += '?' + query_string

        body_str = json.dumps(body) if body else ''
        sign, timestamp = self.generate_signature(method, path, query_string, body_str)
        apikey = self.API_KEY
        headers = {
            'KEY': apikey,
            'Timestamp': timestamp,
            'SIGN': sign
        }
        if method == 'POST':
            headers['Content-Type'] = 'application/json'

        response = requests.request(
            method,
            url,
            headers=headers,
            json=body if method == 'POST' else None,
            verify=True
        )

        #print(f"Request URL: {url}")
        #print(f"Request Headers: {headers}")
        #print(f"Response Status: {response.status_code}")
        #print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    def gateio_V2_request(self, method, endpoint, params=None, customurl=False):
        path = endpoint  # 시그니처용 경로는 '/spot/accounts' 형태

        url = self.BASE_URL_V2 + endpoint
        query_string = ''
        body = params if method == 'POST' else None

        if method == 'GET' and params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url += '?' + query_string

        body_str = json.dumps(body) if body else ''
        sign, timestamp = self.generate_V2_signature()
        apikey = self.API_KEY
        headers = {
            'KEY': apikey,
            'Timestamp': timestamp,
            'SIGN': sign
        }
        if method == 'POST':
            headers['Content-Type'] = 'application/json'

        response = requests.request(
            method,
            url,
            headers=headers,
            json=body if method == 'POST' else None,
            verify=True
        )

        #print(f"Request URL: {url}")
        #print(f"Request Headers: {headers}")
        #print(f"Response Status: {response.status_code}")
        #print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()    
    

# 시그니처 생성 함수

    def generate_signature(self, method, path, query_string='', body_str=''):
        
        t = str(int(time.time()))
        path = "/api/v4" + path
        m = hashlib.sha512()
        m.update((body_str or "").encode('utf-8'))
        hashed_payload = m.hexdigest()
        payload = f"{method}\n{path}\n{query_string}\n{hashed_payload}\n{t}"
        secretkey = self.API_SECRET
        sign = hmac.new(secretkey.encode('utf-8'), payload.encode('utf-8'), hashlib.sha512).hexdigest()
        return sign, t
    
    def generate_V2_signature(self):
        secret_key = self.API_SECRET
        nonce = int(time.time() * 1000)
        message = str(nonce)
        h = (base64.b64encode(hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha512).digest())).decode()
        return h, message