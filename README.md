# cryptonote_renewal

여러 거래소(Binance, Bithumb, Gate.io)와 개인지갑 자산을 합산해 USDT 기준으로 분석하고, 엑셀/HTML 리포트를 생성하는 Python 프로젝트입니다.

## 1) 빠른 실행

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --output-format both
```

- 결과물: `assets.xlsx`, `assets.html`
- 테스트성 실행: `python main_test.py`, `python main_test_2.py`
- ROI 리포트: `python roi_report.py --skip-fetch`
  - `app.py` 대시보드는 `roi_report.csv`가 있으면 ROI 섹션에 표시합니다.
  - ROI 생성은 거래소 로딩 실패가 하나라도 있으면 기본적으로 중단됩니다.

## 2) 환경 변수(.env) 핵심

`main.py`에서 아래 키를 읽습니다.

- Binance: `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`
- Bithumb: `BITHUMB_API_KEY`, `BITHUMB_SECRET_KEY`
- Gate.io(1): `GATEIO_API_KEY`, `GATEIO_SECRET_KEY`
- Gate.io(2): `GATEIO_API_KEY_2ND`, `GATEIO_SECRET_KEY_2ND`
- Gate.io(1) 활성화 여부: `GATEIO1_ENABLED` (기본값 `false`)
- 개인지갑 파일: `PERSONAL_WALLET_FILE` (기본값 `personal_wallet_assets.json`)
- Web3 지갑 RPC(선택): `WEB3_ETHEREUM_RPC_URL`, `WEB3_BSC_RPC_URL`, `WEB3_POLYGON_RPC_URL`, `WEB3_ARBITRUM_RPC_URL`, `WEB3_BASE_RPC_URL`
- Bitcoin explorer API(선택): `BITCOIN_EXPLORER_API_URL` (기본값 `https://blockstream.info/api`)
- Ethereum explorer API(선택): `ETHEREUM_EXPLORER_API_URL`, `ETHPLORER_API_KEY` (기본값 `freekey`)

## 2-1) 개인 Web3 지갑 자산 조회

`personal_wallet_assets.json`에 `web3_wallets`를 추가하면 private Web3 wallet 주소의 온체인 잔액도 합산됩니다.

주소만으로 토큰을 자동 조회하려면 Binance Web3 조회 방식을 사용합니다. 현재 Binance Web3 조회는 `bsc`, `base`, `solana`를 지원합니다.

```json
{
  "assets": [
    { "symbol": "BTC", "amount": 0.015 }
  ],
  "web3_wallets": [
    {
      "name": "my-bsc-wallet",
      "enabled": true,
      "provider": "binance_web3",
      "chain": "bsc",
      "address": "0x내지갑주소"
    }
  ]
}
```

EVM RPC 방식도 계속 사용할 수 있습니다. 이 방식은 `ethereum`, `bsc`, `polygon`, `arbitrum`, `base`를 지원하지만 ERC-20 토큰은 `tokens`에 컨트랙트 주소를 등록해야 합니다.

Bitcoin SegWit 주소는 `bitcoin_explorer` provider로 가져올 수 있습니다. `bc1...` 네이티브 SegWit과 `3...` P2SH-SegWit 주소를 지원합니다.

```json
{
  "web3_wallets": [
    {
      "name": "my-bitcoin-segwit-wallet",
      "enabled": true,
      "provider": "bitcoin_explorer",
      "chain": "bitcoin",
      "address": "bc1q내비트코인주소"
    }
  ]
}
```

Ethereum 주소에서 ETH와 ERC-20 토큰을 contract 입력 없이 자동 조회하려면 `ethereum_explorer` provider를 사용합니다. 기본값은 Ethplorer `freekey`이며, 사용량이 많으면 `ETHPLORER_API_KEY`를 별도로 설정하세요.

```json
{
  "web3_wallets": [
    {
      "name": "my-ethereum-explorer-wallet",
      "enabled": true,
      "provider": "ethereum_explorer",
      "chain": "ethereum",
      "address": "0x내이더리움주소"
    }
  ]
}
```

```json
{
  "assets": [
    { "symbol": "BTC", "amount": 0.015 }
  ],
  "web3_wallets": [
    {
      "name": "my-ethereum-wallet",
      "enabled": true,
      "chain": "ethereum",
      "address": "0x내지갑주소",
      "include_native": true,
      "tokens": [
        {
          "symbol": "USDT",
          "contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
          "decimals": 6
        }
      ]
    }
  ]
}
```

- `include_native: true`이면 해당 체인의 네이티브 코인(예: Ethereum/Base/Arbitrum은 `ETH`, BSC는 `BNB`)을 조회합니다.
- ERC-20 토큰은 `tokens`에 컨트랙트 주소를 등록한 것만 조회합니다.
- `rpc_url`을 지갑 항목에 직접 넣거나 `.env`의 `WEB3_*_RPC_URL`로 커스텀 RPC를 지정할 수 있습니다.

