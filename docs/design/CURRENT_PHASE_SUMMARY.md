# 直近フェーズ サマリー (引き継ぎ用)

最終更新: 2026-06-25  
位置づけ: **次フェーズ着手時に最初に読む唯一の引き継ぎ** (AGENTS.md §5.0 ローリング運用 / 常に1件)。  
正本は `docs/architecture/` 配下 (AGENTS.md §0 / V9 正本3冊 + `cat_color_master.csv` 系)。本書は要約であり正本ではない。

---

## 1. このフェーズで完了したこと (2026-06-24〜25)

### A. 色柄マスター唯一正本 `cat_color_master.csv` の作成・確定
- 元データ `色柄データUTF8Ver.csv` (407名) と遺伝子座マップ `cat_color_genetic_map.csv` を突合し、機械可読な色柄概念マスター **`docs/architecture/cat_color_master.csv` (385概念)** を生成。仕様 `cat_color_master_schema.md` / 差分レビュー `cat_color_master_review.md` / 生成器 `scripts/build_cat_color_master.py` (再実行で同結果)。
- **別名は独立行** (固有 ColorId + `Status=alias`)。**alias 解決は専用カラム `CanonicalColorId` を機械可読の唯一根拠**とする (`Notes` は人間用メモ)。
- 内訳: canonical 266 / alias 33 / breed_specific 84 / excluded 3 / review **0**。元データ 407件カバレッジ 100%、alias 解決 100%。
- 主な分類確定 (schema §12):
  - **Pt→Patched** 解釈、CFA/TICA差 (Blue Cream=Blue Tortie 等) は alias 統合。
  - 猫種固有 (Ebony/Sable/Ruddy/Mink/Mitted/Leopard 等) は breed_specific + `DisplayAllowed=false`。
  - **Peke-Face/P-F** は形態語 → alias 化。**Chinchilla/Shell** は計算上同一 (黒/青系=Chinchilla, 赤/ク系=Shell を canonical, 表示は基色で使い分け)。**Shaded** は別概念で維持。**Golden** は non_silver+wideband/tipping。**Smoke** は solid+I/- の別系統。
  - **Smoke×Tortie/Calico** 確定 (Smoke単独=excluded, Calico Smoke→tortie_smoke_white 等)。
  - **Van(S/S) は -White(S/s) と別概念**として保持 (collapse しない)。一般表示の Van→-White 正規化は表示名マスタ (未整備) が担う。`CanonicalColorId` は全行で「遺伝的同一性」を一貫して意味する。
  - **C-locus 猫種固定**を補完 (Colorpoint Shorthair=cs/cs, Tonkinese=cb/cs)。

