import os
import json

def load_trades_from_file(currency_pair, filename):
    filepath = os.path.join("history", filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(currency_pair, [])
    return []

def save_trades_to_file(currency_pair, filename, trades):
    os.makedirs("history", exist_ok=True)  # 폴더가 없으면 생성
    filepath = os.path.join("history", filename)
    data = {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[currency_pair] = trades
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def list_json_files(folder_path, readername=None):
    # 지정한 폴더 내의 모든 .json 파일 이름 출력
    filelists = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.json'):
            if readername is None or readername in filename:
                filelists.append(filename)
    return filelists

