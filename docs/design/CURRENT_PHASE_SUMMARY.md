# 直近フェーズ サマリー (引き継ぎ用)

最終更新: 2026-06-29
位置づけ: **次フェーズ着手時に最初に読む唯一の引き継ぎ** (AGENTS.md §5.0 ローリング運用 / 常に1件)。
正本は `docs/architecture/` 配下 (AGENTS.md §0 / V9 正本3冊 + `cat_color_master.csv` 系 + `cat_color_display_alias_map.csv`)。本書は要約であり正本ではない。

---

## 1. このフェーズで完了したこと: 計算パフォーマンス改善 (逆引き / リター推定 / エンジン)

逆引き (オス×メス総当たり) とリター推定 (親候補爆発) が大規模入力で重すぎた問題を、**出力を一切変えずに** 高速化した。設計と計測の詳細は本フェーズで一旦 `docs/design/performance_refactor_specification.md` に置き、完了に伴い V9 正本 §9.3 / §9.4 へ実装メモを統合して当該指示書は削除した。

### 実施内容 (チケット単位)
- **PERF-1 入力上限**: `api.py` の `field_validator` で **逆引き登録猫 ≤ 50 / リター観察子猫 ≤ 12**。超過は理由が分かる日本語で 422。
- **PERF-2 エンジンのメモ化**: `engine.py` で `calculate_report` / `_resolve_parent_genotypes` / `_build_gametes` をインスタンスキャッシュ化 (純粋計算 = import時定数 + 引数のみに依存)。キャッシュ返却物は **読み取り専用扱い** (破壊的変更しない) が規約。
- **PERF-3 リター推定の座位独立分解**: `litter_inference.py` を、結合 (joint) 子猫遺伝子型集合の物質化から **座位単位のビットマスク照合** へ置換。メンデル分離が座位ごと独立である等価性に基づく。`possible_kitten_genotypes` ベースの旧経路は廃止。
- **PERF-4 逆引きの追加最適化**: **見送り** (PERF-2 だけで目標達成のため、不要な複雑化を避けた)。さらに大規模化する場合のみ再検討。
- **PERF-5 フロント表示**: `frontend/lib/api.ts` の `describeError` を改修し、配列形式422 の **日本語検証メッセージ (上限超過等) を表示**。英語の pydantic 検証エラーは従来どおり総括文言にフォールバック (`Value error,` 接頭辞は除去)。

### 計測 (実測・2026-06-29)
| 対象 | 改善前 | 改善後 |
|------|--------|--------|
| 逆引き 40頭 / 60頭 | 5,866ms / 12,947ms | 341ms / 193ms |
| リター Black×Black 1子 | 1,309ms | 18.5ms |
| リター **Silver Tabby×Silver Tabby 1子** | **113,096ms** | **341ms** (実機プロキシ経由 0.32s) |

### 検証
- `pytest -q` **151 passed** (既存148 + 新規3: リター新旧 brute-force 等価テスト・逆引き猫上限・リター子猫上限)。
- 出力同一性は **130×204 / golden_crosses 無変更通過** + **リター新旧等価テスト** で担保。
- フロント **typecheck / lint クリーン**。
- **実機確認** (uvicorn:8000 + next:3000、プロキシ :3000→:8000): golden path / 逆引き / リター正常、上限超過は 422 + 日本語文言、最悪ケース 0.32s。

---

## 2. 計算機の現状 (バックエンド)

- **遺伝計算**: 全座位 Punnett + モード別の親遺伝子型生成 (`engine.py` / `master_data.py`)。3モード実装済み。**純粋計算はプロセス内メモ化** (PERF-2)。
- **逆引き** (`reverse_lookup.py`): 登録猫から目標カラー成立候補を分類。登録猫 ≤ 50。
- **リター推定** (`litter_inference.py`): 観察子猫群から父母遺伝子型候補を座位独立分解で絞り込み。観察子猫 ≤ 12。
- **名前 (入力)**: `cat_color_master.csv` 経由で alias 入力受理・canonical 解決 (`color_master.py`)。
- **名前 (出力表示)**: canonical 正規化の後段で `cat_color_display_alias_map.csv` 経由の猫種別表示名・Van 正規化 (`display_alias_map.py`)。
- **API**: `POST /api/v1/calculate` / `/reverse-lookup` / `/litter-inference` / `/colors` / `/breeds` / `/feedback`。

