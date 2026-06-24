# 直近フェーズ サマリー (引き継ぎ用)

最終更新: 2026-06-24  
位置づけ: **次フェーズ着手時に最初に読む唯一の引き継ぎ** (AGENTS.md §5.0 ローリング運用 / 常に1件)。  
正本は `docs/architecture/` 配下 (AGENTS.md §0 / V9 正本3冊 + `cat_color_master.csv` 系 + `cat_color_display_alias_map.csv`)。本書は要約であり正本ではない。

---

## 1. このフェーズで完了したこと: 表示名マスタ `cat_color_display_alias_map.csv` 整備

### A. 表示名マスタの新設 (データ正本 V9 §4 準拠)
- `docs/architecture/cat_color_display_alias_map.csv` を新設 (36 行)。生成器 `scripts/build_cat_color_display_alias_map.py` (再実行で同結果、`scripts/README.md` 登録済み)。
- §4.2 必須カラム (AliasId / CanonicalPhenotype / GeneralDisplayName / Breed / BreedSpecificDisplayName / Registry / OfficialStatus / DisplayContext / Priority / Notes) に準拠。
- **CanonicalPhenotype 列はエンジンが実際に出力する内部表現型名 (canonical 正規化済み)** を置く (`cat_color_master.csv` の CanonicalColorId とは別概念。逆引き突合キーのため一致が必須)。
- シード範囲は「名指し例 + 経路網羅」:
  - **Oriental** (Shorthair/Longhair): Black→Ebony / Chocolate→Chestnut / Lilac→Lavender を、solid / smoke / tabby / silver_tabby について収録。
  - **Abyssinian / Somali**: Brown(Black) Ticked Tabby→Ruddy、Blue/Cinnamon/Fawn/Red、`* Silver Ticked Tabby`→`* Silver`。

### B. 解決レイヤ + エンジン統合 (ハードコード置換)
- **解決レイヤ `cat_breeding_simulator/display_alias_map.py`** を新設。`resolve_display_name(name, breed)` が ①白斑接尾辞 (`-White` / `-White Van`) 分離 → ②猫種別呼称変換 (猫種は部分一致照合: `Oriental Shorthair`→`Oriental`) → ③一般 Van→-White 正規化 (§5.2) → ④接尾辞再付与、を行う。
- **engine.py の `_apply_breed_color_names` ハードコードを削除**し、CSV 駆動へ置換 (データ正本 §1.1「コードに固定値を書かない」準拠)。`_post_process_color_name` の適用順を `clean → simplify_patterns → COLOR_MASTER.canonical_name → DISPLAY_ALIAS_MAP.resolve_display_name` に変更。
  - **順序が重要**: Ebony/Chestnut/Lavender は master では Black/Chocolate/Lilac の alias。canonical 正規化を先に、表示名解決を後に置かないと猫種別呼称が一般名へ戻る。

### C. テスト
- `tests/test_calculator_api.py` に表示名解決の回帰テストを追加 (Oriental 復元 / 一般表示は canonical 維持 / Abyssinian・Somali Ruddy 保持 / Van→-White / -White 合成)。
- **pytest 42 passed** (既存 36 + 新規 6)。Abyssinian の出力は置換前と同一 (回帰なし)。

---

## 2. 計算機の現状

- **遺伝計算**: 全座位 Punnett + モード別の親遺伝子型生成 (`engine.py` / `master_data.py`)。3モード (normal / explicit_carrier / carrier_exploration) 実装済み。
- **名前 (入力)**: `cat_color_master.csv` 経由で alias 入力受理・canonical 解決 (`color_master.py`)。
- **名前 (出力表示)**: canonical 正規化の後段で `cat_color_display_alias_map.csv` 経由の猫種別表示名・Van 正規化 (`display_alias_map.py`)。
- **API**: `POST /api/v1/calculate`。`mode` / `sire_carriers` / `dam_carriers` / `breed`。

---

## 3. 次回以降の作業候補

### 優先度: 中〜高
1. **フロントエンド (#2)**: 親色2つ + breed + mode 入力、結果 (results / diagnostics / carrier_exploration_results) 表示。Next.js + Tailwind。← **ユーザー指定: 本フェーズの次に着手**。
2. **表示名マスタの経路拡張**: 猫種固有のパターン細分 (Mackerel/Spotted/Classic の組合せ)、Mitted/Bi-Color の猫種文脈表示 (§5.3/§5.4)、親入力での明示 Van 保持 (入力レベルのシグナル伝搬)。
3. **CI 整備**: GitHub Actions で `pytest -q` を PR ゲート化 (運用正本 §6)。※計算ロジック修正中は運用系を触らない原則に注意。

### 優先度: 中〜低 (データ/精緻化)
4. **review_required 遺伝子座の確定**: Wb系 (Shell/Shaded/Chinchilla/Golden) と Point/Mink/Sepia の C系。`cat_color_master_review.md` §8 参照。
5. **猫種 C 固定の追加**: Javanese/Snowshoe 等のポイント前提種を cs/cs 固定するか (保留)。

### 優先度: 設計判断が要る (将来フェーズ)
6. **carrier_exploration の拡張**: I-locus の扱い、猫種文脈との併用、mink の詳細シナリオ。
7. **State-key による本格正本化**: engine の逆引き (GENOTYPE_TO_COLOR_MAP) を master の状態カラム駆動へ置換 (影響範囲大)。

---

## 4. 既知の留意点 (落とし穴)

- **表示名解決は canonical 正規化の「後」**。順序を入れ替えると Ebony 等が Black へ戻る (回帰テストで担保)。
- **CanonicalPhenotype 列はエンジン内部出力名と一致必須** (master の CanonicalColorId と混同しない)。エンジン出力は黒アグーチのタビーを `Brown Tabby`、黒シルバータビーを `Silver Tabby` と出す点に注意。
- **A/Wb は normal で展開しない**。タビー/ワイドバンド親から Solid/Smoke/Calico/wideband を normal で出さない。
- **carrier_exploration は通常結果に混ぜない**。事前確率を掛けない (条件付きのみ)。両親とも隠れキャリアの自動生成は禁止。
- 計算ロジック修正タスクで `Dockerfile`/`.github/workflows/`/Cloud Run 等の運用系を触らない (運用正本 §3.3)。
