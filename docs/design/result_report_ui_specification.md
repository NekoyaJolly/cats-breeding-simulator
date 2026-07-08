# フェーズ指示書 — 結果レポート化 ＋ モード2つ化

位置づけ: **現在進行中フェーズの指示書** (AGENTS.md §5.0 ローリング運用 / 0〜1件)。
正本は `docs/architecture/` 配下 (V9 正本4冊 + CSV 系)。本書はフェーズ完了時に V9 正本へ統合し、**削除**する。
起案日: 2026-07-08

---

## 0. ゴール

1. **結果画面をレポート形式へ全面刷新**する。現行のバッジ羅列をやめ、以下HTMLプロトタイプの構成をそのままアプリUIの計算結果表示として採用する。
   - プロトタイプ: 本セッションで作成した「座位検証10ケース」レポート (確定色 → 全分布(周辺確率) → 推定色 の3層構成、暗め背景、改良スウォッチ)。
   - 既存の `ResultView.tsx` のバッジ表示を土台にはしない。まずプロトタイプ通りの表示にし、細部は後続で詰める。
2. **計算モードを `normal` / `explicit_carrier` の2つに削減**し、`carrier_exploration` (全キャリア探索モード) を **UI・API・エンジン・テストから全撤去**する。

### 撤去の根拠 (調査で確定)

- 通常モードの **周辺確率 `results`** と **推定色 `conditional_color_groups`** が、`carrier_exploration` の目的 (隠れキャリア由来カラーの探索) を**カバーし、かつ上回る**。
  - `carrier_exploration`: 「片親が劣性発現 × 相手がキャリア」シナリオのみ (両親とも隠れキャリアは自動生成しない)。
  - `conditional_color_groups`: 上記①に加え、「両親とも優性発現 → 両親ヘテロ仮定」シナリオ②も提示 (逆推論ラベル付き)。
- **依存関係の安全性 (検証済)**: `conditional_color_groups` の計算経路 (`_build_conditional_color_groups` → `_conditional_scenario_results` → `_resolve_parent_genotypes` / `_override_carrier_locus` / `_aggregate_cross`) は、`carrier_exploration` の経路 (`_calculate_carrier_exploration` / `_build_carrier_scenarios` / `_compute_carrier_scenario`) を**一切呼ばない**。よって後者を削除しても推定色は壊れない。
- コード内に使われない探索経路を残すと、人・エージェントの認識/処理の混乱源になる (単一ソース明確化のため撤去)。

---

## 1. レポート仕様 (新・結果画面)

### 1.1 データ源

バックエンドは既に必要な要素を返している (`/api/v1/calculate` レスポンス)。**表示に必要なデータ追加は不要**、フロントは表示層の付け替えが中心。

| レポート区画 | API フィールド | 意味 |
|--------------|----------------|------|
| 確定色 | `confirmed_results` | 隠れキャリアに依らず必ず出る色 (カテゴリA 非展開)。normal のみ非 null |
| 全分布 (周辺確率) | `results` | 実際に表示する全色柄。カテゴリA (A/D/I/Mc/Ta) 展開込みの周辺確率 |
| 推定色 (もし出たら) | `conditional_color_groups` | 確定色に無いが隠れキャリアがあれば出る色。scenario / 逆推論ラベル付き |
| 親色不在注釈 | `parent_color_notes` | 入力した親色が子に出ないときの注釈 |

### 1.2 画面構成 (交配1件あたり)

1. **ヘッダー**: 父 × 母 (毛色スウォッチ + 色名)。猫種があれば併記。
2. **確定色**: 保因に依らず必ず出る色。性別マーク (♂/♀) + スウォッチ + 色名 + 確率。最も目立たせる。
   - `confirmed_results` が空のケース (例: 優性白 epistasis) は、その旨の注記を出し全分布を参照させる。
3. **全分布 (周辺確率)**: ♂ / ♀ 別の一覧。スウォッチ + 色名 + 確率 + 確率バー。低確率も表示 (アコーディオン集約は後続の細部調整で検討)。
4. **推定色 (もしこの色が出たら)**: scenario 単位のグループ。「対象の親 (父/母/両親) が ◯◯ 保因」バッジ + 逆推論ラベル + 色チップ (スウォッチ + 性別)。
5. **フッター**: 合計100% / 未分類0% の健全性表示。

