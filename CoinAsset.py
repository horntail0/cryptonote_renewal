CLUSTER_ASSET = [
    ['ETH', 'WBETH', 'GTETH'],
    ['SOL', 'SOL2', 'BNSOL', 'JITOSOL'],
    ["GT", "GT2"],
    ["BNB", "SLISBNB"],
    ["BTC", "GTBTC"],
    ["USDT", "USDC", "FDUSD", "KRW"]
]
STABLE_ASSET = CLUSTER_ASSET[-1]  # 마�?�?그룹???�테?�블 코인 그룹
class CoinAsset:

    def __init__(self, symbol, amount=0.0, usdt_price=0.0):
        # Basic attributes for CoinAsset
        normalized_symbol = str(symbol).upper().strip()
        self.symbol = normalized_symbol  # ?�산 ?�볼
        self.amount = amount  # 보유 ?�량
        self.usdt_price = usdt_price  # ?�재 USDT ?�위가�?
        self.usdt_value = amount * usdt_price  # ?�재 보유 ?�산??USDT 가�?

        # Additional attributes for CoinAsset : History
        self.total_buy_qty = 0  # �?매수 ?�량
        self.total_buy_cost = 0  # �?매수 비용
        self.total_sell_qty = 0  # �?매도 ?�량
        self.total_sell_income = 0  # �?매도 ?�익
        self.total_qty = 0  # ?�재 보유 ?�량 (매수 - 매도)
        self.total_cost = 0  # ?�재 보유 ?�산??�?비용
        self.avg_buy_price = 0.0  # ?�균 매수 가�?
        self.avg_price = 0.0  # ?�재 ?�균 가�?(매수 - 매도)

        # Additional attributes for CoinAsset : Status
        self.IsStable = False if normalized_symbol not in STABLE_ASSET else True  # ?�테?�블코인 ?��?
        self.NeedCluster = False
        for cluster in CLUSTER_ASSET:
            if normalized_symbol in cluster:
                self.NeedCluster = True
                self.Cluster = cluster
                break
        self.MainCoin = None
        if self.NeedCluster:
            self.MainCoin = self.Cluster[0]

        # Additional attributes for CoinAsset : Ratio
        self.ratio = 0.0  # ?�체 ?�산 ?��?비율
        self.ratio_nonstable = 0.0  # ?�테?�블 코인 ?�외 ?�체 ?�산 ?��?비율
        self.ratio_clustered = 0.0  
        self.ratio_clustered_nonstable = 0.0

        # Additional attributes for CoinAsset : Fee
        self.fee = {}  # ?�수�??�역

    def get_avg_price(self):
        if self.IsStable:
            return
        self.avg_buy_price = self.total_buy_cost / self.total_buy_qty if self.total_buy_qty > 0 else 0.0
        self.avg_price = self.total_cost / self.total_qty if self.total_qty > 0 else 0.0
        return
    def __repr__(self):
        base = (f"CoinAsset({self.symbol} : amount={self.amount}, usdt_price={self.usdt_price:.4f}, "
                f"usdt_value={self.usdt_value:.4f})")
        ratio_info = ""
        if self.ratio != 0.0:
            ratio_info += f" Ratio: {self.ratio:.2f}%"
        if self.ratio_nonstable != 0.0:
            ratio_info += f", Non-Stable Ratio: {self.ratio_nonstable:.2f}%"
        if self.ratio_clustered != 0.0:
            ratio_info += f", Clustered Ratio: {self.ratio_clustered:.2f}%"
        if self.ratio_clustered_nonstable != 0.0:
            ratio_info += f", Clustered Non-Stable Ratio: {self.ratio_clustered_nonstable:.2f}%"
        if self.total_buy_qty > 0 or self.total_sell_qty > 0:
            ratio_info += f", Total Buy Qty: {self.total_buy_qty}, Total Sell Qty: {self.total_sell_qty}"
        if self.total_buy_cost > 0 or self.total_sell_income > 0:
            ratio_info += f", Total Buy Cost: {self.total_buy_cost:.2f}, Total Sell Income: {self.total_sell_income:.2f}"
        if self.total_sell_qty > 0 or self.total_qty != 0:
            ratio_info += f", Total Sell Qty: {self.total_sell_qty}, Total Qty: {self.total_qty}"
        if self.total_sell_income > 0 or self.total_cost != 0:
            ratio_info += f", Total Sell Income: {self.total_sell_income:.2f}, Total Cost: {self.total_cost:.2f}"
        
        if self.total_qty != 0 or self.total_cost != 0:
            ratio_info += f", Total Qty: {self.total_qty}, Total Cost: {self.total_cost:.2f}"
        if self.avg_buy_price > 0:
            ratio_info += f", Avg Buy Price: {self.avg_buy_price:.4f}"
        if self.avg_price > 0:
            ratio_info += f", Avg Price: {self.avg_price:.4f}"
        if self.fee:
            fee_info = ", Fees: " + ", ".join(f"{k}: {v:.4f}" for k, v in self.fee.items())
            ratio_info += fee_info
        
        
        return base + ratio_info

