#!/bin/bash
# クイックセットアップスクリプト

echo "🚀 薬局データスクレイパーのセットアップ"
echo "=========================================="

# 仮想環境の作成
echo "📦 仮想環境を作成中..."
python3 -m venv venv

# 仮想環境を有効化
echo "✅ 仮想環境を有効化..."
source venv/bin/activate

# パッケージのインストール
echo "📥 必要なパッケージをインストール中..."
pip install -r requirements.txt

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "実行方法:"
echo "  source venv/bin/activate"
echo "  python pharmacy_scraper_enhanced.py"
echo ""