### 1.3 スタイル方針

- **背景**: 白基調をやめ、温かみのある暗め (眩しさ低減)。テーマ対応 (light/dark 両対応)。
- **可読性**: 情報密度は高く、視線移動を楽に (確定 → 全分布 → 推定 の縦導線)。モバイル1列 / デスクトップ2列。
- **色名は常にテキスト併記** (スウォッチは近似の視認補助)。

### 1.4 スウォッチ仕様 (`coatColorSwatch.ts` 改訂)

プロトタイプで確定した改良を実アプリの `frontend/lib/coatColorSwatch.ts` に反映する。

- **Calico** = トーティ (黒×赤の2色) **＋ 白** の3色 (三毛)。
- **Dilute Calico** = 希釈トーティ (Blue Cream = 青×クリームの2色) **＋ 白** の3色。
  - 現行バグ: 「dilute」を希釈語として解釈できず、Dilute Calico が Calico と同色 (黒×赤) で描画され、かつ両者とも白が乗っていない。
  - 修正方針: Calico → `Tortoiseshell` ベース、Dilute Calico → `Blue Cream` ベースに読み替え、いずれも白斑くさびを付与。
- **White / -White (白斑)** の表現はプロトタイプの方式を採用 (White=ほぼ白、-White=白のくさびを重ねたバイカラー)。
- 上記以外 (下地→先端ティッピング、トーティ2色、タビー横縞、ポイント淡色) は既存ロジックを踏襲。

---

## 2. モード削減 / carrier_exploration 撤去

### 2.1 撤去スコープ

| 領域 | ファイル (参照数) | 作業 |
|------|-------------------|------|
| エンジン | `engine.py`(18), `master_data.py`(2) | `_calculate_carrier_exploration` / `_build_carrier_scenarios` / `_compute_carrier_scenario` / `CarrierScenario` / mode 分岐 / 探索用 locus 既定値 を削除。`SUPPORTED_MODES` から除外 |
| API | `api.py`(7) | mode 値 `carrier_exploration` / `carrier_exploration_results` フィールド / `CarrierScenarioEntry` を削除 (**後方互換を壊す変更 §4**) |
| フロント | `BreedingForm.tsx`, `ResultView.tsx`(3), `schema.ts`(3), `i18n.ts`, `ResultView.test.tsx` | モード選択肢から除外、レポート化に伴い関連表示を除去 |
| テスト | `test_mode_carrier_calculation.py`(18), `test_golden_crosses.py`(1)+`golden_crosses.json`(28), `test_parent_color_notes.py`(2) | carrier_exploration ケース削除、golden 再生成 |
| 正本 | 下記 §3 | §2.3 削除・モード一覧・表示/スウォッチ仕様の改訂 |

> 対象外 (触らない): `docs/archive/**`、`.artifacts/**` (アーカイブ・作業痕跡)。

### 2.2 API 変更 (破壊的)

- リクエスト: `mode` の許容値から `carrier_exploration` を除外 (指定時は 422)。
- レスポンス: `carrier_exploration_results` フィールドと `CarrierScenarioEntry` を削除。
- 破壊的変更 (§4)。外部利用者向けの告知が必要な場合はリリースノートに明記する。

---

## 3. V9 正本 改訂対象

| 正本 | 該当箇所 | 改訂内容 |
|------|----------|----------|
| 01_シミュレーター正本 | §0 (13-15行) | モード列挙を「通常 / 明示キャリア」の2つに |
| 〃 | §2.3 (129-149行) | **全キャリア探索モードの節を削除** (または「廃止」注記へ) |
| 〃 | §2.1 注記 (94行) 他 | 「全キャリア探索モードでのみ扱う」→「明示キャリアモードでのみ扱う」等の文言修正 |
| 〃 | 227 / 300 / 476 / 758行 | チェックリスト・診断フィールド・テスト観点から carrier_exploration を除去 |
| 〃 | §6 表示仕様 (新規/改訂) | **結果レポート表示仕様** (確定/全分布/推定の3層、スウォッチ仕様) を追記 |
| 02_データ正本 | 2箇所 | スウォッチ/表示仕様と carrier_exploration 参照の整合 |
| 03_運用正本 | 1箇所 | テスト運用から carrier_exploration を除去 |
| cat_color_master_schema.md | 2箇所 | carrier_exploration 参照の整合 |
| AGENTS.md | ドメイン原則 §1 | 3モード → 2モードへ。「やってはいけないこと」の整合 |

