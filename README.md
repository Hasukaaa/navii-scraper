# navii-scraper

厚生労働省 医療情報ネット 薬局データスクレイパー

## 概要

全国の薬局情報（処方箋数を含む）を厚生労働省の医療情報ネットから取得するスクレイピングツールです。

## 機能

- 全47都道府県の薬局データを自動収集
- 処方箋数（総取扱処方箋数）の抽出
- 中断・再開機能（進捗状況を保存）
- 詳細なロギング機能
- 統計情報の出力
- 実行時間の計測

## プロジェクト構成

```
navii-scraper/
├── scraper/                    # メインパッケージ
│   ├── __init__.py            # パッケージ初期化
│   ├── main.py                # メイン実行フロー
│   ├── browser.py             # Selenium初期化・操作
│   ├── parser.py              # データ抽出
│   ├── utils.py               # ユーティリティ関数
│   ├── progress_manager.py    # 進捗・統計管理
│   └── config.py              # 設定ファイル
├── outputs/                    # 出力ディレクトリ
│   ├── XX_都道府県名_prescription.csv
│   ├── progress.json          # 進捗状況
│   ├── statistics.json        # 統計情報
│   └── scraper.log            # ログファイル
├── run.py                      # 実行エントリポイント
├── requirements.txt            # 依存パッケージ
└── setup.sh                    # セットアップスクリプト

※ pharmacy_scraper_enhanced.py と pharmacy_scraper_original.py は旧バージョンです
```

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/Hasukaaa/navii-scraper.git
cd navii-scraper
```

### 2. 自動セットアップ（推奨）

```bash
bash setup.sh
```

### 3. 手動セットアップ

```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# パッケージのインストール
pip install -r requirements.txt
```

## 使い方

### 基本的な実行

```bash
# 仮想環境を有効化
source venv/bin/activate

# スクレイパーを実行
python run.py
```

### 中断と再開

- 実行中に `Ctrl+C` で中断可能
- 再度 `python run.py` を実行すると、前回の続きから再開されます
- 進捗状況は `outputs/progress.json` に保存されます

## 出力データ

### CSV形式（都道府県ごと）

`outputs/XX_都道府県名_prescription.csv`

| カラム名 | 説明 |
|---------|------|
| id | 薬局ID |
| name | 薬局名 |
| address | 住所 |
| prescription_count | 総取扱処方箋数 |
| prefecture | 都道府県名 |
| scraped_at | 取得日時（ISO形式） |

### 進捗ファイル

`outputs/progress.json` - 各都道府県の完了状態

### 統計ファイル

`outputs/statistics.json` - 実行統計情報
- 実行時間
- 総薬局数
- 処方箋数データの有無
- エラー数、スキップ数
- 都道府県別統計

### ログファイル

`outputs/scraper.log` - 詳細な実行ログ

## 設定のカスタマイズ

`scraper/config.py` で以下の設定を変更できます：

- タイムアウト時間
- 待機時間（MIN_WAIT, MAX_WAIT）
- リトライ回数
- 出力ディレクトリ
- ログレベル

## 注意事項

- スクレイピング実行中はサーバーに負荷をかけないよう、適切な待機時間を設定しています
- 実行には数時間かかる場合があります（全都道府県）
- Chrome/Chromiumがインストールされている必要があります（webdriver-managerが自動管理）

## ライセンス

MIT License

## 開発者向け情報

### モジュール構成

- **config.py**: 全設定値の一元管理
- **browser.py**: Seleniumドライバーの初期化、検索条件設定
- **parser.py**: Webページからのデータ抽出
- **utils.py**: CSV操作、ログ設定などのユーティリティ
- **progress_manager.py**: 進捗追跡と統計情報管理
- **main.py**: メイン実行ロジック

### 旧バージョンからの移行

pharmacy_scraper_enhanced.py の機能は完全に新しい構成に移行されています。
モジュール化により、保守性・拡張性が向上しました。