## 3) 파일별 역할 / 메서드 / 수정 포인트

### `main.py` (전체 오케스트레이션)
- 역할:
  - Reader 인스턴스 생성
  - 거래소별 자산 로드 및 병합
  - 비율 계산, 수익률 계산
  - 엑셀/HTML 내보내기
- 주요 함수:
  - `main(...)`
  - `merge_coinasset_dicts(dict1, dict2)`
  - `calculate_ratios(CW)`
  - `calculate_benefit_ratio(cw)`
  - `export_assets_to_html(cw, filename)`
- 여기 고치면 되는 경우:
  - 출력 포맷/리포트 컬럼 변경: `export_assets_to_html`, `main`의 export 분기
  - 자산 병합 로직 변경: `merge_coinasset_dicts`
  - 비율 계산식 변경: `calculate_ratios`
  - 수익률 계산식 변경: `calculate_benefit_ratio`

### `Reader.py` (거래소 Reader 공통 베이스)
- 역할:
  - spot/earn 자산 통합 공통 처리
  - 거래내역 파일(history) 로드/저장 루프
  - 체결내역 누적(`accumulate_trade_history`) 공통 처리
- 주요 메서드:
  - `load_assets()`, `load_symbol_assets(symbol)`
  - `get_trade_history(...)`
  - `accumulate_trade_history(all_trades, Assetlist, symbol)`
  - `add_CoinAsset_to_dict(...)`
  - 추상성 메서드(서브클래스 구현 필요): `get_spot_balance`, `get_earn_balance`, `get_trade_history_from_reader`
- 여기 고치면 되는 경우:
  - 공통 체결 누적 방식(매수/매도/수수료): `accumulate_trade_history`
  - 거래내역 캐시(history) 전략: `get_trade_history`
  - 최소 자산 표시 컷오프(현재 0.1 USDT): `add_CoinAsset_to_dict`

### `CoinAsset.py` (자산 도메인 모델)
- 역할:
  - 코인 단위 상태(수량/평가금액/매수매도 누적/비율/수수료) 보관
  - 클러스터 자산(예: ETH-WBETH) 규칙 보관
- 주요 요소:
  - 상수: `CLUSTER_ASSET`, `STABLE_ASSET`
  - 클래스: `CoinAsset`
  - 메서드: `get_avg_price()`, `__repr__()`
- 여기 고치면 되는 경우:
  - 스테이블 코인 정의 변경: `STABLE_ASSET`(= `CLUSTER_ASSET` 마지막 그룹)
  - 클러스터링 기준 변경: `CLUSTER_ASSET`
  - 평균단가 계산 방식 변경: `get_avg_price`

### `CoinWallet.py` (전체 지갑 집계/엑셀 출력)
- 역할:
  - 거래소 Reader 보관
  - 전체/스테이블 자산 합산값, 입출금/수익률 상태 보관
  - 엑셀 출력
- 주요 메서드:
  - `get_temporary_assets_dict(exchange_name)`
  - `export_assets_to_excel(filename="assets.xlsx")`
- 여기 고치면 되는 경우:
  - 엑셀 시트 컬럼/요약 행 변경: `export_assets_to_excel`
  - 임시자산(수동 반영) 적용 방식 변경: `Temporary_assets`, `get_temporary_assets_dict`

### `Binance_Reader.py` (Binance 구현)
- 역할:
  - Binance spot/earn 조회
  - Binance 거래내역 조회
  - Dual Investment 체결 반영
- 주요 메서드:
  - `get_spot_balance`, `get_earn_balance`
  - `get_trade_history_from_reader`
  - `get_trade_history_from_dual_investment`
  - `get_usdt_price`
- 여기 고치면 되는 경우:
  - Binance API endpoint/파라미터 변경 대응: `binance_manual_request`, 각 조회 메서드
  - Binance 수수료/체결 판정 변경: `check_buyer`, 지표 필드(`id_indicator` 등)

### `Bithumb_Reader.py` (Bithumb 구현)
- 역할:
  - Bithumb spot/거래내역 조회
  - KRW-USDT 환율 및 KRW 입출금 집계
- 주요 메서드:
  - `get_spot_balance`, `get_trade_history_from_reader`
  - `get_KRW_Currency`, `get_USDT_KRW_at`
  - `get_KRW_deposits`, `get_KRW_withdrawals`
- 여기 고치면 되는 경우:
  - 원화 환산 로직 변경: `get_USDT_KRW_at`, `get_KRW_Currency`
  - 입출금 집계 규칙 변경: `get_KRW_deposits`, `get_KRW_withdrawals`

