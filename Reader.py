from CoinAsset import CoinAsset
from CoinAsset import CLUSTER_ASSET, STABLE_ASSET
import HistoryManager
import re
from datetime import datetime, timedelta
from dateutil.parser import parse
class Reader:
    def __init__(self, name, apikey, secretkey, *args, **kwargs):
        self.name = name
        self.API_KEY = apikey
        self.API_SECRET = secretkey
    def load_assets(self):
        # assets: CoinAsset 리스트
        dict_spot_assets = self.get_spot_balance()
        dict_earn_assets = self.get_earn_balance()
        # 두 리스트를 합산 (심볼 기준으로 amount, usdt_price 등 합산)
        asset_dict = {}
        total_usdt_value = 0.0
        # spot_assets와 earn_assets를 합쳐서 asset_dict에 저장
        for sa in dict_spot_assets.values():
            if sa.symbol in asset_dict:
                asset_dict[sa.symbol].amount += sa.amount
                asset_dict[sa.symbol].usdt_value += sa.usdt_value
            else:
                asset_dict[sa.symbol] = sa
        if dict_earn_assets:
            for ea in dict_earn_assets.values():
                if ea.symbol in asset_dict:
                    asset_dict[ea.symbol].amount += ea.amount
                    asset_dict[ea.symbol].usdt_value += ea.usdt_value
                    # usdt_price 등 필요한 필드도 합산/갱신
                else:
                    asset_dict[ea.symbol] = ea
        for asset in asset_dict.values():
            if asset.usdt_value > 0:
                total_usdt_value += asset.usdt_value
        print(self.name, total_usdt_value)
        return asset_dict
    

    def load_symbol_assets(self, symbol):
        # 특정 심볼에 대한 자산을 로드
        dict_spot_assets = self.get_spot_balance(symbol)
        dict_earn_assets = self.get_earn_balance(symbol)
        asset_dict = {}
        for sa in dict_spot_assets.values():
            if sa.symbol in asset_dict:
                asset_dict[sa.symbol].amount += sa.amount
                asset_dict[sa.symbol].usdt_value += sa.usdt_value
            else:
                asset_dict[sa.symbol] = sa
        if dict_earn_assets:
            for ea in dict_earn_assets.values():
                if ea.symbol in asset_dict:
                    asset_dict[ea.symbol].amount += ea.amount
                    asset_dict[ea.symbol].usdt_value += ea.usdt_value
                    # usdt_price 등 필요한 필드도 합산/갱신
                else:
                    asset_dict[ea.symbol] = ea
        return asset_dict
    def get_spot_balance(self, input_symbol=None):
        # Implement logic to fetch spot balance
        pass

    def get_earn_balance(self, input_symbol=None):
        # Implement logic to fetch earn balance
        pass
    def get_trade_history_from_reader(self, currency_pair, last_time):
        # Implement logic to fetch trade history from the reader
        pass


    def get_trade_history(self, Assetlist, input_symbol = None):
        ReaderHistoryList = HistoryManager.list_json_files("./history", self.name)
        # Implement logic to fetch trade history
        for stable_asset in STABLE_ASSET:
            if stable_asset == "KRW":
                continue
            if "bithumb" in self.name and stable_asset != "USDT":
                continue
            if stable_asset == "FDUSD" and "binance" not in self.name:
                continue
            for symbol, asset in Assetlist.items():
                if symbol in STABLE_ASSET:
                    continue
                if input_symbol and symbol != input_symbol:
                    continue
                filename = f"{self.name}_trades_{symbol}{stable_asset}.json"
                currency_pair = symbol + stable_asset
                last_time = 0
                all_trades = []

                if filename in ReaderHistoryList:
                    all_trades = HistoryManager.load_trades_from_file(currency_pair, filename)
                    if all_trades:
                        if all_trades[0][self.id_indicator] == "DUMMY":
                            last_time = int(all_trades[0][self.time_indicator])
                            all_trades = []
                        else:
                            print(f"[{self.name}] {currency_pair} 거래내역 로드 완료, {len(all_trades)}건")
                            # 이미 저장된 데이터의 마지막 거래 시각을 확인
                            if is_iso8601_datetime(all_trades[0][self.time_indicator]):
                                last_time = int(parse(all_trades[0][self.time_indicator]).timestamp())
                            else:
                                last_time = max(int(t[self.time_indicator]) for t in all_trades)
                            #self.accumulate_trade_history(all_trades, Assetlist, symbol)

                    else:
                        last_time = 0
                    # Get the latest trade history from the reader
                else:
                    print(f"[{self.name}] {currency_pair} 거래내역 파일이 없습니다. 새로 가져옵니다.")
                    last_time = 0
                

                trade_history_from_reader, end_ts = self.get_trade_history_from_reader(currency_pair, last_time)
                if trade_history_from_reader is None:
                    print(f"[{self.name}] {currency_pair} 거래내역을 가져오지 못했습니다.")
                    continue

                
                all_trades.extend(trade_history_from_reader)

                # 중복 제거 (id 기준)
                unique_trades = {t[self.id_indicator]: t for t in all_trades}
                all_trades = list(unique_trades.values())

                # 시간순 정렬
                self.accumulate_trade_history(all_trades, Assetlist, symbol)
                if all_trades and is_iso8601_datetime(all_trades[0][self.time_indicator]):
                    all_trades.sort(key=lambda x: parse(x[self.time_indicator]))
                else:
                    all_trades.sort(key=lambda x: int(x[self.time_indicator]))
                if all_trades == []:
                    dummy_trade = {
                        self.id_indicator: "DUMMY",
                        self.time_indicator: end_ts,
                    }
                    all_trades.append(dummy_trade)
                HistoryManager.save_trades_to_file(currency_pair, filename, all_trades)

            
        
        self.get_trade_history_from_dual_investment(Assetlist, input_symbol)
        self.get_trade_history_from_auto_invest(Assetlist, input_symbol)

        
        return
       


    def get_trade_history_from_dual_investment(self, Assetlist):
        # Implement logic to fetch trade history from dual investment
        # This is a placeholder method and should be overridden by subclasses if needed
        pass

    def accumulate_trade_history(self, all_trades, Assetlist, symbol):
        if symbol not in Assetlist:
            print(f"[Binance] {symbol} 에 대한 거래내역이 Assetlist에 없습니다.")
            Assetlist[symbol] = CoinAsset(symbol, 0.0, 0.0)
        buy_qty = 0.0
        buy_cost = 0.0
        sell_qty = 0.0
        sell_income = 0.0

        SymbolCoinAsset = Assetlist[symbol]
        for trade in all_trades:
            qty = float(trade[self.qty_indicator])
            price = float(trade[self.price_indicator])
            usdt_value = qty * price
            fee = float(trade[self.fee_indicator])
            
            if 'bithumb' in self.name:
                fee_currency = 'USDT'
                fee = fee / self.get_USDT_KRW_at(trade[self.time_indicator]) if fee > 0 else 0
                price = price / self.get_USDT_KRW_at(trade[self.time_indicator]) if price > 0 else 0
                usdt_value = qty * price
            else:
                fee_currency = trade[self.feeCurrency_indicator]
            
            if fee_currency not in SymbolCoinAsset.fee:
                SymbolCoinAsset.fee[fee_currency] = 0.0
            SymbolCoinAsset.fee[fee_currency] += fee

            if self.check_buyer(trade) == True:  # 매수

                SymbolCoinAsset.total_buy_qty += qty
                SymbolCoinAsset.total_buy_cost += usdt_value
                SymbolCoinAsset.total_qty += qty
                SymbolCoinAsset.total_cost += usdt_value
                buy_qty += qty
                if fee_currency == symbol:
                    SymbolCoinAsset.total_buy_qty -= fee
                    SymbolCoinAsset.total_qty -= fee


            else:
                SymbolCoinAsset.total_sell_qty += qty
                SymbolCoinAsset.total_sell_income += usdt_value
                SymbolCoinAsset.total_qty -= qty
                SymbolCoinAsset.total_cost -= usdt_value
                sell_qty += qty
                if fee_currency in STABLE_ASSET:
                    SymbolCoinAsset.total_sell_income -= fee
            
            print(f"[{self.name}] {symbol}")
            print(f"buy_qty = {buy_qty}, sell_qty = {sell_qty}")
        return       

    def add_CoinAsset_to_dict(self, asset_dict, symbol, amount, usdt_price):
        usdt_value = amount * usdt_price if usdt_price else 0
        if usdt_value < 0.1:
            return
        if symbol not in asset_dict:
            asset_dict[symbol] = CoinAsset(symbol, amount, usdt_price)
        else:
            asset_dict[symbol].amount += amount
            # asset_dict[symbol].usdt_price = usdt_price
            asset_dict[symbol].usdt_value += amount * usdt_price if usdt_price else 0


def is_iso8601_datetime(value):
    if not isinstance(value, str):
        return False
    try:
        parse(value)
        return True
    except Exception:
        return False