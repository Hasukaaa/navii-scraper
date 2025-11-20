#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pharmacy Scraper Package
厚生労働省 医療情報ネット 薬局データスクレイパー
"""

__version__ = "2.0.0"
__author__ = "navii-scraper"

from .main import main
from .config import PREFECTURES, OUTPUT_DIR
from .progress_manager import ProgressManager, Statistics

__all__ = [
    'main',
    'PREFECTURES',
    'OUTPUT_DIR',
    'ProgressManager',
    'Statistics'
]
