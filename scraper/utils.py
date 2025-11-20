#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ユーティリティモジュール
共通で使用する補助関数を提供
"""

import os
import csv
import time
import random
import logging

from .config import MIN_WAIT, MAX_WAIT, CSV_FIELDNAMES, CSV_ENCODING

logger = logging.getLogger('PharmacyScraper')


def random_sleep():
    """
    ランダムな時間待機（サーバー負荷軽減のため）
    """
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))


def append_to_csv(filename, data_dict):
    """
    CSVファイルにデータを追記

    Args:
        filename (str): CSVファイルパス
        data_dict (dict): 追記するデータ
    """
    file_exists = os.path.exists(filename)

    with open(filename, 'a', newline='', encoding=CSV_ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)


def get_existing_ids(filepath):
    """
    既存のCSVファイルから薬局IDを取得

    Args:
        filepath (str): CSVファイルパス

    Returns:
        set: 既存の薬局IDのセット
    """
    if not os.path.exists(filepath):
        return set()

    ids = set()
    try:
        with open(filepath, 'r', encoding=CSV_ENCODING) as f:
            reader = csv.DictReader(f)
            row_count = 0
            for row in reader:
                row_count += 1
                if row.get('id'):
                    ids.add(row['id'])

            # ヘッダーのみの場合は空セット
            if row_count == 0:
                return set()

    except Exception as e:
        logger.error(f"既存IDの読み込みエラー: {filepath} - {e}")

    return ids


def is_csv_valid(filepath):
    """
    CSVファイルが有効か確認（データ行が存在するか）

    Args:
        filepath (str): CSVファイルパス

    Returns:
        bool: データ行が存在する場合True
    """
    if not os.path.exists(filepath):
        return False

    try:
        with open(filepath, 'r', encoding=CSV_ENCODING) as f:
            # ヘッダー行とデータ行があるか確認
            return len(f.readlines()) > 1
    except:
        return False


def setup_logging(log_file, log_level, log_format):
    """
    ロギング設定の初期化

    Args:
        log_file (str): ログファイルパス
        log_level (str): ログレベル
        log_format (str): ログフォーマット

    Returns:
        logging.Logger: 設定済みロガー
    """
    logger = logging.getLogger('PharmacyScraper')
    logger.setLevel(getattr(logging, log_level))

    # ファイルハンドラ
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    # コンソールハンドラ
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # フォーマッター
    formatter = logging.Formatter(log_format)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
