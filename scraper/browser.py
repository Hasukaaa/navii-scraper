#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラウザ管理モジュール
Playwrightブラウザの初期化と設定を管理
"""

import logging
import time
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from .config import (
    USER_AGENT,
    PAGE_LOAD_TIMEOUT,
    ELEMENT_TIMEOUT,
    MAX_RETRIES
)

logger = logging.getLogger('PharmacyScraper')


def setup_browser():
    """
    Playwrightブラウザの初期化と設定

    Returns:
        tuple: (playwright, browser, page) のタプル
    """
    playwright = sync_playwright().start()

    # Chromiumブラウザを起動（Docker環境で最適化）
    # ローカル環境でクラッシュする場合はDockerでの実行を推奨
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-setuid-sandbox',
        ]
    )

    # コンテキストとページを作成
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True  # SSL証明書エラーを無視
    )

    # タイムアウト設定
    context.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)  # ミリ秒に変換

    page = context.new_page()

    logger.info("Playwrightブラウザを初期化しました")
    return playwright, browser, page


def safe_set_value(page: Page, element_id: str, value: str):
    """
    リトライ機能付きの要素値設定

    Args:
        page: Playwrightページオブジェクト
        element_id (str): 要素のID
        value (str): 設定する値

    Returns:
        bool: 成功時True、失敗時False
    """
    for i in range(MAX_RETRIES):
        try:
            # Playwrightは自動待機機能があるため、明示的な待機は不要
            page.evaluate(f"""
                const element = document.getElementById('{element_id}');
                if (element) {{
                    element.value = '{value}';
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            """)
            return True
        except PlaywrightTimeoutError:
            time.sleep(1)
            continue
        except Exception as e:
            logger.warning(f"input設定再試行中({i+1}/{MAX_RETRIES}): {e}")
            time.sleep(1)
    return False


def setup_search_conditions(page: Page, pref_code: str, pref_name: str, base_url: str):
    """
    検索条件の設定

    Args:
        page: Playwrightページオブジェクト
        pref_code (str): 都道府県コード
        pref_name (str): 都道府県名
        base_url (str): ベースURL

    Returns:
        bool: 成功時True、失敗時False
    """
    for attempt in range(MAX_RETRIES):
        try:
            # ページを開く
            page.goto(base_url, wait_until='networkidle')

            # 都道府県コードの要素が表示されるまで待機
            page.wait_for_selector('#todofukenCd', timeout=ELEMENT_TIMEOUT * 1000)

            # 都道府県コードを設定
            if not safe_set_value(page, "todofukenCd", pref_code):
                raise Exception("都道府県セット失敗")
            time.sleep(1)

            # 医療機関種別を設定（5 = 薬局）
            if not safe_set_value(page, "iryoKikanShubetsuCd", "5"):
                raise Exception("医療機関種別セット失敗")
            time.sleep(1)

            # 検索ボタンをクリック
            page.click("xpath=//button[contains(text(), '検索')]")

            # 結果が表示されるまで待機
            page.wait_for_selector('.result-count', timeout=ELEMENT_TIMEOUT * 1000)

            logger.info(f"{pref_name}: 検索条件設定成功")
            return True

        except Exception as e:
            logger.warning(f"{pref_name}: 検索条件設定エラー (試行 {attempt+1}/{MAX_RETRIES}) - {e}")
            time.sleep(3)

    logger.error(f"{pref_name}: 検索条件設定に失敗しました")
    return False