### B. 計算エンジンへの接続 + 計算ロジック修正
- **名前解決レイヤ `cat_breeding_simulator/color_master.py`** を新設。入力 alias を canonical へ解決、出力名を canonical PrimaryName へ正規化 (略記 Pt/Mc/Sp/Tc/-W 展開で突合)。`engine.py` の遺伝計算は不変、入出力の「名前」だけ正規化。breed_specific/excluded/review は通常モード入力で拒否。
- **A-locus 仕様改訂 (重要)**: normal_mode では A を A/A 相当に固定し **A/a を展開しない** (V9 §2.4 カテゴリA')。これによりタビー親から a/a 前提の Solid/Tortie/Calico/Smoke が誤出力されなくなった。**Wb も normal で非展開**。D/I/Mc/Ta は従来どおり X/- 展開。

### C. 計算モード分離 (3モード実装完了)
- `master_data.py`: 色ごと基準遺伝子型 `COLOR_BASE_LOCI` + **`build_parent_genotypes(color, sex, mode, carriers)`** を新設。
- **normal**: 未明示キャリアを閉じる (A/B/C/Wb 非展開、D/I/Mc/Ta のみ展開)。
- **explicit_carrier**: `sire_carriers`/`dam_carriers` で指定座位のみ上書き開放。
- **carrier_exploration**: 「**片親が劣性を完全発現 → 相手がそのキャリアだったら**」のみを条件付きシナリオ化 (両親とも隠れキャリアの自動生成は禁止)。対象 A(a/a)/B(b/b,bl/bl)/C(cs/cs,cb/cb,cb/cs)/D(d/d)。**事前確率は掛けない**。`results`(normal) と `carrier_exploration_results` を完全分離。
- `CalculationReport` に `mode`/`opened_loci`/`closed_loci`/`assumptions`/`carrier_exploration_results` を追加。API も後方互換 (additive) で `mode`/`diagnostics`/`carrier_exploration_results` を返す。

### D. テスト
- `tests/test_mode_carrier_calculation.py` 新設 (座位別 normal/explicit + carrier_exploration)。
- `tests/test_cross_130_204_output_validity.py` / `test_calculator_api.py` を仕様改訂に追随。
- **pytest 36 passed** (130×204 回帰・不可逆ルール・API 互換・モード/キャリア)。

---

## 2. 計算機の現状

- **遺伝計算**: 全座位 Punnett + モード別の親遺伝子型生成。`engine.py` / `master_data.py` / `color_master.py`。
- **名前**: `cat_color_master.csv` 経由で alias 入力受理・canonical 出力。
- **API**: `POST /api/v1/calculate`。`mode` (normal/explicit_carrier/carrier_exploration)、`sire_carriers`/`dam_carriers`。レスポンスは `results` + `mode` + `diagnostics`(opened/closed/assumptions/確率) + `carrier_exploration_results`。
- **130×204 normal** は全出力タビー/パッチドタビー系・合計100%・unmatched 0。

---

## 3. 次回以降の作業候補

### 優先度: 中〜高
1. **表示名マスタ `cat_color_display_alias_map.csv` 整備**: Van→-White の一般表示正規化、Oriental 文脈の Ebony/Lavender/Chestnut 表示復元、Abyssinian の Ruddy 等の猫種別表示名。データ正本 V9 §4 のスキーマ準拠。
2. **UI / フロントエンド**: 親色2つ + breed + mode 入力、結果 (results / diagnostics / carrier_exploration_results) 表示。技術スタックは Next.js + Tailwind (ルート AGENTS 既定) を想定。
3. **CI 整備**: GitHub Actions で `pytest -q` を PR ゲート化 (運用正本 §6)。※計算ロジック修正中は運用系を触らない原則に注意。

### 優先度: 中〜低 (データ/精緻化)
4. **review_required 遺伝子座の確定**: Wb系 (Shell/Shaded/Chinchilla/Golden) と Point/Mink/Sepia の C系。`cat_color_master_review.md` §8 参照。
5. **猫種 C 固定の追加**: Javanese(24)/Snowshoe(42) 等のポイント前提種を cs/cs 固定するか (前回「固定候補」として保留)。
6. **未シード別名の追加**: `Dilute Tortoiseshell` 等、元データに無い登録別名を alias として受理可能にする (`ALIAS_TARGETS`/Aliases)。
7. **Van 概念の名称重複統合**: `Van Calico`(47) と `Tortoiseshell-White Van`(355) など同一遺伝概念の統合 (review.md §10)。

### 優先度: 設計判断が要る (将来フェーズ)
8. **carrier_exploration の拡張**: I-locus の扱い、猫種文脈との併用、mink の詳細シナリオ。
9. **State-key による本格正本化**: engine の逆引き (GENOTYPE_TO_COLOR_MAP) を master の状態カラム駆動へ置換 (現在は名前正規化レイヤ方式)。影響範囲大。

---

## 4. 既知の留意点 (落とし穴)

- **A/Wb は normal で展開しない**。タビー/ワイドバンド親から Solid/Smoke/Calico/wideband を normal で出してはいけない (回帰テストで担保)。
- **Van は collapse しない**: 入力 Van は S/S を保持。一般表示の Van→-White は表示名マスタの担当 (master の CanonicalColorId に流用しない)。
- **carrier_exploration は通常結果に混ぜない**。事前確率を掛けない (条件付きのみ)。両親とも隠れキャリアの自動生成は禁止。
- 計算ロジック修正タスクで `Dockerfile`/`.github/workflows/`/Cloud Run 等の運用系を触らない (運用正本 §3.3)。
