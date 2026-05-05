import os
import re
import json

def rename_trade_files(directory):
    for filename in os.listdir(directory):
        # 패턴: prefix_trades_symbol_USDT.json
        match = re.match(r"(.+_trades_.+)_USDT(\.json)$", filename)
        if match:
            new_filename = match.group(1) + "USDT" + match.group(2)
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                print(f"✅ Renamed: {filename} ➝ {new_filename}")
            else:
                print(f"⚠️ Skipped (already exists): {new_filename}")
        else:
            print(f"⏭ No change needed: {filename}")

def rename_files_in_history(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 첫 번째 key만 변환
            keys = list(data.keys())
            if keys:
                old_key = keys[0]
                if "_" in old_key:
                    new_key = old_key.replace("_", "")
                    data[new_key] = data.pop(old_key)
                    print(f"{filename}: {old_key} → {new_key}")

            # 다시 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)



# 사용 예시
rename_trade_files("history")
rename_files_in_history("history")