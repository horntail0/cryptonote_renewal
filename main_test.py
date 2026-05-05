import CoinWallet
from CoinAsset import CLUSTER_ASSET, STABLE_ASSET
import Binance_Reader
import Gateio_Reader
import Bithumb_Reader
import os
import subprocess
import time
from dotenv import load_dotenv
os.environ["MOBILE"] = "0"  # 0 또는 1로 설정
load_dotenv()
def run_cmd(cmd):
    """명령어 실행 후 출력 결과와 상태코드 반환"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def start_time_service():
    """Windows Time 서비스가 꺼져 있으면 자동 시작"""
    print("[*] Windows Time 서비스 시작 확인 중...")
    # 서비스 상태 확인
    status_cmd = 'sc query w32time'
    out, err, _ = run_cmd(status_cmd)

    if "RUNNING" in out:
        print("[+] Windows Time 서비스가 이미 실행 중입니다.")
        return True

    print("[*] Windows Time 서비스가 실행 중이 아닙니다. 시작 시도 중...")
    # 서비스 시작
    start_cmd = 'net start w32time'
    out, err, code = run_cmd(start_cmd)

    if code == 0 and "started successfully" in out.lower():
        print("[+] Windows Time 서비스 시작 성공.")
        return True
    elif "already been started" in out:
        print("[+] 이미 시작된 상태로 간주합니다.")
        return True
    else:
        print(f"[!] 서비스 시작 실패: {err or out}")
        return False
    
def sync_time():
    """시간 동기화 명령 실행"""
    print("[*] 시간 동기화 실행 중...")
    sync_cmd = 'w32tm /resync'
    out, err, code = run_cmd(sync_cmd)

    if code == 0:
        print(f"[+] 동기화 성공: {out}")
    else:
        print(f"[!] 동기화 실패: {err or out}")



def main():
    #if start_time_service():
    #    time.sleep(1)  # 서비스 시작 후 대기
    #    sync_time()
    # 시스템 시간을 time.windows.com과 동기화
    #os.system("w32tm /resync")
    if os.environ["MOBILE"] == "0":
        CW = CoinWallet.CoinWallet(
            binance_reader=Binance_Reader.Binance_Reader('binance', os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY")),
            bithumb_reader=Bithumb_Reader.Bithumb_Reader('bithumb', os.getenv("BITHUMB_API_KEY"), os.getenv("BITHUMB_SECRET_KEY")),
            gateio1_reader=Gateio_Reader.Gateio_Reader('gateio1', os.getenv("GATEIO_API_KEY"), os.getenv("GATEIO_SECRET_KEY")),
            gateio2_reader=Gateio_Reader.Gateio_Reader('gateio2', os.getenv("GATEIO_API_KEY_2ND"), os.getenv("GATEIO_SECRET_KEY_2ND"))
        )
    else:
        CW = CoinWallet.CoinWallet(
            binance_reader=Binance_Reader.Binance_Reader('binance_mobile', os.getenv("BINANCE_API_KEY_MOBILE"), os.getenv("BINANCE_SECRET_KEY_MOBILE")),
            bithumb_reader=Bithumb_Reader.Bithumb_Reader('bithumb_mobile', os.getenv("BITHUMB_API_KEY_V1"), os.getenv("BITHUMB_SECRET_KEY_V1")),
            gateio1_reader=Gateio_Reader.Gateio_Reader('gateio1_mobile', os.getenv("GATEIO_API_KEY"), os.getenv("GATEIO_SECRET_KEY")),
            gateio2_reader=Gateio_Reader.Gateio_Reader('gateio2_mobile', os.getenv("GATEIO_API_KEY_2ND"), os.getenv("GATEIO_SECRET_KEY_2ND"))
        )


    symbol_name = None
    for reader_name, reader in CW.readers.items():
        if reader is None:
            continue
        print(f"Loading assets from {reader_name}...")
        assets = reader.load_assets()
        #assets = reader.load_symbol_assets(symbol_name)
        CW.assets = merge_coinasset_dicts(CW.assets, assets)

    
    
    
    # Laod assets from each reader

    #CW.readers['binance'].get_trade_history(CW.assets)
    #CW.readers['gateio1'].get_trade_history(CW.assets)
    #CW.readers['gateio2'].get_trade_history(CW.assets)
    #CW.readers['bithumb'].get_trade_history(CW.assets)


    CW.readers['binance'].get_trade_history(CW.assets, symbol_name)

    CW.readers['gateio1'].get_trade_history(CW.assets, symbol_name)
    CW.readers['gateio2'].get_trade_history(CW.assets, symbol_name)
    CW.readers['bithumb'].get_trade_history(CW.assets, symbol_name)

    #print("All assets loaded and merged successfully.")
    for asset in CW.assets.values():
        asset.get_avg_price()
        print(asset)
    
    #CW.readers['gateio'].get_trade_history_from_dual_investment(CW.assets)
    return CW




def print_loaded_assets(assets):
    print("Assets loaded successfully.")
    # Here you can add more detailed logging or processing of the loaded assets if needed
    # For example, you can print the total number of assets loaded
    for symbol, asset in assets.items():
        print(f"{asset}")

def merge_coinasset_dicts(dict1, dict2):
    result = dict(dict1)  # dict1을 복사
    for symbol, asset in dict2.items():
        #print(f"Merging asset: {symbol}, Amount: {asset.amount}, USDT Value: {asset.usdt_value}")
        if symbol in result:
            result[symbol].amount += asset.amount
            result[symbol].usdt_value += asset.usdt_value
        else:
            result[symbol] = asset
    return result

def get_stable_asset_list(COIN_WALLET_ASSETS):
    stable_assets = []
    for asset in COIN_WALLET_ASSETS.values():
        if asset.symbol in STABLE_ASSET:
            if hasattr(asset, "MainCoin") and asset.MainCoin == asset.symbol:
                stable_assets.insert(0, asset)  # 맨 앞에 추가
            else:
                stable_assets.append(asset)
    return stable_assets


def calculate_ratios(CW):
    for Coinasset in CW.assets.values():
        Coinasset.ratio = Coinasset.usdt_value / CW.Total_Assets_value * 100
        if Coinasset.IsStable:
            Coinasset.ratio_nonstable = 0.0
        else:
            Coinasset.ratio_nonstable = Coinasset.usdt_value / (CW.Total_Assets_value - CW.Stable_Assets_value) * 100
        if Coinasset.NeedCluster:
            if Coinasset.MainCoin == Coinasset.symbol:
                clustered_assets = [asset for asset in CW.assets.values() if asset.symbol in Coinasset.Cluster]
                total_clustered_value = sum(asset.usdt_value for asset in clustered_assets)
                Coinasset.ratio_clustered = total_clustered_value / CW.Total_Assets_value * 100
                if not Coinasset.IsStable:
                    Coinasset.ratio_clustered_nonstable = total_clustered_value / (CW.Total_Assets_value - CW.Stable_Assets_value) * 100
                else:
                    Coinasset.ratio_clustered_nonstable = 0.0
            else:
                Coinasset.ratio_clustered = 0.0
                Coinasset.ratio_clustered_nonstable = 0.0
        else:
            Coinasset.ratio_clustered = Coinasset.ratio
            Coinasset.ratio_clustered_nonstable = Coinasset.ratio_nonstable


if __name__ == "__main__":
    main()