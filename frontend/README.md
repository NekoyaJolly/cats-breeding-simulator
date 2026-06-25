# フロントエンド (猫毛色シミュレーター)

親猫2匹の毛色から子猫の毛色確率を計算する Web UI。バックエンド
(`cat_breeding_simulator`, FastAPI) の `POST /api/v1/calculate` を呼び出す。

## 技術スタック

- Next.js 14 (App Router) / React 18 / TypeScript (strict)
- Tailwind CSS
- Zod (API レスポンスのランタイム検証)

## 構成

```
frontend/
├── app/            # App Router (layout / page / globals.css)
├── components/     # BreedingForm (入力) / ResultView (結果表示)
├── lib/            # schema.ts (Zod) / api.ts (fetch ラッパ)
└── next.config.mjs # /api/* を BACKEND_ORIGIN へ rewrite
```

## バックエンド連携

`next.config.mjs` の rewrite が `/api/*` を `BACKEND_ORIGIN`
(既定 `http://localhost:8000`) へプロキシする。これにより同一オリジン
扱いとなり、バックエンドに CORS 設定を足さずに済む。

## 開発手順

```bash
# 1. バックエンド (リポジトリ直下で)
uvicorn main:app --reload --port 8000

# 2. フロントエンド (本ディレクトリで)
npm install
npm run dev          # http://localhost:3000

# 型チェック / ビルド
npm run typecheck
npm run build
```

## 環境変数

`.env.example` を参照。`BACKEND_ORIGIN` でバックエンド接続先を差し替える。
