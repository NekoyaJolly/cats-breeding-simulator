# 直近フェーズ サマリー (引き継ぎ用)

最終更新: 2026-06-28
位置づけ: **次フェーズ着手時に最初に読む唯一の引き継ぎ** (AGENTS.md §5.0 ローリング運用 / 常に1件)。  
正本は `docs/architecture/` 配下 (AGENTS.md §0 / V9 正本3冊 + `cat_color_master.csv` 系 + `cat_color_display_alias_map.csv`)。本書は要約であり正本ではない。

---

## 1. このフェーズで完了したこと: フロントエンド (Web UI) MVP 新設

### 2026-06-28 追記: 「目標カラーから探す」逆引きMVP
- **座位単位の純粋関数**を `cat_breeding_simulator/mendelian.py` に追加し、B/D/A/O/C/I/Wb の主要遺伝ケースを分数ベースで検証するテストを追加。
- **逆引きAPI** `POST /api/v1/reverse-lookup` を追加。登録猫または自舎カラー構成と目標カラーから、交配候補を「確定で期待できる」「条件付きで期待できる」「現在の情報では判定が難しい」「現在の登録情報では確認できない」に分類して返す。
- **逆引き結果**は、確定確率、条件付き最大確率、確認が必要な条件、推奨検査、座位別根拠、目標カラー以外に生まれる可能性のあるカラーを含む。候補が無い場合も、目標カラーに必要な条件と現在確認できない条件を返す。
- **フロントエンド**は通常シミュレーターを既定タブとして維持し、別タブに「目標カラーから探す」を追加。両親猫のカラー登録は `frontend/lib/registeredCatRepository.ts` の抽象リポジトリ経由でローカル保存する。
- **逆引き画面の入力UI**は、通常シミュレーターと同じ `GET /api/v1/colors` / `ColorCombobox` を使う。一括カラー登録、登録済み父母候補の編集、父候補/母候補のアコーディオン表示、目標性別の任意指定、検索結果候補のアコーディオン表示に対応。

### A. スタック・配置
- `frontend/` に Next.js 14 (App Router) / React 18 / TypeScript strict / Tailwind CSS で新設。バックエンド (FastAPI) は**無改修**。
- 構成: `app/` (layout / page / globals.css)、`components/` (`BreedingForm` 入力 / `ResultView` 結果表示)、`lib/` (`schema.ts` Zod / `api.ts` fetch ラッパ)。
- `npm run typecheck` / `npm run build` 成功。lint クリーン。

### B. 入出力
- **入力**: 父色・母色 (自由入力・必須)、猫種 (任意)、モード選択 (`normal` / `explicit_carrier` / `carrier_exploration`)。`explicit_carrier` 時のみキャリア入力欄 (`座位:遺伝子型` カンマ区切り) を表示。
- **出力**: `results` (性別×毛色×確率テーブル) / `diagnostics` (opened/closed loci・assumptions・unmatched) / `carrier_exploration_results` を表示。**carrier_exploration は通常結果と視覚的に分離**して表示 (シミュレーター正本 §2)。

### C. API 連携 (フロント単独方針)
- **`POST /api/v1/calculate` を Zod でランタイム検証** (`lib/schema.ts`、`api.py` の `CalculationResponse` を再宣言)。`any`/`unknown` 型は持ち込まず narrow (AGENTS 最優先5原則 §2)。
- FastAPI の **422 を人間可読へ整形** (`lib/api.ts`): 自前 `BreedingCalculationError` の**文字列 detail** と pydantic 検証エラーの**配列 detail (`{msg}`)** の両形を処理。バックエンド未起動時の接続エラーも文言化。
- **`next.config.mjs` の rewrite で `/api/*` を `BACKEND_ORIGIN` (既定 `http://localhost:8000`) へプロキシ**。同一オリジン扱いとし、バックエンド側 CORS 追加を回避。本番は env で差し替え。

### D. 検証 (AGENTS §6.3 サーバ起動 + 実経路)
- uvicorn (:8000) + `next start` (:3000) を起動し、**proxy 経由 (:3000→:8000)** で確認:
  - golden path (normal): Silver Tabby × Brown Tabby → 8 行 + diagnostics。
  - carrier_exploration: `carrier_exploration_results` フィールド処理。
  - 未知の色 → 422 (文字列 detail)。空入力 → 422 (配列 detail)。両形ともフロントで整形表示。

---

## 2. 計算機の現状 (バックエンド)

- **遺伝計算**: 全座位 Punnett + モード別の親遺伝子型生成 (`engine.py` / `master_data.py`)。3モード実装済み。
- **名前 (入力)**: `cat_color_master.csv` 経由で alias 入力受理・canonical 解決 (`color_master.py`)。
- **名前 (出力表示)**: canonical 正規化の後段で `cat_color_display_alias_map.csv` 経由の猫種別表示名・Van 正規化 (`display_alias_map.py`)。
- **API**: `POST /api/v1/calculate`。`mode` / `sire_carriers` / `dam_carriers` / `breed`。
- **テスト**: pytest 42 passed。

---

## 3. 次回以降の作業候補

### 優先度: 中〜高 (フロント続き)
1. **逆引き入力UXのさらなる統一**: 通常シミュレーター側の最近選択した毛色・猫種履歴を、逆引き画面の両親猫カラー登録にも共有する。
2. **フロントのテスト/CI**: コンポーネント・`lib/` のユニットテスト、`typecheck`/`build` の PR ゲート化。
3. **デプロイ構成**: フロント (Vercel 等) とバックエンド (Cloud Run) の接続・`BACKEND_ORIGIN` 運用 (運用正本と整合のこと)。

### 優先度: 中 (バックエンド継続)
4. **表示名マスタの経路拡張**: 猫種固有パターン細分、Mitted/Bi-Color の猫種文脈表示 (§5.3/§5.4)、親入力での明示 Van 保持。
5. **CI 整備**: GitHub Actions で `pytest -q` を PR ゲート化 (運用正本 §6)。

### 優先度: 設計判断が要る (将来フェーズ)
6. **review_required 遺伝子座の確定**: Wb系 / Point/Mink/Sepia の C系 (`cat_color_master_review.md` §8)。
7. **carrier_exploration の拡張**: I-locus の扱い、猫種文脈併用、mink シナリオ。
8. **State-key による本格正本化**: engine 逆引き (GENOTYPE_TO_COLOR_MAP) を master 状態カラム駆動へ (影響範囲大)。

---

## 4. 既知の留意点 (落とし穴)

### フロントエンド
- **API レスポンスは必ず Zod で narrow**してから使う。`api.py` の契約を変えたら `lib/schema.ts` を同期。
- **422 detail は2形ある** (文字列 / 配列)。`lib/api.ts` の `describeError` が両対応。新たなエラー形を足す際は注意。
- dev/本番とも `/api/*` は rewrite 前提。バックエンド接続先は `BACKEND_ORIGIN` で制御 (ハードコードしない)。

### バックエンド
- **表示名解決は canonical 正規化の「後」**。順序を入れ替えると Ebony 等が Black へ戻る (回帰テストで担保)。
- **CanonicalPhenotype 列はエンジン内部出力名と一致必須** (master の CanonicalColorId と混同しない)。
- **A/Wb は normal で展開しない**。**carrier_exploration は通常結果に混ぜない** (事前確率を掛けない / 両親隠れキャリアの自動生成禁止)。
- 計算ロジック修正タスクで `Dockerfile`/`.github/workflows/`/Cloud Run 等の運用系を触らない (運用正本 §3.3)。
