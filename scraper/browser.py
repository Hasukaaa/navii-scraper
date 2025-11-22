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
    from playwright_stealth import stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

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
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-setuid-sandbox',
            '--disable-software-rasterizer',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            # --single-process を削除（タブクラッシュの原因となる可能性あり）
            '--disable-blink-features=AutomationControlled',  # WebDriverフラグを隠す
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--window-size=1920,1080',
            '--start-maximized',
            # 追加のボット検出回避オプション
            '--disable-web-security',
            '--disable-features=site-per-process',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-prompt-on-repost',
            '--disable-popup-blocking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--enable-automation=false',
            '--password-store=basic',
            '--use-mock-keychain',
        ],
        # より自然なブラウザ環境
        chromium_sandbox=False
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

    # playwright-stealthを適用（利用可能な場合）
    if STEALTH_AVAILABLE:
        try:
            stealth(page)
            logger.info("playwright-stealthを適用しました")
        except Exception as e:
            logger.warning(f"playwright-stealth適用エラー: {e}")

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
            # ページを開く
            logger.info(f"{pref_name}: ページを開いています: {base_url}")
            page.goto(base_url, wait_until='load', timeout=60000)

            # ネットワークが安定するまで待機
            time.sleep(5)

            # DOMContentLoadedを待つ
            page.wait_for_load_state('domcontentloaded', timeout=30000)

            # より長く待機してページが完全に読み込まれるのを待つ（JavaScriptの実行も含む）
            time.sleep(8)

            # ページのスクリーンショットを撮る（デバッグ用）
            screenshot_path = f"outputs/debug_{pref_code}_{attempt}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"{pref_name}: スクリーンショット保存: {screenshot_path}")

            # ページのHTMLを確認（デバッグ用）
            page_content = page.content()
            if "todofukenCd" in page_content:
                logger.info(f"{pref_name}: todofukenCd要素がHTMLに存在します")
            else:
                logger.warning(f"{pref_name}: todofukenCd要素がHTMLに見つかりません")

            # さらに待機してJavaScriptが実行されるのを待つ
            time.sleep(5)

            # 都道府県コードの要素がDOM上に存在するまで待機（hidden要素なので'attached'を使用）
            page.wait_for_selector('#todofukenCd', state='attached', timeout=ELEMENT_TIMEOUT * 1000)

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
