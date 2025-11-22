#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラウザ設定のテストスクリプト
1つの都道府県のみをテストして、ボット検出回避が機能しているか確認
"""

import os
import sys
import logging

# scraperモジュールをインポート
from scraper.config import BASE_URL, OUTPUT_DIR, LOG_LEVEL, LOG_FORMAT
from scraper.browser import setup_browser, setup_search_conditions
from scraper.utils import setup_logging

def main():
    """テスト実行"""
    # 出力ディレクトリの作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ロギング設定
    log_path = os.path.join(OUTPUT_DIR, "test_browser.log")
    logger = setup_logging(log_path, LOG_LEVEL, LOG_FORMAT)

    logger.info("=" * 60)
    logger.info("ブラウザ設定テスト開始")
    logger.info("=" * 60)

    # Playwrightブラウザの初期化
    playwright, browser, page = setup_browser()

    try:
        # 北海道でテスト
        pref_code = "01"
        pref_name = "北海道"

        logger.info(f"{pref_name} ({pref_code}) のテストを開始します")

        # 検索条件の設定
        success = setup_search_conditions(page, pref_code, pref_name, BASE_URL)

        if success:
            logger.info("✅ テスト成功！ボット検出を回避できました")
            return 0
        else:
            logger.error("❌ テスト失敗：検索条件の設定に失敗しました")
            return 1

    except Exception as e:
        logger.error(f"❌ エラー: {e}", exc_info=True)
        return 1
    finally:
        browser.close()
        playwright.stop()
        logger.info("ブラウザを終了しました")

if __name__ == "__main__":
    sys.exit(main())
