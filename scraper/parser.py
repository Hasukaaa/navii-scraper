#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データパーサーモジュール
Webページからのデータ抽出を管理
"""

import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from .config import WAIT_TIMEOUT

logger = logging.getLogger('PharmacyScraper')


def extract_prescription_count(driver, detail_url, pharmacy_id, pharmacy_name):
    """
    薬局詳細ページから処方箋数を抽出

    Args:
        driver: Seleniumドライバー
        detail_url (str): 詳細ページURL
        pharmacy_id (str): 薬局ID
        pharmacy_name (str): 薬局名

    Returns:
        str: 処方箋数（見つからない場合は空文字列）
    """
    try:
        driver.get(detail_url)
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        try:
            # 「総取扱処方箋数」のセルを検索
            target = driver.find_element(
                By.XPATH,
                "//th[contains(text(), '総取扱処方箋数')]/following-sibling::td"
            )
            text = target.text.strip()

            # 数値を抽出（カンマ付きの数値に対応）
            match = re.search(r'(\d+(?:,\d+)?)', text)
            if match:
                return match.group(1)

        except NoSuchElementException:
            logger.debug(f"処方箋数なし: {pharmacy_id} - {pharmacy_name}")

    except Exception as e:
        logger.error(f"詳細ページエラー: {pharmacy_id} - {pharmacy_name} - {e}")

    return ""


def extract_pharmacy_list(driver):
    """
    検索結果ページから薬局リストを抽出

    Args:
        driver: Seleniumドライバー

    Returns:
        list: 薬局情報の辞書リスト
              [{'id': str, 'name': str, 'address': str, 'url': str}, ...]
    """
    pharmacy_list = []

    try:
        rows = driver.find_elements(
            By.XPATH,
            "//table[contains(@class, 'result-table')]/tbody/tr"
        )

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                p_id = cols[0].text.strip()
                p_name = cols[1].text.strip()
                p_addr = cols[2].text.strip()

                try:
                    # 詳細ページへのリンクを取得
                    link = cols[1].find_element(By.TAG_NAME, "a").get_attribute("href")
                    pharmacy_list.append({
                        "id": p_id,
                        "name": p_name,
                        "address": p_addr,
                        "url": link
                    })
                except:
                    # リンクが見つからない場合はスキップ
                    pass

    except Exception as e:
        logger.error(f"リスト取得エラー: {e}")

    return pharmacy_list


def has_next_page(driver):
    """
    次ページが存在するかチェック

    Args:
        driver: Seleniumドライバー

    Returns:
        bool: 次ページが存在する場合True
    """
    try:
        next_links = driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
        if not next_links:
            return False

        parent_li = next_links[0].find_element(By.XPATH, "..")
        if "disabled" in parent_li.get_attribute("class"):
            return False

        return True

    except Exception:
        return False


def go_to_next_page(driver):
    """
    次ページへ遷移

    Args:
        driver: Seleniumドライバー

    Returns:
        bool: 成功時True、失敗時False
    """
    try:
        next_links = driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
        if next_links:
            driver.execute_script("arguments[0].click();", next_links[0])
            return True
    except Exception as e:
        logger.error(f"ページ送りエラー: {e}")

    return False
