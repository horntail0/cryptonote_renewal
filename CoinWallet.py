import pandas as pd
from CoinAsset import CLUSTER_ASSET, STABLE_ASSET, CoinAsset
from collections import OrderedDict

class CoinWallet:
    def __init__(self, binance_reader, bithumb_reader, gateio1_reader, gateio2_reader, personal_reader=None):
        
        self.assets = {}  # dict of CoinAsset instances (from CoinAsset.py)
        self.readers = OrderedDict()
        self.readers['binance'] = binance_reader
        self.readers['bithumb'] = bithumb_reader
        self.readers['gateio1'] = gateio1_reader
        self.readers['gateio2'] = gateio2_reader
        self.readers['personal'] = personal_reader

        self.Total_Assets_value = 0.0

        self.Stable_Assets_value = 0.0

        self.KRW_deposits = 0.0
        self.KRW_withdrawals = 0.0
        self.KRW_fees = 0.0
        self.CurrentKRWUSDT = 0.0
        self.Benefit_Ratio = 0.0

        self.Temporary_assets = {
        }

    def get_temporary_assets_dict(self, exchange_name):
        temp_dict = {}
        for asset in self.Temporary_assets.get(exchange_name, []):
            if asset.symbol in temp_dict:
                temp_dict[asset.symbol].amount += asset.amount
                temp_dict[asset.symbol].usdt_value += asset.usdt_value
            else:
                temp_dict[asset.symbol] = CoinAsset(asset.symbol, asset.amount, asset.usdt_price)
        return temp_dict


    def export_assets_to_excel(self, filename="assets.xlsx"):
        data = []
        for asset in self.assets.values():
            data.append({
                "symbol": asset.symbol,
                "amount": asset.amount,
                "usdt_price": round(asset.usdt_price, 5),
                "usdt_value": round(asset.usdt_value, 3),
                "ratio": round(asset.ratio, 2),
                "ratio_nonstable": round(asset.ratio_nonstable, 2),
                "ratio_clustered": round(asset.ratio_clustered, 2),
                "ratio_clustered_nonstable": round(asset.ratio_clustered_nonstable, 2)
            })
        data = sorted(data, key=lambda x: x['ratio_clustered'], reverse=True)
        data.append({})
        data.append({
            "symbol": "Total Assets Value",
            "usdt_value": round(self.Total_Assets_value, 3),
            "ratio": round(self.Total_Assets_value * self.CurrentKRWUSDT, 1)

        })
        data.append({
            "symbol": "Stable Assets Value",
            "usdt_value": round(self.Stable_Assets_value, 3)
        })
        stable_ratio = (self.Stable_Assets_value / self.Total_Assets_value * 100) if self.Total_Assets_value else 0.0
        data.append({
            "symbol": "Stable Asset Ratio (%)",
            "usdt_value": round(stable_ratio, 2)
        })
        data.append({
            "symbol": "KRW Deposits",
            "usdt_value": round(self.KRW_deposits, 3)
        })
        data.append({
            "symbol": "KRW Withdrawals",
            "usdt_value": round(self.KRW_withdrawals, 3)
        })
        data.append({
            "symbol": "KRW Fees",
            "usdt_value": round(self.KRW_fees, 3)
        })
        CurrentKRWBalance = self.KRW_deposits - self.KRW_withdrawals - self.KRW_fees
        total_krw_balance_usdt = CurrentKRWBalance / self.CurrentKRWUSDT if self.CurrentKRWUSDT else 0.0
        data.append({
            "symbol": "Total KRW Balance",
            "usdt_value": round(total_krw_balance_usdt, 3),
            "ratio": round(CurrentKRWBalance, 3)
        })
        data.append({
            "symbol": "Benefit",
            "usdt_value": round(self.Total_Assets_value - total_krw_balance_usdt, 2),
            "ratio": round((self.Total_Assets_value - total_krw_balance_usdt) * self.CurrentKRWUSDT, 1)
        })
        data.append({
            "symbol": "Current KRW USDT Rate",
            "usdt_value": round(self.CurrentKRWUSDT, 5)
        })
        self.Benefit_Ratio = ((self.Total_Assets_value * self.CurrentKRWUSDT) - CurrentKRWBalance) / CurrentKRWBalance * 100 if CurrentKRWBalance else 0.0
        data.append({
            "symbol": "Benefit Ratio",
            "usdt_value": round(self.Benefit_Ratio, 2)
        })
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        print(f"Exported assets to {filename}")
