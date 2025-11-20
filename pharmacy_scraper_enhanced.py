#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
厚生労働省 医療情報ネット 薬局データスクレイパー (改善版)

新機能:
- ロギング機能（ファイル出力）
- 進捗率表示
- 実行時間計測
- 統計情報の出力
- タイムアウト設定の統一
- エラー詳細情報
"""
import time
import csv
import os
import json
import re
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
# 設定
# ============================================================
BASE_URL = "https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize"
OUTPUT_DIR = "pharmacy_data_enhanced"
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "scraper.log")
STATS_FILE = os.path.join(OUTPUT_DIR, "statistics.json")

# タイムアウト設定（統一）
WAIT_TIMEOUT = 15
ELEMENT_TIMEOUT = 10
PAGE_LOAD_TIMEOUT = 20

# 待機時間
MIN_WAIT = 2.0
MAX_WAIT = 4.0

# リトライ設定
MAX_RETRIES = 3

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

# ============================================================
# ログ設定
# ============================================================
def setup_logging():
    """ログ設定の初期化"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ロガーの作成
    logger = logging.getLogger('PharmacyScraper')
    logger.setLevel(logging.DEBUG)
    
    # ファイルハンドラ
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # コンソールハンドラ
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # フォーマッター
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

logger = setup_logging()

# ============================================================
# 統計情報管理
# ============================================================
class Statistics:
    """統計情報を管理するクラス"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_pharmacies = 0
        self.total_with_data = 0
        self.total_without_data = 0
        self.errors = 0
        self.skipped = 0
        self.prefecture_stats = {}
    
    def add_pharmacy(self, pref_code, has_data=True):
        """薬局データを記録"""
        self.total_pharmacies += 1
        if has_data:
            self.total_with_data += 1
        else:
            self.total_without_data += 1
        
        if pref_code not in self.prefecture_stats:
            self.prefecture_stats[pref_code] = {'total': 0, 'with_data': 0}
        
        self.prefecture_stats[pref_code]['total'] += 1
        if has_data:
            self.prefecture_stats[pref_code]['with_data'] += 1
    
    def add_error(self):
        """エラー数を記録"""
        self.errors += 1
    
    def add_skip(self):
        """スキップ数を記録"""
        self.skipped += 1
    
    def save(self):
        """統計情報を保存"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        stats_data = {
            'execution_time_seconds': elapsed,
            'execution_time_human': str(datetime.now() - self.start_time),
            'total_pharmacies': self.total_pharmacies,
            'total_with_prescription_data': self.total_with_data,
            'total_without_prescription_data': self.total_without_data,
            'errors': self.errors,
            'skipped_duplicates': self.skipped,
            'prefecture_stats': self.prefecture_stats,
            'completed_at': datetime.now().isoformat()
        }
        
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"統計情報を保存しました: {STATS_FILE}")
    
    def print_summary(self):
        """統計サマリーを表示"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*60)
        print("📊 実行統計")
        print("="*60)
        print(f"実行時間: {elapsed/3600:.2f}時間")
        print(f"総薬局数: {self.total_pharmacies:,}件")
        print(f"  └ 処方箋数データあり: {self.total_with_data:,}件")
        print(f"  └ 処方箋数データなし: {self.total_without_data:,}件")
        print(f"エラー数: {self.errors}件")
        print(f"スキップ数: {self.skipped}件")
        print("="*60)

stats = Statistics()

# ============================================================
# ドライバー設定
# ============================================================
def setup_driver():
    """Webドライバーの設定"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
    options.add_argument("--log-level=3")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    logger.info("Webドライバーを初期化しました")
    return driver

# ============================================================
# ユーティリティ関数
# ============================================================
def get_existing_ids(filepath):
    """既存のCSVから薬局IDを取得"""
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
            if row_count == 0:
                return set()
    except Exception as e:
        logger.error(f"既存IDの読み込みエラー: {filepath} - {e}")
    return ids

def is_csv_valid(filepath):
    """CSVファイルが有効か確認"""
    if not os.path.exists(filepath):
        return False
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return len(f.readlines()) > 1
    except:
        return False

def random_sleep():
    """ランダムな待機"""
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))

def append_to_csv(filename, data_dict):
    """CSVにデータを追記"""
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['id', 'name', 'address', 'prescription_count', 'prefecture', 'scraped_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)

# ============================================================
# スクレイピング関数
# ============================================================
def safe_set_value(driver, element_id, value):
    """リトライ機能付きの値セット"""
    for i in range(MAX_RETRIES):
        try:
            element = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
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
            logger.warning(f"input設定再試行中({i+1}/{MAX_RETRIES}): {e}")
            time.sleep(1)
    return False

def extract_prescription_count(driver, detail_url, pharmacy_id, pharmacy_name):
    """処方箋数を抽出"""
    try:
        driver.get(detail_url)
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        try:
            target = driver.find_element(
                By.XPATH, 
                "//th[contains(text(), '総取扱処方箋数')]/following-sibling::td"
            )
            text = target.text.strip()
            match = re.search(r'(\d+(?:,\d+)?)', text)
            if match:
                return match.group(1)
        except NoSuchElementException:
            logger.debug(f"処方箋数なし: {pharmacy_id} - {pharmacy_name}")
    except Exception as e:
        logger.error(f"詳細ページエラー: {pharmacy_id} - {pharmacy_name} - {e}")
        stats.add_error()
    return ""

def setup_search_conditions(driver, pref_code, pref_name):
    """検索条件の設定"""
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(BASE_URL)
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "todofukenCd"))
            )
            
            if not safe_set_value(driver, "todofukenCd", pref_code):
                raise Exception("都道府県セット失敗")
            time.sleep(1)
            
            if not safe_set_value(driver, "iryoKikanShubetsuCd", "5"):
                raise Exception("医療機関種別セット失敗")
            time.sleep(1)
            
            btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '検索')]"))
            )
            driver.execute_script("arguments[0].click();", btn)
            
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result-count"))
            )
            
            logger.info(f"{pref_name}: 検索条件設定成功")
            return True
            
        except Exception as e:
            logger.warning(f"{pref_name}: 検索条件設定エラー (試行 {attempt+1}/{MAX_RETRIES}) - {e}")
            time.sleep(3)
    
    logger.error(f"{pref_name}: 検索条件設定に失敗しました")
    return False