> 実装と正本更新は別コミット (AGENTS.md §5.1)。設計書上書きは1ファイル1コミット (§6.4)。

---

## 4. チケット分割

| ID | 内容 | 主な完了条件 |
|----|------|--------------|
| **T1** | V9 正本 + AGENTS.md 改訂 (§3 の全箇所) | 正本からモードが2つに統一され、レポート表示/スウォッチ仕様が記載される。1ファイル1コミット |
| **T2** | エンジン/API から carrier_exploration 撤去 | `SUPPORTED_MODES` が2つ。carrier_exploration 指定で 422。`carrier_exploration_results` フィールド廃止。既存の normal/explicit テスト緑 |
| **T3** | テスト整理 + golden 再生成 | carrier_exploration ケース削除、`golden_crosses.json` 再生成 (差分を目視レビュー)、全テスト緑 |
| **T4** | フロント: モード選択削除 | BreedingForm からモード選択が消え、schema/i18n が2モード整合。型/ビルド緑 |
| **T5** | フロント: ResultView レポート化 | プロトタイプ通りの3層レポート表示 (確定/全分布/推定 + 暗め背景)。実機で golden path 確認 |
| **T6** | `coatColorSwatch.ts` 改良反映 | Calico/Dilute Calico の三毛3色化、White/-White 表現。スウォッチ単体テスト追加 |

推奨順: **T1 → T2 → T3 → (T4 / T6) → T5**。正本先行。T6 は T5 と並行可。

### 4.1 進捗 (2026-07-08)

- ✅ **T1** 正本 + AGENTS.md 改訂 / ✅ **T2** エンジン・API から carrier_exploration 撤去 /
  ✅ **T3** テスト整理・golden 再生成 / ✅ **T4** フロントのモード削除 / ✅ **T6** スウォッチ三毛修正
- ✅ **T5** ResultView のレポート化。**フェーズ完了**。

### 4.2 T5 の設計判断 (確定・実装済)

プロトタイプ (座位検証10ケースレポート) をアプリUIへ採用する際の判断は、ユーザー確認のうえ以下で確定・実装した。

1. **配色/背景**: **独自トークン** (`--r-*` CSS 変数) の暖かいダーク島。アプリの slate 体系から独立し、白基調の眩しさを解消。
2. **i18n**: **en/ja 二言語対応** (`i18n.ts` にレポート用ラベルを追加)。
3. **既存構造の置換範囲**: `ResultView` を**全面置換**。有用な補助情報 (AOC 説明 / 親色不在注釈 / 座位解説 / 通常モード注記 / 診断) はレポートの体裁に載せ替えて保持。
4. **低確率カラー**: 全分布の **1%未満をアコーディオン集約** (性別ごと「1%未満 · N色」で展開)。

構成: 確定色 (chips) → 全分布 (♂/♀ スウォッチ + 確率バー) → 推定色 (座位別・逆推論) → 補助情報 → 診断。

---

## 5. テスト方針

- **削除**: `test_mode_carrier_calculation.py` の carrier_exploration 依存ケース、`golden_crosses.json` の carrier_exploration エントリ。
- **再生成**: `GOLDEN_REGEN=1 python -m pytest tests/test_golden_crosses.py` で golden を再生成し、差分を git で目視レビューしてコミット。
- **維持**: `tests/test_cross_loci_mapping.py` (本フェーズ前に追加した座位→出力 oracle)。
- **追加**: `coatColorSwatch` の Calico/Dilute Calico/White スウォッチ単体テスト、ResultView のレポート構造テスト。
- UI 変更は dev サーバーで golden path / edge case を実機確認 (AGENTS.md §6.3)。

---

## 6. 未確定事項 (実装時に詰める)

- 全分布の低確率カラーのアコーディオン集約の要否・閾値 (§2.1 注記が UI 抑制を許容)。
- レポートの配色トークン (暗め背景) を既存フロントのテーマ体系にどう載せるか。
- API 破壊的変更の外部告知/バージョニングの要否。
