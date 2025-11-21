#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データパーサーモジュール
Webページからのデータ抽出を管理
"""

import re
import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .config import WAIT_TIMEOUT

logger = logging.getLogger('PharmacyScraper')


def extract_prescription_count(page: Page, detail_url: str, pharmacy_id: str, pharmacy_name: str):
    """
    薬局詳細ページから処方箋数を抽出

    Args:
        page: Playwrightページオブジェクト
        detail_url (str): 詳細ページURL
        pharmacy_id (str): 薬局ID
        pharmacy_name (str): 薬局名

    Returns:
        str: 処方箋数（見つからない場合は空文字列）
    """
    try:
        page.goto(detail_url, wait_until='networkidle')

        try:
            # 「総取扱処方箋数」のセルを検索
            target = page.locator("xpath=//th[contains(text(), '総取扱処方箋数')]/following-sibling::td").first
            text = target.inner_text().strip()

            # 数値を抽出（カンマ付きの数値に対応）
            match = re.search(r'(\d+(?:,\d+)?)', text)
            if match:
                return match.group(1)

        except Exception:
            logger.debug(f"処方箋数なし: {pharmacy_id} - {pharmacy_name}")

    except Exception as e:
        logger.error(f"詳細ページエラー: {pharmacy_id} - {pharmacy_name} - {e}")

    return ""


def extract_pharmacy_list(page: Page):
    """
    検索結果ページから薬局リストを抽出

    Args:
        page: Playwrightページオブジェクト

    Returns:
        list: 薬局情報の辞書リスト
              [{'id': str, 'name': str, 'address': str, 'url': str}, ...]
    """
    pharmacy_list = []

    try:
        # テーブル行を取得
        rows = page.locator("xpath=//table[contains(@class, 'result-table')]/tbody/tr").all()

        for row in rows:
            cols = row.locator("td").all()
            if len(cols) >= 3:
                p_id = cols[0].inner_text().strip()
                p_name = cols[1].inner_text().strip()
                p_addr = cols[2].inner_text().strip()

                try:
                    # 詳細ページへのリンクを取得
                    link = cols[1].locator("a").get_attribute("href")
                    if link:
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


def has_next_page(page: Page):
    """
    次ページが存在するかチェック

    Args:
        page: Playwrightページオブジェクト

    Returns:
        bool: 次ページが存在する場合True
    """
    try:
        next_links = page.locator("xpath=//a[contains(text(), '次へ')]").all()
        if not next_links:
            return False

        # 最初の「次へ」リンクの親要素を確認
        parent_li = next_links[0].locator("xpath=..").first
        parent_class = parent_li.get_attribute("class") or ""
        if "disabled" in parent_class:
            return False

        return True

    except Exception:
        return False


def go_to_next_page(page: Page):
    """
    次ページへ遷移

    Args:
        page: Playwrightページオブジェクト

    Returns:
        bool: 成功時True、失敗時False
    """
    try:
        next_links = page.locator("xpath=//a[contains(text(), '次へ')]").all()
        if next_links:
            next_links[0].click()
            return True
    except Exception as e:
        logger.error(f"ページ送りエラー: {e}")

    return False