### `Gateio_Reader.py` (Gate.io 구현)
- 역할:
  - spot/earn/staking/auto-invest 조회
  - V4/V2 요청 래핑 및 서명 생성
  - 거래내역/자동투자 이력 반영
- 주요 메서드:
  - `get_spot_balance`, `get_earn_balance`, `get_staking_balance`
  - `get_auto_invest`, `get_auto_invest_history`
  - `get_trade_history_from_reader`, `get_trade_history_from_auto_invest`
  - `gateio_request`, `gateio_V2_request`, `generate_signature`
- 여기 고치면 되는 경우:
  - Gate.io API 버전/서명 변경 대응: `gateio_request`, `gateio_V2_request`, `generate_signature`
  - 자동투자 계산 변경: `get_trade_history_from_auto_invest`, `get_auto_invest_history`

### `PersonalWallet_Reader.py` (개인지갑 JSON 입력)
- 역할:
  - 로컬 JSON 파일 기반 자산을 Reader 인터페이스로 통합
  - 공개 시세 API(Binance/Gate/CoinGecko) fallback 조회
- 주요 메서드:
  - `load_assets`, `get_spot_balance`, `get_usdt_price`
  - `_get_binance_public_price`, `_get_gate_public_price`, `_get_coingecko_usd_price`
- 여기 고치면 되는 경우:
  - 개인지갑 JSON 포맷 변경: `load_assets`, `get_spot_balance`
  - 시세 fallback 우선순위 변경: `get_usdt_price`

### `HistoryManager.py` (거래내역 파일 관리)
- 역할: history 폴더의 JSON 읽기/쓰기/목록 조회
- 메서드:
  - `load_trades_from_file`
  - `save_trades_to_file`
  - `list_json_files`
- 여기 고치면 되는 경우:
  - 저장 경로/파일명 정책 변경
  - JSON 저장 포맷 변경

### `main_simulation.py` (시뮬레이션 리포트)
- 역할:
  - 특정 BTC 가격 가정 시 자산/비율 재계산
  - `simulation_report.html` 생성
- 주요 함수:
  - `simulate_btc_price(cw, target_btc_price)`
  - `write_simulation_html(...)`
- 여기 고치면 되는 경우:
  - 시나리오 입력 확장(ETH/SOL 가정 등): `simulate_btc_price`
  - 시뮬레이션 출력 UI 변경: `write_simulation_html`

### `main_test.py`, `main_test_2.py` (스크립트형 검증)
- 역할:
  - 로직 점검용 수동 실행 스크립트
  - 파싱/계산 확인
- 여기 고치면 되는 경우:
  - 새 로직 검증 케이스 추가 시 우선 여기에 빠르게 추가

### `GateioV2API.py` (Gate V2 WebSocket 보조)
- 역할: V2 요청 서명/요청 구조 보조
- 주요 요소:
  - `get_sign`, `GateWs.gateGet`, `GateWs.gateRequest`
- 여기 고치면 되는 경우:
  - V2 WS 인증 규격 바뀔 때

### `renamefiles.py` (히스토리 파일명 정리 유틸)
- 역할: 거래내역 JSON 파일명 일괄 정리
- 메서드:
  - `rename_trade_files`
  - `rename_files_in_history`
- 여기 고치면 되는 경우:
  - 파일명 규칙이 바뀔 때

## 4) “무엇을 고치고 싶은지”별 빠른 가이드

- 거래소 하나만 연동 추가/변경:
  - 새 `XXX_Reader.py` 작성(또는 기존 Reader 수정)
  - `Reader` 인터페이스 메서드 구현
  - `main.py`에서 Reader 주입

- 수익률 계산식 변경:
  - `main.py`의 `calculate_benefit_ratio`
  - 엑셀 표시도 맞추려면 `CoinWallet.export_assets_to_excel`의 Benefit 행 동시 수정

- 스테이블/클러스터 기준 변경:
  - `CoinAsset.py`의 `CLUSTER_ASSET`, `STABLE_ASSET`

- 리포트 형태(엑셀/HTML) 변경:
  - 엑셀: `CoinWallet.py`의 `export_assets_to_excel`
  - HTML: `main.py`의 `export_assets_to_html`

- 체결 누적 로직(평단/수수료 처리) 변경:
  - 공통: `Reader.py`의 `accumulate_trade_history`
  - 거래소 특이사항: 각 `*_Reader.py`의 `check_buyer`, 필드 지표 설정

## 5) 데이터/보안 주의

- `.env`, `personal_wallet_assets.json`, `history/*.json`, `assets.xlsx`에는 민감정보가 포함될 수 있습니다.
- 외부 공유 전에 계정/거래 관련 데이터는 반드시 마스킹하세요.
