#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
厚生労働省 医療情報ネット 薬局データスクレイパー
メインエントリポイント
"""

import os
import time
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import (
    BASE_URL,
    OUTPUT_DIR,
    PREFECTURES,
    LOG_FILE,
    LOG_LEVEL,
    LOG_FORMAT,
    WAIT_TIMEOUT
)
from .browser import setup_driver, setup_search_conditions
from .parser import (
    extract_prescription_count,
    extract_pharmacy_list,
    has_next_page,
    go_to_next_page
)
from .utils import (
    setup_logging,
    random_sleep,
    append_to_csv,
    get_existing_ids,
    is_csv_valid
)
from .progress_manager import ProgressManager, Statistics

# ロガー初期化
logger = None


def scrape_prefecture(driver, pref_code, pref_name, progress_manager, statistics):
    """
    都道府県のデータを取得

    Args:
        driver: Seleniumドライバー
        pref_code (str): 都道府県コード
        pref_name (str): 都道府県名
        progress_manager (ProgressManager): 進捗管理オブジェクト
        statistics (Statistics): 統計管理オブジェクト
    """
    logger.info(f"{'='*60}")
    logger.info(f"🏥 {pref_name} ({pref_code}) 開始")
    logger.info(f"{'='*60}")

    csv_filename = os.path.join(OUTPUT_DIR, f"{pref_code}_{pref_name}_prescription.csv")

    # 完了チェック
    if not is_csv_valid(csv_filename) and progress_manager.is_done(pref_code):
        logger.info(f"{pref_name}: 完了記録がありますが、データがないため再取得します")
    elif progress_manager.is_done(pref_code):
        logger.info(f"{pref_name}: データ取得済みのためスキップします")
        return

    # 既存IDの読み込み
    existing_ids = get_existing_ids(csv_filename)
    if existing_ids:
        logger.info(f"{pref_name}: 既存データ {len(existing_ids)}件 (スキップします)")

    # 検索条件の設定
    if not setup_search_conditions(driver, pref_code, pref_name, BASE_URL):
        logger.error(f"{pref_name}: 検索条件の設定に失敗しました。スキップします。")
        return

    page_num = 1
    prefecture_count = 0

    # ページネーション処理
    while True:
        logger.info(f"{pref_name}: ページ {page_num} 処理中...")

        # 薬局リストを取得
        pharmacy_list = extract_pharmacy_list(driver)

        if not pharmacy_list:
            logger.warning(f"{pref_name}: データなし、または取得終了")
            break

        # 現在のURLを保存（詳細ページから戻るため）
        current_list_url = driver.current_url

        # 各薬局の処理
        for pharmacy in pharmacy_list:
            # 既存IDはスキップ
            if pharmacy['id'] in existing_ids:
                statistics.add_skip()
                continue

            # 処方箋数を取得
            count = extract_prescription_count(
                driver,
                pharmacy['url'],
                pharmacy['id'],
                pharmacy['name']
            )

            if count:
                logger.info(f"{pref_name}: {pharmacy['name'][:20]}... ✅ {count}件")
                save_data = {
                    'id': pharmacy['id'],
                    'name': pharmacy['name'],
                    'address': pharmacy['address'],
                    'prescription_count': count,
                    'prefecture': pref_name,
                    'scraped_at': datetime.now().isoformat()
                }
                append_to_csv(csv_filename, save_data)
                existing_ids.add(pharmacy['id'])
                statistics.add_pharmacy(pref_code, has_data=True)
                prefecture_count += 1
            else:
                logger.debug(f"{pref_name}: {pharmacy['name'][:20]}... ー")
                statistics.add_pharmacy(pref_code, has_data=False)

            random_sleep()

        # リストページに戻る
        driver.get(current_list_url)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result-table"))
            )

            # 次ページへ
            if has_next_page(driver):
                go_to_next_page(driver)
                time.sleep(3)
                page_num += 1
            else:
                break

        except Exception as e:
            logger.info(f"{pref_name}: ページ送り終了 - {e}")
            break

    # 完了記録
    progress_manager.mark_done(pref_code)
    logger.info(f"{pref_name}: 完了 - 取得数 {prefecture_count}件")


def main():
    """メイン処理"""
    global logger

    # 出力ディレクトリの作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ロギング設定
    log_path = os.path.join(OUTPUT_DIR, LOG_FILE)
    logger = setup_logging(log_path, LOG_LEVEL, LOG_FORMAT)

    logger.info("="*60)
    logger.info("🏥 厚生労働省 医療情報ネット 薬局データスクレイパー")
    logger.info("="*60)

    # 進捗管理と統計の初期化
    progress_manager = ProgressManager(OUTPUT_DIR)
    statistics = Statistics(OUTPUT_DIR)

    # 進捗状況の表示
    completed, total, percentage = progress_manager.calculate_progress(len(PREFECTURES))
    logger.info(f"📊 進捗状況: {completed}/{total}都道府県完了 ({percentage:.1f}%)")

    # Webドライバーの初期化
    driver = setup_driver()

    try:
        # 全都道府県を処理
        for code, name in PREFECTURES.items():
            scrape_prefecture(driver, code, name, progress_manager, statistics)

            # 進捗表示
            completed, total, percentage = progress_manager.calculate_progress(len(PREFECTURES))
            logger.info(f"📊 全体進捗: {completed}/{total}都道府県完了 ({percentage:.1f}%)")

        logger.info("✅ 全都道府県の処理が完了しました！")

    except KeyboardInterrupt:
        logger.warning("⚠️ ユーザーによる中断")
    except Exception as e:
        logger.error(f"❌ エラー: {e}", exc_info=True)
        statistics.add_error()
    finally:
        driver.quit()
        statistics.save()
        statistics.print_summary()
        logger.info("ブラウザを終了しました")


if __name__ == "__main__":
    main()
