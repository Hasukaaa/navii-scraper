#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラウザ管理モジュール
Playwrightブラウザの初期化と設定を管理
"""

import logging
import time
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    stealth_sync = None

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

    # Chromiumブラウザを起動（ボット検出回避のための設定）
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',  # WebDriverフラグを隠す
            '--window-size=1920,1080',
            # 安定性のためのオプション
            '--disable-extensions',
            '--disable-popup-blocking',
            '--no-first-run',
        ]
    )

    # コンテキストとページを作成（より人間らしい設定）
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,  # SSL証明書エラーを無視
        locale='ja-JP',
        timezone_id='Asia/Tokyo',
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    )

    # タイムアウト設定
    context.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)  # ミリ秒に変換

    page = context.new_page()

    # playwright-stealthを適用（利用可能な場合）- 一時的に無効化
    # if STEALTH_AVAILABLE and stealth_sync:
    #     try:
    #         stealth_sync(page)
    #         logger.info("playwright-stealthを適用しました")
    #     except Exception as e:
    #         logger.warning(f"playwright-stealth適用エラー: {e}")

    # WebDriver検出を回避するための追加設定
    page.add_init_script("""
        // WebDriverフラグを削除
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // automationフラグを削除
        Object.defineProperty(navigator, 'automation', {
            get: () => undefined
        });

        // Chrome検出をバイパス
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // Permissions APIのバイパス
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // プラグイン配列の設定（より現実的な値に）
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
                {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
            ]
        });

        // 言語設定
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ja-JP', 'ja', 'en-US', 'en']
        });

        // Platform設定
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });

        // vendor設定
        Object.defineProperty(navigator, 'vendor', {
            get: () => 'Google Inc.'
        });

        // maxTouchPoints設定
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0
        });

        // connection設定
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: 100,
                downlink: 10,
                saveData: false
            })
        });

        // hardwareConcurrency設定
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });

        // deviceMemory設定
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
    """)

    logger.info("Playwrightブラウザを初期化しました（ボット検出回避設定有効）")
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
            # リトライ時は新しいページを作成（クラッシュ後の状態をクリア）
            if attempt > 0:
                logger.info(f"{pref_name}: リトライ {attempt + 1}/{MAX_RETRIES} - 新しいページを作成")
                try:
                    page.close()
                except:
                    pass
                page = page.context.new_page()

            # ページを開く（より軽量な読み込み方法）
            logger.info(f"{pref_name}: ページを開いています: {base_url}")
            page.goto(base_url, wait_until='domcontentloaded', timeout=60000)

            # JavaScriptが実行されるまで待機
            logger.info(f"{pref_name}: JavaScript実行を待機中（20秒）...")
            time.sleep(20)

            # 都道府県コードの要素がDOM上に存在するか直接チェック（wait_for_selectorを避ける）
            logger.info(f"{pref_name}: todofukenCd要素を確認中...")
            found = False
            for check_attempt in range(10):  # 最大10回、1秒ごとにチェック
                element_exists = page.evaluate("""
                    () => {
                        const el = document.getElementById('todofukenCd');
                        return el !== null;
                    }
                """)
                if element_exists:
                    logger.info(f"{pref_name}: todofukenCd要素が見つかりました")
                    found = True
                    break
                time.sleep(1)

            if not found:
                raise Exception("todofukenCd要素が見つかりませんでした")

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
            # より長い待機時間でリトライ（指数バックオフ）
            wait_time = 10 * (attempt + 1)
            logger.info(f"{pref_name}: {wait_time}秒待機してからリトライします")
            time.sleep(wait_time)

    logger.error(f"{pref_name}: 検索条件設定に失敗しました")
    return False
