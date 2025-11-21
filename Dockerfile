# Playwright公式イメージをベースに使用
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 作業ディレクトリを設定
WORKDIR /app

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザをインストール（Chromiumのみ）
RUN playwright install chromium

# アプリケーションコードをコピー
COPY . .

# 出力ディレクトリを作成
RUN mkdir -p outputs

# 環境変数の設定（必要に応じて）
ENV PYTHONUNBUFFERED=1

# スクレイパーを実行
CMD ["python", "run.py"]
