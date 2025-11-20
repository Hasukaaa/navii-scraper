#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import csv
import os
import json
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# --- 設定 ---
BASE_URL = "https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize"
OUTPUT_DIR = "pharmacy_data_final"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress_v5.json")
MIN_WAIT = 2.0  # 待機時間を少し延長
MAX_WAIT = 4.0

PREFECTURES = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県", "05": "秋田県",
    "06": "山形県", "07": "福島県", "08": "茨城県", "09": "栃木県", "10": "群馬県",
    "11": "埼玉県", "12": "千葉県", "13": "東京都", "14": "神奈川県", "15": "新潟県",
    "16": "富山県", "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県", "25": "滋賀県",
    "26": "京都府", "27": "大阪府", "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
    "31": "鳥取県", "32": "島根県", "33": "岡山県", "34": "広島県", "35": "山口県",
    "36": "徳島県", "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県", "45": "宮崎県",
    "46": "鹿児島県", "47": "沖縄県"
}

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
    options.add_argument("--log-level=3")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_existing_ids(filepath):
    if not os.path.exists(filepath):
        return set()
    ids = set()
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row_count = 0
            for row in reader:
                row_count += 1
                if row.get('id'):
                    ids.add(row['id'])
            # ファイルはあるが中身がヘッダーしかない場合は削除して再取得させる
            if row_count == 0:
                return set()
    except Exception:
        pass
    return ids

def is_csv_valid(filepath):
    """CSVファイルが存在し、かつデータ行が含まれているか確認"""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            # ヘッダー以外にデータがあるか読む
            return len(f.readlines()) > 1 
    except:
        return False

def random_sleep():
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))

def safe_set_value(driver, element_id, value):
    """リトライ機能付きの値セット"""
    for i in range(3): # 3回リトライ
        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, element, value)
            return True
        except (StaleElementReferenceException, TimeoutException):
            time.sleep(1)
            continue
        except Exception as e:
            print(f"    ⚠️ input設定再試行中({i+1}/3): {e}")
            time.sleep(1)
    return False

def extract_prescription_count(driver, detail_url):
    try:
        driver.get(detail_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        try:
            target = driver.find_element(By.XPATH, "//th[contains(text(), '総取扱処方箋数')]/following-sibling::td")
            text = target.text.strip()
            match = re.search(r'(\d+(?:,\d+)?)', text)
            if match:
                return match.group(1)
        except NoSuchElementException:
            pass
    except Exception:
        pass
    return ""

def append_to_csv(filename, data_dict):
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'address', 'prescription_count'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)

def setup_search_conditions(driver, pref_code, pref_name):
    """検索条件の設定（リトライロジック込み）"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            driver.get(BASE_URL)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "todofukenCd")))
            
            # 都道府県セット
            if not safe_set_value(driver, "todofukenCd", pref_code):
                raise Exception("都道府県セット失敗")
            time.sleep(1)

            # 医療機関種別セット
            if not safe_set_value(driver, "iryoKikanShubetsuCd", "5"):
                raise Exception("医療機関種別セット失敗")
            time.sleep(1)

            # 検索ボタンクリック
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '検索')]"))
            )
            driver.execute_script("arguments[0].click();", btn)
            
            # 成功確認
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "result-count")))
            return True

        except Exception as e:
            print(f"  ⚠️ 検索条件設定エラー (試行 {attempt+1}/{max_retries}): ページをリロードして再試行します...")
            time.sleep(3)
    
    return False

def scrape_prefecture(driver, pref_code, pref_name, progress_data):
    print(f"\n{'='*60}")
    print(f"🏥 {pref_name} ({pref_code}) 開始")
    print(f"{'='*60}")
    
    csv_filename = os.path.join(OUTPUT_DIR, f"{pref_code}_{pref_name}_prescription.csv")
    
    # CSVファイルの実在チェック（データがない場合はJSONの記録を無視して実行）
    if not is_csv_valid(csv_filename) and progress_data.get(pref_code) == "DONE":
        print(f"ℹ️  {pref_name}は完了記録がありますが、データがないため再取得します。")
    elif progress_data.get(pref_code) == "DONE":
        print(f"🎉 {pref_name} はデータ取得済みのためスキップします。")
        return

    existing_ids = get_existing_ids(csv_filename)
    if existing_ids:
        print(f"📂 既存データ: {len(existing_ids)}件 (これらはスキップします)")

    # 検索画面の設定（リトライ機能付き）
    if not setup_search_conditions(driver, pref_code, pref_name):
        print(f"❌ {pref_name}: 検索条件の設定に繰り返し失敗しました。スキップします。")
        return

    # ページネーション処理
    page_num = 1
    while True:
        print(f"\n📄 ページ {page_num} 処理中...")
        
        pharmacy_list = []
        try:
            rows = driver.find_elements(By.XPATH, "//table[contains(@class, 'result-table')]/tbody/tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 3:
                    p_id = cols[0].text.strip()
                    p_name = cols[1].text.strip()
                    p_addr = cols[2].text.strip()
                    try:
                        link = cols[1].find_element(By.TAG_NAME, "a").get_attribute("href")
                        pharmacy_list.append({
                            "id": p_id, "name": p_name, "address": p_addr, "url": link
                        })
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ リスト取得エラー: {e}")
            break

        if not pharmacy_list:
            print("⚠️ データなし、または取得終了")
            break

        current_list_url = driver.current_url

        processed_in_page = 0
        for p in pharmacy_list:
            if p['id'] in existing_ids:
                continue
            
            print(f"   🔍 {p['name'][:15]}... ", end="", flush=True)
            count = extract_prescription_count(driver, p['url'])
            
            if count:
                print(f"✅ {count}件")
                save_data = {
                    'id': p['id'], 'name': p['name'], 'address': p['address'], 'prescription_count': count
                }
                append_to_csv(csv_filename, save_data)
                existing_ids.add(p['id'])
            else:
                print("ー")
            
            processed_in_page += 1
            random_sleep()

        # リストページに戻る
        driver.get(current_list_url)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "result-table")))
            
            next_links = driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
            if not next_links:
                break
            
            parent_li = next_links[0].find_element(By.XPATH, "..")
            if "disabled" in parent_li.get_attribute("class"):
                break
                
            driver.execute_script("arguments[0].click();", next_links[0])
            time.sleep(3) # ページ遷移待ち時間を延長
            page_num += 1
            
        except Exception as e:
            print(f"⚠️ ページ送り終了: {e}")
            break
    
    # 完了記録（正常にループを抜けた場合のみ）
    progress_data[pref_code] = "DONE"
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = setup_driver()
    
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)

    try:
        for code, name in PREFECTURES.items():
            scrape_prefecture(driver, code, name, progress)
            
    except KeyboardInterrupt:
        print("\n⚠️ 中断しました")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()