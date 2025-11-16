import sys
import csv
import ipaddress
import re

SUPERNET = ipaddress.ip_network('2a0f:1cc0::/29')

# 驗證國家代碼 (ISO 3166-1 alpha-2)
COUNTRY_CODE_REGEX = re.compile(r'^[A-Z]{2}$')
# 驗證區域代碼 (ISO 3166-2, e.g., US-CA, JP-13)
REGION_CODE_REGEX = re.compile(r'^[A-Z]{2}-[A-Za-z0-9]{1,3}$')

# 標記是否有任何錯誤
validation_failed = False

# 從命令行參數獲取文件列表
files_to_check = sys.argv[1:]

if not files_to_check:
    print("No relevant .csv files changed in 'client_feeds/'. Skipping.")
    sys.exit(0)

for filepath in files_to_check:
    print(f"--- Validating file: {filepath} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 使用 csv.reader 處理，以正確處理帶引號的字段
            reader = csv.reader(f)
            
            for i, row in enumerate(reader):
                linenum = i + 1
                
                # 跳過空行或註解行
                if not row or (row[0].strip().startswith('#')):
                    continue

                # --- [!! 新增 !!] ---
                # 處理行尾可能多出的空字段 (例如由行尾逗號 'Tokyo,' 引起)
                # 這會將 ['...', 'Tokyo', ''] 變為 ['...', 'Tokyo']
                if len(row) > 0 and row[-1] == '':
                    row.pop()
                # ---------------------

                # 1. 檢查列數 (geofeed 至少 2 列，最多 4 列)
                if not (2 <= len(row) <= 4):
                    print(f"  ERROR: {filepath}:{linenum}: Invalid column count ({len(row)}). Must be 2, 3, or 4.")
                    validation_failed = True
                    continue
                
                ip_prefix = row[0].strip()
                country_code = row[1].strip()

                # 2. 驗證 IP 前綴
                try:
                    network = ipaddress.ip_network(ip_prefix)
                except ValueError as e:
                    print(f"  ERROR: {filepath}:{linenum}: Invalid IP prefix '{ip_prefix}'. Details: {e}")
                    validation_failed = True
                    continue
                
                # 3. 檢查 IP 是否在允許的超網內
                if not network.subnet_of(SUPERNET):
                    print(f"  ERROR: {filepath}:{linenum}: IP prefix '{ip_prefix}' is NOT within the allowed range {SUPERNET}.")
                    validation_failed = True
                
                # 4. 驗證國家代碼格式
                if not COUNTRY_CODE_REGEX.match(country_code):
                    print(f"  ERROR: {filepath}:{linenum}: Invalid country code format '{country_code}'. Must be 2 uppercase letters (e.g., US, JP).")
                    validation_failed = True

                # --- [!! 新增 !!] ---
                # 5. 驗證區域代碼 (如果存在)
                if len(row) >= 3 and row[2].strip(): # 如果第3列存在且不為空
                    region_code = row[2].strip()
                    if not REGION_CODE_REGEX.match(region_code):
                        print(f"  ERROR: {filepath}:{linenum}: Invalid region code format '{region_code}'. Must match ISO 3166-2 (e.g., US-CA, JP-13).")
                        validation_failed = True
                
                # 6. (可選) 檢查城市名稱 (如果存在)
                # 城市名稱通常是自由文本，我們只做基本檢查
                if len(row) == 4 and row[3].strip():
                    city_name = row[3].strip()
                    if len(city_name) > 64: # 檢查一下合理的長度
                        print(f"  WARN: {filepath}:{linenum}: City name '{city_name}' seems very long. Is this correct?")
                
                # 7. (RFC 8805 推薦) 檢查是否有城市但沒有區域
                if len(row) == 4 and row[3].strip() and (len(row) < 3 or not row[2].strip()):
                    print(f"  WARN: {filepath}:{linenum}: City '{row[3]}' is specified, but region (column 3) is empty. This is discouraged by RFC 8805/9092.")
                # ---------------------

    except FileNotFoundError:
        print(f"  INFO: File {filepath} not found (likely deleted in this PR). Skipping.")
    except Exception as e:
        print(f"  FATAL: Could not process file {filepath}. Error: {e}")
        validation_failed = True

# --- 總結 ---
if validation_failed:
    print("\nValidation FAILED. See errors above.")
    sys.exit(1) # 退出代碼 1，使 GitHub Action 失敗
else:
    print("\nAll changed geofeed files validated SUCCESSFULLY.")
    sys.exit(0) # 退出代碼 0，使 GitHub Action 成功
