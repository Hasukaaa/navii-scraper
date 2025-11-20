#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進捗管理モジュール
スクレイピングの進捗状況と統計情報を管理
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger('PharmacyScraper')


class ProgressManager:
    """
    進捗状況管理クラス
    都道府県ごとの完了状態を保存・読み込み
    """

    def __init__(self, output_dir):
        """
        Args:
            output_dir (str): 出力ディレクトリ
        """
        self.output_dir = output_dir
        self.progress_file = os.path.join(output_dir, "progress.json")
        self.progress_data = {}
        self._load()

    def _load(self):
        """進捗ファイルを読み込み"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress_data = json.load(f)
                logger.info(f"進捗ファイルを読み込みました: {self.progress_file}")
            except Exception as e:
                logger.error(f"進捗ファイル読み込みエラー: {e}")
                self.progress_data = {}
        else:
            logger.info("新規スクレイピングを開始します")

    def save(self):
        """進捗状態を保存"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"進捗ファイル保存エラー: {e}")

    def mark_done(self, pref_code):
        """
        都道府県を完了としてマーク

        Args:
            pref_code (str): 都道府県コード
        """
        self.progress_data[pref_code] = "DONE"
        self.save()

    def is_done(self, pref_code):
        """
        都道府県が完了済みかチェック

        Args:
            pref_code (str): 都道府県コード

        Returns:
            bool: 完了済みの場合True
        """
        return self.progress_data.get(pref_code) == "DONE"

    def calculate_progress(self, total_prefectures):
        """
        進捗率を計算

        Args:
            total_prefectures (int): 総都道府県数

        Returns:
            tuple: (完了数, 総数, 進捗率%)
        """
        completed = sum(1 for v in self.progress_data.values() if v == "DONE")
        percentage = (completed / total_prefectures) * 100 if total_prefectures > 0 else 0
        return completed, total_prefectures, percentage


class Statistics:
    """
    統計情報管理クラス
    スクレイピング実行の統計を記録
    """

    def __init__(self, output_dir):
        """
        Args:
            output_dir (str): 出力ディレクトリ
        """
        self.output_dir = output_dir
        self.stats_file = os.path.join(output_dir, "statistics.json")
        self.start_time = datetime.now()
        self.total_pharmacies = 0
        self.total_with_data = 0
        self.total_without_data = 0
        self.errors = 0
        self.skipped = 0
        self.prefecture_stats = {}

    def add_pharmacy(self, pref_code, has_data=True):
        """
        薬局データを記録

        Args:
            pref_code (str): 都道府県コード
            has_data (bool): 処方箋数データの有無
        """
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
        """統計情報をファイルに保存"""
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

        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
            logger.info(f"統計情報を保存しました: {self.stats_file}")
        except Exception as e:
            logger.error(f"統計情報保存エラー: {e}")

    def print_summary(self):
        """統計サマリーをコンソールに出力"""
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
