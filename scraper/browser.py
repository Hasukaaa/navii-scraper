#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラウザ管理モジュール
Seleniumドライバーの初期化と設定を管理
"""

import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

from .config import (
    USER_AGENT,
    WINDOW_SIZE,
    PAGE_LOAD_TIMEOUT,
    ELEMENT_TIMEOUT,
    MAX_RETRIES
)

logger = logging.getLogger('PharmacyScraper')


def setup_driver():
    """
    Webドライバーの初期化と設定

    Returns:
        webdriver.Chrome: 設定済みのChromeドライバー
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={WINDOW_SIZE}')
    options.add_argument(f'--user-agent={USER_AGENT}')
    options.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    logger.info("Webドライバーを初期化しました")
    return driver


def safe_set_value(driver, element_id, value):
    """
    リトライ機能付きの要素値設定

    Args:
        driver: Seleniumドライバー
        element_id (str): 要素のID
        value (str): 設定する値

    Returns:
        bool: 成功時True、失敗時False
    """
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


def setup_search_conditions(driver, pref_code, pref_name, base_url):
    """
    検索条件の設定

    Args:
        driver: Seleniumドライバー
        pref_code (str): 都道府県コード
        pref_name (str): 都道府県名
        base_url (str): ベースURL

    Returns:
        bool: 成功時True、失敗時False
    """
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(base_url)
            WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "todofukenCd"))
            )

            # 都道府県コードを設定
            if not safe_set_value(driver, "todofukenCd", pref_code):
                raise Exception("都道府県セット失敗")
            time.sleep(1)

            # 医療機関種別を設定（5 = 薬局）
            if not safe_set_value(driver, "iryoKikanShubetsuCd", "5"):
                raise Exception("医療機関種別セット失敗")
            time.sleep(1)

            # 検索ボタンをクリック
            btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '検索')]"))
            )
            driver.execute_script("arguments[0].click();", btn)

            # 結果が表示されるまで待機
            WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result-count"))
            )

            logger.info(f"{pref_name}: 検索条件設定成功")
            return True

        except Exception as e:
            logger.warning(f"{pref_name}: 検索条件設定エラー (試行 {attempt+1}/{MAX_RETRIES}) - {e}")
            time.sleep(3)

    logger.error(f"{pref_name}: 検索条件設定に失敗しました")
    return False