## 3. フロントエンドの現状

- `frontend/` に Next.js 14 (App Router) / React 18 / TypeScript strict / Tailwind。通常シミュレーター・逆引き・リター推定の3タブ。
- API レスポンスは Zod で narrow (`lib/schema.ts`)。422 detail は **文字列 / 配列の2形** を `lib/api.ts` `describeError` が処理 (配列の日本語メッセージは表示、英語は総括文言)。
- `/api/*` は `next.config.mjs` の rewrite で `BACKEND_ORIGIN` (既定 `http://localhost:8000`) へプロキシ。

---

## 4. 次回以降の作業候補

### 優先度: 中〜高 (フロント続き)
1. **フロントのテスト基盤**: 現状 `frontend/` にテストランナーが無い。`describeError` 等のユニットテスト、`typecheck`/`build` の PR ゲート化。
2. **逆引き入力UXの統一**: 通常シミュレーター側の最近選択履歴を逆引きの両親猫登録へ共有。
3. **デプロイ構成**: フロント (Vercel 等) とバックエンド (Cloud Run) 接続・`BACKEND_ORIGIN` 運用 (運用正本と整合)。

### 優先度: 中 (バックエンド継続)
4. **CI 整備**: GitHub Actions で `pytest -q` を PR ゲート化 (運用正本 §6)。パフォーマンス回帰は環境依存のため CI ゲート化せず計測ログ参考に留める方針。
5. **表示名マスタの経路拡張**: 猫種固有パターン細分、Mitted/Bi-Color の猫種文脈表示、親入力での明示 Van 保持。

### 優先度: 設計判断が要る (将来フェーズ)
6. **review_required 遺伝子座の確定**: Wb系 / Point/Mink/Sepia の C系 (`cat_color_master_review.md` §8)。
7. **carrier_exploration の拡張**: I-locus の扱い、猫種文脈併用、mink シナリオ。

---

## 5. 既知の留意点 (落とし穴)

### パフォーマンス (本フェーズ追加)
- **エンジンのキャッシュ返却物は破壊的変更しない**。`calculate_report` / `_resolve_parent_genotypes` / `_build_gametes` は同一オブジェクトを返し得る (frozen dataclass / 読み取り専用前提)。結果リストを mutate する変更を入れる場合はキャッシュ方針ごと見直す。
- **リター推定の座位独立分解は「メンデル分離が座位ごと独立」前提**。座位間に依存を持つルール (連鎖等) を導入する場合、ビットマスク照合の等価性が崩れる。変更時は新旧等価テスト (`test_litter_surviving_pairs_match_bruteforce`) を必ず維持・更新する。
- **入力上限 (50 / 12)** は `api.py` 定数。引き上げる場合は最悪ケースの計算量を再計測してから。

### フロントエンド
- **API レスポンスは必ず Zod で narrow**。`api.py` の契約を変えたら `lib/schema.ts` を同期。
- **422 detail は2形ある** (文字列 / 配列)。`describeError` は配列の日本語メッセージのみ表示し英語は総括文言にする。サーバ側の検証メッセージは日本語で投げると UI に出る。

### バックエンド
- **表示名解決は canonical 正規化の「後」**。順序を入れ替えると Ebony 等が Black へ戻る。
- **A/Wb は normal で展開しない**。**carrier_exploration は通常結果に混ぜない**。
- 計算ロジック修正タスクで `Dockerfile`/`.github/workflows/`/Cloud Run 等の運用系を触らない (運用正本 §3.3)。
