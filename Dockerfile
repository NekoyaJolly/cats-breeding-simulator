# 3.12-slimベースイメージを使用 (速度と軽量化を最適化)
FROM python:3.12-slim

# 作業ディレクトリを /app に設定
WORKDIR /app

# 依存関係ファイルを先にコピーしてキャッシュを有効化
COPY requirements.txt .

# 依存関係をキャッシュなしでインストール
RUN pip install --no-cache-dir -r requirements.txt

# マスタデータファイルとPythonスクリプトをコンテナ内にコピー。
# 遺伝マップ (genetic/breed) に加え、色名正規化レイヤが import 時に読む
# cat_color_master.csv (入力 alias 解決 + 出力 canonical 化) と
# cat_color_display_alias_map.csv (猫種別表示名 / Van 正規化) も同梱する。
# これらを欠くと COLOR_MASTER / DISPLAY_ALIAS_MAP が空マスタになり、
# 本番でのみ正規化が無効化される (略称のまま入出力される)。
COPY docs/architecture/cat_color_genetic_map.csv docs/architecture/cat_breed_genetic_map.csv ./
COPY docs/architecture/cat_color_master.csv docs/architecture/cat_color_display_alias_map.csv ./
COPY main.py ./
COPY cat_breeding_simulator/ ./cat_breeding_simulator/

# ポート 8080 を解放
EXPOSE 8080

# uvicornでFastAPIアプリケーションを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
