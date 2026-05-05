import os
from dotenv import load_dotenv
import Bithumb_Reader
from datetime import datetime

load_dotenv()
api_key = os.getenv("BITHUMB_API_KEY")
api_secret = os.getenv("BITHUMB_SECRET_KEY")

bithumb = Bithumb_Reader.Bithumb_Reader('bithumb', api_key, api_secret)

# 입금/출금 내역 모두 가져오기
deposits = bithumb.bithumb_request("/v1/deposits/krw")
withdrawals = bithumb.bithumb_request("/v1/withdraws/krw")

events = []

for item in deposits:
    if item.get('state') != 'CANCELLED':
        events.append({
            'type': '입금',
            'amount': float(item.get('amount', 0)),
            'created_at': item.get('created_at', ''),
            'desc': f"입금자명: {item.get('sender', 'N/A')}, 상태: {item.get('state', 'N/A')}"
        })

for item in withdrawals:
    if item.get('state') == 'DONE':
        events.append({
            'type': '출금',
            'amount': -float(item.get('amount', 0)),
            'created_at': item.get('created_at', ''),
            'desc': f"수수료: {item.get('fee', 'N/A')}, 출금계좌: {item.get('bank', 'N/A')}, 상태: {item.get('state', 'N/A')}"
        })

# 시간순 정렬
def parse_time(x):
    try:
        return datetime.fromisoformat(x['created_at'])
    except Exception:
        return datetime.min

events.sort(key=parse_time)

# 잔고 변화 출력
balance = 0
print("=== KRW 입출금 시간순 내역 및 잔고 변화 ===")
for event in events:
    balance += event['amount']
    print(f"{event['created_at']} | {event['type']} | 금액: {abs(event['amount']):,.0f} | 잔고: {balance:,.0f} | {event['desc']}")