def scrape_prefecture(driver, pref_code, pref_name, progress_data):
    """都道府県のデータを取得"""
    logger.info(f"{'='*60}")
    logger.info(f"🏥 {pref_name} ({pref_code}) 開始")
    logger.info(f"{'='*60}")
    
    csv_filename = os.path.join(OUTPUT_DIR, f"{pref_code}_{pref_name}_prescription.csv")
    
    # 完了チェック
    if not is_csv_valid(csv_filename) and progress_data.get(pref_code) == "DONE":
        logger.info(f"{pref_name}: 完了記録がありますが、データがないため再取得します")
    elif progress_data.get(pref_code) == "DONE":
        logger.info(f"{pref_name}: データ取得済みのためスキップします")
        return
    
    existing_ids = get_existing_ids(csv_filename)
    if existing_ids:
        logger.info(f"{pref_name}: 既存データ {len(existing_ids)}件 (スキップします)")
    
    # 検索画面の設定
    if not setup_search_conditions(driver, pref_code, pref_name):
        logger.error(f"{pref_name}: 検索条件の設定に失敗しました。スキップします。")
        return
    
    page_num = 1
    prefecture_count = 0
    
    while True:
        logger.info(f"{pref_name}: ページ {page_num} 処理中...")
        
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
            logger.error(f"{pref_name}: リスト取得エラー - {e}")
            break
        
        if not pharmacy_list:
            logger.warning(f"{pref_name}: データなし、または取得終了")
            break
        
        current_list_url = driver.current_url
        
        for p in pharmacy_list:
            if p['id'] in existing_ids:
                stats.add_skip()
                continue
            
            count = extract_prescription_count(driver, p['url'], p['id'], p['name'])
            
            if count:
                logger.info(f"{pref_name}: {p['name'][:20]}... ✅ {count}件")
                save_data = {
                    'id': p['id'],
                    'name': p['name'],
                    'address': p['address'],
                    'prescription_count': count,
                    'prefecture': pref_name,
                    'scraped_at': datetime.now().isoformat()
                }
                append_to_csv(csv_filename, save_data)
                existing_ids.add(p['id'])
                stats.add_pharmacy(pref_code, has_data=True)
                prefecture_count += 1
            else:
                logger.debug(f"{pref_name}: {p['name'][:20]}... ー")
                stats.add_pharmacy(pref_code, has_data=False)
            
            random_sleep()
        
        # 次ページへ
        driver.get(current_list_url)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result-table"))
            )
            
            next_links = driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
            if not next_links:
                break
            
            parent_li = next_links[0].find_element(By.XPATH, "..")
            if "disabled" in parent_li.get_attribute("class"):
                break
            
            driver.execute_script("arguments[0].click();", next_links[0])
            time.sleep(3)
            page_num += 1
            
        except Exception as e:
            logger.info(f"{pref_name}: ページ送り終了 - {e}")
            break
    
    # 完了記録
    progress_data[pref_code] = "DONE"
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"{pref_name}: 完了 - 取得数 {prefecture_count}件")

# ============================================================
# メイン処理
# ============================================================
def calculate_progress(progress_data):
    """進捗率を計算"""
    completed = sum(1 for v in progress_data.values() if v == "DONE")
    total = len(PREFECTURES)
    percentage = (completed / total) * 100
    return completed, total, percentage

def main():
    """メイン処理"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logger.info("="*60)
    logger.info("🏥 厚生労働省 医療情報ネット 薬局データスクレイパー (改善版)")
    logger.info("="*60)
    
    driver = setup_driver()
    
    # 進捗読み込み
    progress = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        completed, total, percentage = calculate_progress(progress)
        logger.info(f"📊 進捗状況: {completed}/{total}都道府県完了 ({percentage:.1f}%)")
    
    try:
        for code, name in PREFECTURES.items():
            scrape_prefecture(driver, code, name, progress)
            
            # 進捗表示
            completed, total, percentage = calculate_progress(progress)
            logger.info(f"📊 全体進捗: {completed}/{total}都道府県完了 ({percentage:.1f}%)")
        
        logger.info("✅ 全都道府県の処理が完了しました！")
        
    except KeyboardInterrupt:
        logger.warning("⚠️ ユーザーによる中断")
    except Exception as e:
        logger.error(f"❌ エラー: {e}", exc_info=True)
    finally:
        driver.quit()
        stats.save()
        stats.print_summary()
        logger.info("ブラウザを終了しました")

if __name__ == "__main__":
    main()
