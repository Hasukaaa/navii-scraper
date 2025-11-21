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
- Playwrightによる安定したブラウザ自動化
- Dockerコンテナ環境対応

## プロジェクト構成

```
navii-scraper/
├── scraper/                    # メインパッケージ
│   ├── __init__.py            # パッケージ初期化
│   ├── main.py                # メイン実行フロー
│   ├── browser.py             # Playwright初期化・操作
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
├── Dockerfile                  # Docker設定
├── docker-compose.yml          # Docker Compose設定
└── .dockerignore               # Docker除外ファイル
```

## セットアップ

### 方法1: Docker（推奨）

Dockerを使用すると、環境構築が不要で最も簡単に実行できます。

```bash
# リポジトリのクローン
git clone https://github.com/Hasukaaa/navii-scraper.git
cd navii-scraper

# Dockerイメージのビルドと実行
docker-compose up --build
```

出力ファイルは `./outputs` ディレクトリに自動的に保存されます。

### 方法2: ローカル環境（手動セットアップ）

```bash
# リポジトリのクローン
git clone https://github.com/Hasukaaa/navii-scraper.git
cd navii-scraper

# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# パッケージのインストール
pip install -r requirements.txt

# Playwrightブラウザのインストール
playwright install chromium
```

## 使い方

### Docker環境での実行

```bash
# バックグラウンドで実行
docker-compose up -d

# ログを確認
docker-compose logs -f

# 停止
docker-compose down
```

### ローカル環境での実行

```bash
# 仮想環境を有効化
source venv/bin/activate

# スクレイパーを実行
python run.py
```

### 中断と再開

- 実行中に `Ctrl+C` で中断可能
- 再度実行すると、前回の続きから再開されます
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

## 技術スタック

- **Python 3.x**: メインプログラミング言語
- **Playwright**: ブラウザ自動化（Chromium使用）
- **Docker**: コンテナ化による環境統一

## 注意事項

- スクレイピング実行中はサーバーに負荷をかけないよう、適切な待機時間を設定しています
- 実行には数時間かかる場合があります（全都道府県）
- Docker環境では、Playwright公式イメージを使用して安定動作を実現しています

## ライセンス

MIT License

## 開発者向け情報

### モジュール構成

- **config.py**: 全設定値の一元管理
- **browser.py**: Playwrightブラウザの初期化、検索条件設定
- **parser.py**: Webページからのデータ抽出
- **utils.py**: CSV操作、ログ設定などのユーティリティ
- **progress_manager.py**: 進捗追跡と統計情報管理
- **main.py**: メイン実行ロジック

### 移行履歴

- **v2.0**: SeleniumからPlaywrightへ移行
  - コンテナ環境での安定性向上
  - Chromeクラッシュ問題の解決
  - よりシンプルで堅牢なAPI