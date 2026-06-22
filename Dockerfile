# 3.12-slimベースイメージを使用 (速度と軽量化を最適化)
FROM python:3.12-slim

# 作業ディレクトリを /app に設定
WORKDIR /app

# 依存関係ファイルを先にコピーしてキャッシュを有効化
COPY requirements.txt .

# 依存関係をキャッシュなしでインストール
RUN pip install --no-cache-dir -r requirements.txt

# マスタデータファイルとPythonスクリプトをコンテナ内にコピー
COPY docs/architecture/cat_color_genetic_map.csv docs/architecture/猫種データUTF8Ver.csv ./
COPY main.py ./
COPY cat_breeding_simulator/ ./cat_breeding_simulator/

# ポート 8080 を解放
EXPOSE 8080

# uvicornでFastAPIアプリケーションを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
