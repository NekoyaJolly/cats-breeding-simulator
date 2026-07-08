# 猫色柄マスター唯一正本 cat_color_master.csv 仕様書
作成日: 2026-06-24  
位置づけ: **色柄概念マスター `cat_color_master.csv` のスキーマ定義・運用ルールの正本**

---

## 0. 本書の位置づけ

- `docs/architecture/cat_color_master.csv` は、猫の遺伝学シミュレーターで使用する**色柄概念の唯一正本 (single source of truth)** である。
- 既存の遺伝定義 [`cat_color_genetic_map.csv`](./cat_color_genetic_map.csv) と表示名定義 (`cat_color_display_alias_map.csv`) は、本マスターを基準に整合させていく。本マスターと既存CSVが矛盾する場合は、レビュー (`cat_color_master_review.md`) で差分を可視化し、人間が確定する。
- 本マスターは [`scripts/build_cat_color_master.py`](../../scripts/build_cat_color_master.py) で生成・再生成できる。手編集する場合はスクリプトの決定テーブルにも反映し、再生成で同じ結果が得られる状態を保つ。
- **エンジン接続 (2026-06-24)**: 計算エンジンは名前解決レイヤ [`cat_breeding_simulator/color_master.py`](../../cat_breeding_simulator/color_master.py) 経由で本マスターを使用する。**入力**色名を PrimaryName / Aliases / SourceNames から検索し canonical 概念へ解決 (alias 受理)、**出力**色名を `CanonicalColorId` 経由で canonical PrimaryName へ正規化する。`Status=breed_specific` は猫種未指定の通常モードで拒否、`excluded` / `review` は入力拒否する。

> **名前の正本化に専念**する設計は維持する。遺伝計算ロジック (`engine.py` の遺伝子型計算) と計算モードの挙動 ([`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md)) は変更せず、エンジンの入出力の「名前」だけを本マスターで正規化する (State-key による本格再構築は将来フェーズ)。

---

## 1. 1 行の意味 — 「表示名」ではなく「色柄概念」

`cat_color_master.csv` の **1 行は 1 つの色柄概念**を表す。表示名そのものの一覧ではない。

- 1 概念 = 1 行 = 一意の `ColorId`。
- 同一概念に複数の元データ名 (コード) が紐づく場合、それらは 1 行に集約し `SourceCodes` / `SourceNames` に全件保持する。
- 別名 (CFA/TICA/実務/猫種呼称差・タイポ・略称) は失わない。下記「別名の持ち方」に従う。

---

## 2. 別名 (alias) の持ち方 — 独立行方式 (確定事項)

別名は**独立した行**として保持する (本プロジェクトでの確定方針)。

- 各別名は**固有の `ColorId`** を持ち、`Status=alias` とする。
- 別名行は専用カラム **`CanonicalColorId`** に、出力時に寄せるべき canonical 概念の `ColorId` を持つ (§4)。**機械処理は必ず `CanonicalColorId` を参照する**。`Notes` は人間用メモ欄であり、解決情報の機械的な根拠にしてはならない。
- これにより、元データの全コード・全名が行単位で追跡可能になり、`ColorId` の一意性 (重複禁止) も保てる。
- `Aliases` 列は、その行の `PrimaryName` の**綴り違い・元データ表記・既知の登録団体別名**を `|` 区切りで補助的に列挙する用途に使う (別名行を作るほどではない軽微な表記揺れ)。

> 補足: 依頼プロンプトのスキーマには「ColorId は重複禁止」「1 行=1 概念」と「別名は同じ ColorId に紐づける」が併記され、文面上は矛盾する。本プロジェクトでは **別名も独立行 (固有 ColorId + Status=alias + resolves_to)** を採用してこの矛盾を解消した。

---

## 3. カラム定義

| カラム | 型 | 説明 |
|---|---|---|
| `ColorId` | string | 機械用の一意ID。snake_case。§4 の命名ルールに従う |
| `CanonicalColorId` | string | 機械可読な解決先 `ColorId`。alias 解決の唯一の根拠 (§4.1) |
| `Status` | enum | `canonical` / `alias` / `breed_specific` / `excluded` / `review` (§5) |
| `PrimaryName` | string | この概念の通常表示名 (正規化後) |
| `Aliases` | string | 軽微な表記揺れ・別名。`|` 区切り |
| `RegistryNotes` | string | CFA/TICA/日本団体等の呼称差・団体タグのメモ |
| `BreedContext` | enum | `general` または猫種名 (§7) |
| `ColorGroup` | enum | `solid` / `tabby` / `silver_tabby` / `patched_tabby` / `tortie` / `calico` / `smoke` / `shaded` / `point` / `mink` / `sepia` |
| `BaseSeries` | enum | `black` / `chocolate` / `cinnamon` / `red` / `unknown` (B/O 由来の基色) |
| `OrangeState` | enum | `non_orange` / `orange` / `tortie` / `unknown` |
| `Dilution` | enum | `dense` / `dilute` / `unknown` |
| `AgoutiState` | enum | `agouti` / `solid` / `not_applicable` / `unknown` |
| `SilverState` | enum | `silver` / `smoke` / `cameo` / `non_silver` / `unknown` |
| `WhiteState` | enum | `none` / `white` / `high_white` / `mitted` / `bicolor` / `van` / `unknown` |
| `PointState` | enum | `full` / `point` / `mink` / `sepia` / `unknown` |
| `PatternState` | enum | `none` / `tabby` / `mackerel` / `classic` / `spotted` / `ticked` / `shaded` / `shell` / `unknown` |
| `SexRestriction` | enum | `unrestricted` / `female_only` / `male_only` (§8) |
| `DisplayAllowed` | bool | `true` / `false` (§6) |
| `InputAllowed` | bool | `true` / `false` (§6) |
| `OutputPriority` | int | 数値。高いほど優先 (同遺伝子型に複数名が競合した際の選択に使う) |
| `SourceCodes` | string | 元データ Code を `|` 区切り。`[map]` 由来は別途 Notes/SourceNames に記載 |
| `SourceNames` | string | 元データ名を `|` 区切り (正規化前の原文を保持) |
| `GeneticRuleSource` | enum | `current_map` / `inferred` / `review_required` (§9) |
| `Notes` | string | 人間向けメモ。alias 行は `resolves_to=...` を含む |

---

## 4. ColorId 命名ルール

- 全て小文字 snake_case (`[a-z0-9_]+`)。
- `PrimaryName` を小文字化し、括弧内・記号を除去、空白とハイフンを `_` に置換して生成する。
  - 例: `Brown Tabby-White` → `brown_tabby_white` / `Peke-Face Red` → `peke_face_red` / `Blue Patched Tabby-White` → `blue_patched_tabby_white`
- 一意性を必ず保証する (重複時は末尾に連番を付与)。
- `Any` を ID・値として使わない (§10)。

### 4.1 CanonicalColorId — alias 解決の機械可読カラム

`CanonicalColorId` は、その行が最終的に寄せられる**正規概念の `ColorId`** を保持する専用カラムである。alias 解決を `Notes` の文字列パースに依存させない (人間用メモと機械情報を分離する) ために設ける。

ルール:

| Status | `CanonicalColorId` |
|---|---|
| `canonical` | 自分自身の `ColorId` |
| `alias` | 解決先の `ColorId` (`Status=canonical`、または同一概念の代表 `breed_specific` を指す) |
| `breed_specific` | 一般概念へ確実に解決できる場合はその canonical の `ColorId`。できない場合は自分自身 (一般概念へのマッピングは人間レビューに委ねる) |
| `review` / `excluded` | 確定できない場合は空欄可。空欄の場合は `Notes` に理由を記録する |

- **機械処理 (表示名解決・集計) は必ず `CanonicalColorId` を参照する**。`Notes` の文言に依存してはならない。
- `Notes` に解決先を人間向けに併記してよいが、それは参考であり機械的な根拠ではない。

バリデーション (ビルド時に強制):

1. `Status=alias` の全行に `CanonicalColorId` が入っている。
2. `Status=alias` の `CanonicalColorId` は実在する `ColorId` を参照する。
3. `Status=alias` の `CanonicalColorId` 参照先は `Status=canonical`、または同一概念の代表 `breed_specific` である (重複呼称を 1 行へ統合する場合に breed_specific を指してよい。例: `Blue Tortie Point Bi-Color` → `blue_cream_point_bi_color`)。
4. `Status=canonical` の `CanonicalColorId` は自分自身である。
5. 元データ全 Code (407 件) が少なくとも 1 行の `SourceCodes` に保持されている (元データ行の完全喪失なし)。
6. `breed_specific` は通常表示に混ざらない (`DisplayAllowed=false`)。
7. `Any` は分類値カラムに使わない (元データ名 `Any Other Color` は原文保持でよい)。

---

## 5. Status の意味

| 値 | 意味 | DisplayAllowed | InputAllowed |
|---|---|---|---|
| `canonical` | 通常計算結果として扱える正規色柄概念 | 原則 true (例外は §6) | true |
| `alias` | 入力名・別名として受け付けるが、出力は `resolves_to` の canonical へ寄せる | false | true |
| `breed_specific` | 特定猫種・特定団体文脈でのみ表示する呼称 | false | true |
| `excluded` | 元データにはあるが通常計算にも入力候補にも使わない (運用上の非カラー区分等) | false | false |
| `review` | 自動判断できず人間レビュー待ち | false | false |

- **迷ったものは必ず `review`** にする。`review` 行は `DisplayAllowed=false`, `InputAllowed=false` を原則とする。
- `review` がゼロである必要はない。不確かなものは確定せず残す。

---

## 6. DisplayAllowed と InputAllowed の違い

- **`InputAllowed`**: その `PrimaryName` を**親猫の入力色**として受け付けてよいか。
- **`DisplayAllowed`**: その `PrimaryName` を**一般文脈 (`general` / `breed_unselected`) の出力表示名**として使ってよいか。

両者は独立である。例:

- `Seal Point` … `InputAllowed=true` (Point の親を入力できる) かつ `DisplayAllowed=false` (一般候補として常時は出さない。親入力・猫種固定・明示キャリアで `cs/cs` が確定した結果としては出力され得る)。
- `Blue Tortie` (alias) … `InputAllowed=true` (入力名として受理) かつ `DisplayAllowed=false` (出力は canonical の `Blue Cream` に寄せる。希釈トーティの正規名は Cream)。

`DisplayAllowed=false` の主な構造:

- `breed_specific` / `alias` / `excluded` / `review`
- `PointState ∈ {point, mink, sepia}`
- `WhiteState ∈ {van, mitted, bicolor}` (一般文脈では `-White` に正規化)

> 重要: `DisplayAllowed` は「名前として一般表示してよいか」の基準であり、**個々の交配で実際にその色が出るかは別問題**。`A/a` や `C/cs` が未明示の場合に出すかどうかはエンジンの計算モード ([`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §2) に従う。本マスターは計算モードの挙動を規定しない。

---

## 7. BreedContext の意味

- `general`: 猫種文脈に依存しない一般概念。
- 猫種名 (`Oriental` / `Burmese` / `Tonkinese` / `Abyssinian` / `Somali` / `Ragdoll` / `Bengal` / `Birman` / `Siamese` / `Persian` 等): その猫種・団体文脈でのみ用いる呼称。
- 複数猫種で同じ固有呼称を共有する場合は `/` 区切りで保持する (例: `Abyssinian/Somali` の `Ruddy`)。

CFA/TICA 差・猫種固有呼称の扱い:

- **CFA/TICA 呼称差は別カラーとして増殖させない**。同一概念の `alias` として 1 つの canonical に統合する。
  - 希釈トーティの正規名は **Cream** に統一する (CFA 呼称を canonical、TICA の Tortie 呼称を alias)。
    - `Blue Tortie` = `Blue Cream` (`blue_cream`)
    - `Lilac Tortie` = `Lilac Cream` (`lilac_cream`)
  - `Tortoiseshell-White` / `Mike Tri Color` = `Calico` (`calico`)
  - `Blue Tortie-White` / `Blue Cream-White` = `Dilute Calico` (`dilute_calico`)
  - `Torbie` = `Patched Tabby`
- **猫種固有呼称は一般カラーとして混ぜない**。`breed_specific` とし `DisplayAllowed=false`。
  - Abyssinian/Somali: `Ruddy`
  - Abyssinian: `Sorrel`
  - Burmese: `Sable` / `Champagne` / `Platinum` / `Sepia`
  - Tonkinese: `*Mink` / `*Point` / `*Solid` class 等
  - Oriental: `Ebony` (→ 一般 `Black`) / `Lavender` (→ 一般 `Lilac`) / `Chestnut` (→ 一般 `Chocolate`)
  - Bengal: `Leopard` / `Snow` / `Marble(d)`
  - Ragdoll: `*Mitted` / `*Bi-Color`
- Oriental 等の単純基色 (`Ebony`/`Lavender`/`Chestnut`) は `alias` として一般概念へ寄せつつ `BreedContext` を保持し、猫種文脈での表示名復元は表示名 alias マスタ側で行う。

---

## 8. SexRestriction

| 値 | 意味 |
|---|---|
| `unrestricted` | オス・メス両方 |
| `female_only` | メスのみ (トーティ/トーティ&白/パッチドタビー/Blue Cream 等) |
| `male_only` | オスのみ (フェーズ1では該当なし) |

- トーティ系 (`OrangeState=tortie`, `ColorGroup ∈ {tortie, calico, patched_tabby}`) は `female_only`。
- 通常XYオスにトーティ/キャリコ/パッチド/Blue Cream/Lilac Cream を割り当ててはならない ([`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §4.3)。

---

## 9. GeneticRuleSource (遺伝子ルールの出所)

| 値 | 意味 |
|---|---|
| `current_map` | `cat_color_genetic_map.csv` に同一 Code・同一名で存在し、その遺伝子座を取り込んだ |
| `inferred` | マップに無く、名前から属性を推定した |
| `review_required` | 遺伝子座が不確かで人間確認が必要 |

`review_required` を付ける主対象 (依頼プロンプト準拠): Burmese/Tonkinese/Oriental/Abyssinian/Somali 系、Point/Mink/Sepia 系、Mitted/Bi-Color/Van 系、Shell/Shaded/Chinchilla/Wide Band 系、Cameo/Silver/Smoke 境界が曖昧なもの、`Calico Smoke` のような一般計算で扱いづらいもの、`alias`/`breed_specific`。

- **全ての色柄に無理やり遺伝子座を埋めない**。不確かなら `review_required` とし、確定しない。

---

## 10. 通常計算結果に出してよい / 出してはいけない基準

`breed_unselected` で実行する `normal_mode` の一般結果に**出してよい**のは、原則 `Status=canonical` かつ `DisplayAllowed=true` の汎用カラー (Black, Blue, Chocolate, Lilac, Cinnamon, Fawn, Red, Cream, 各 Tabby/Silver Tabby/Patched Tabby, Tortoiseshell, Blue Cream, Calico, Dilute Calico, Smoke 系, Silver 系, `-White` 系 等)。

**出してはいけない**もの (一般文脈):

- `breed_specific` の呼称、`Mitted` / `Bi-Color` / `Van`、`Sable` / `Champagne` / `Platinum` / `Ruddy` / `Sorrel` / `Ebony` / `Lavender`、`Mink` / `Sepia` / `Point`、Burmese/Tonkinese/Oriental/Abyssinian/Somali/Bengal/Ragdoll 固有名。
- ただし、猫種指定または表示体系指定がある場合は `alias` / `breed_specific` を表示に使ってよい。

> `A/a`・`C/cs` 等が未明示のときに出すかどうかの最終判断はエンジンの計算モードに従う (本マスターは名前の可否のみ定義)。

---

## 11. review の運用方法

1. `cat_color_master_review.md` の「review にした色柄」「遺伝子ルールがまだ不確かな項目」を確認する。
2. 各 `review` 行を `canonical` / `alias` / `breed_specific` / `excluded` のいずれかへ確定する。確定したら [`scripts/build_cat_color_master.py`](../../scripts/build_cat_color_master.py) の決定テーブル (`ALIAS_TARGETS` / `BREED_SPECIFIC_RULES` / `REVIEW_CONCEPTS` / `EXCLUDED_CONCEPTS`) を更新し、再生成する。
3. 遺伝子座 (`review_required`) を確定する場合は、根拠を `Notes` に残し `GeneticRuleSource` を `current_map` / `inferred` に変更する。
4. **勝手に canonical 確定しない**。判断できないものは `review` のまま残す。

---

## 12. 系統・呼称の分類ポリシー (追加レビュー判断 2026-06-24)

色柄を機械可読に整理するための系統・呼称の確定ルール。`scripts/build_cat_color_master.py` の分類ロジックに実装済み。

### 12.1 Peke-Face / P-F

- **Peke-Face は色柄概念ではなく形態・タイプ由来の混入語**。canonical にしない。
- `Peke-Face` を除去した残りの汎用カラーへ `Status=alias` で解決する (`CanonicalColorId` に解決先)。
  - 例: `Peke-Face Red` → `red`、`Peke-Face Red Tabby` → `red_tabby`、`Peke-Face Red Mackerel Tabby` → `red_mackerel_tabby`、`Peke-Face Red Tabby-White` → `red_tabby_white`。
- `DisplayAllowed=false`。旧データ互換維持のため `InputAllowed=true` は許容。`Notes` に除去・解決の旨を記録。

### 12.2 Chinchilla / Shell

- **計算上は同一の shell tipping 系概念**として扱う (別々の遺伝子計算概念にしない)。`PatternState=shell`、`GeneticRuleSource=review_required`。
- **表示名は基色で使い分ける** (最終表示は CSV の `PrimaryName` / `Aliases` / `BreedContext` / `RegistryNotes` に従う):
  - 黒系・ブルー系 → **Chinchilla 表記を canonical** とし、Shell 表記を `Aliases` に併記する (例: `Chinchilla Silver` (canonical, Aliases に `Shell Silver`)、`Blue Chinchilla Silver` (Aliases に `Blue Shell Silver`))。
  - 赤系・クリーム系 → **Shell / Shell Cameo 表記を canonical** とする (例: `Shell Cameo`、`Cream Shell Cameo`、`Shell Cream`)。
  - 上記に合わない表記 (例: ブルー系を Shell 表記した `Shell Blue`) は、対応する canonical へ `Status=alias` で寄せる (`Shell Blue` → `blue_chinchilla_silver`)。
- 同一概念のため、片方の表記を入力しても他方の `ColorId` に解決できるよう `Aliases` / `CanonicalColorId` を整える。

### 12.3 Shaded

- **Shaded は Shell/Chinchilla とは tipping 量が異なる別概念**として `canonical` を維持する (Shell/Chinchilla へ寄せない)。
- `PatternState=shaded`。遺伝子座は不確かなため `GeneticRuleSource=review_required` を維持する。

### 12.4 Golden

- **Golden は単なる `non_silver` ではなく、`non_silver` + wideband/tipping 系概念**として扱う。
- `i/i` のみで Golden と確定しない。`Wb/-` または wideband/tipping 系の補助情報を要するが、**`Wb/-` のみでも自動生成は確定しない**。
- master では `SilverState=non_silver`・`PatternState=shell または shaded` (chinchilla 級は `shell`、それ以外は `shaded`) として保持し、`GeneticRuleSource=review_required` を維持する (マップの `I/I`・`a/a` 誤りに引きずられない)。
- **エンジンの命名**: 親がワイドバンドで子が非オレンジ・アグーチ・`Wb/-` になる場合、その子を `Golden` (非シルバー) として命名する (濃淡は親名から推論)。詳細は [`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §6.4。

### 12.5 Smoke

- **Smoke は Shell/Shaded/Chinchilla/Golden(Wb系) とは別系統**。
- `Smoke = solid(a/a) + inhibitor I/-` の概念。master では `AgoutiState=solid`・`SilverState=smoke` に固定し、Wb 系とは分離する。
- 遺伝条件: `Smoke = a/a + I/-`、`Tortie Smoke = a/a + I/- + O/o`、`Blue Cream Smoke = a/a + I/- + O/o + d/d`。White ありは `S/-` を付与する。

### 12.6 Smoke × Tortie / Calico の確定

- **`Smoke` 単独**は基色を持たないカテゴリ名のため `Status=excluded` (`DisplayAllowed=false`/`InputAllowed=false`/`CanonicalColorId` 空)。具体色柄ではないため通常計算・入力候補から除外する。
- **トーティ系 smoke** (S/s, -White) は正規表示へ alias 解決する:
  - `Smoke Tortoiseshell` → `tortie_smoke` (Tortie Smoke)
  - `Calico Smoke` / `Smoke Calico` → `tortie_smoke_white` (Tortie Smoke-White。Calico = Tortie + White)
  - `Smoke Dilute Calico` → `blue_cream_smoke_white` (Blue Cream Smoke-White。Dilute Calico = Blue Cream + White)
- **希釈トーティ smoke は Cream を正規名にする** (§7 の希釈トーティ Cream 統一に従う)。`Blue Cream Smoke` 系は元データ行 (Code 74 / 53 / 280) を持つため **canonical**、`Blue Tortie Smoke` 系の表記は元データに直接行が無いため alias としても保持しない (入力は `Blue Cream Smoke` を用いる。エンジンは `Blue Tortie Smoke` を出力しない)。
  - `Blue Cream Smoke` = canonical `blue_cream_smoke`、`Blue Cream Smoke-White` = canonical `blue_cream_smoke_white`
- **Van (S/S)** は -White(S/s) と遺伝的に別概念なので **-White へは寄せない** (§12.7)。同一 Van 概念へまとめる:
  - `Tortie Smoke-White Van` → canonical `tortie_smoke_white_van`、`Smoke Calico Van` → alias → `tortie_smoke_white_van`
  - `Blue Cream Smoke-White Van` = canonical `blue_cream_smoke_white_van` (元データ Code 280)
- 元データ由来の canonical: `tortie_smoke` / `tortie_smoke_white` / `tortie_smoke_white_van` (黒系トーティ smoke)、`blue_cream_smoke` / `blue_cream_smoke_white` / `blue_cream_smoke_white_van` (希釈トーティ smoke = Cream)。旧版では `Blue Tortie Smoke` 系を合成 canonical にして Cream を寄せていたが、Cream 正規化に伴い反転した。

### 12.7 Van (S/S) の扱い — 遺伝的同一性 vs 表示正規化

`Van` (S/S = 高白斑ホモ) は `-White` (S/s) と**遺伝的に別概念**である ([`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §2.4)。入力で Van が与えられたら `S/S` を保持して子に Van を出せる必要があるため、master では Van を **collapse しない**。

- Van 行は **独立概念**として保持する: `WhiteState=van`、`InputAllowed=true`、`DisplayAllowed=false`、`CanonicalColorId` は**自身**または**同一 Van 概念** (-White 側 S/s には向けない)。
- 名称違いの同一 Van 概念 (例: `Smoke Calico Van` = `Tortie Smoke-White Van`) は片方を canonical、他方を alias とし、`CanonicalColorId` は Van 概念を指す (遺伝的同一性)。
- **一般表示での Van → -White 正規化は表示名マスタ ([`cat_color_display_alias_map.csv`](./cat_color_display_alias_map.csv)) が担う** (遺伝定義と表示名定義の分離 / データ正本 §1.2)。master の `CanonicalColorId` を表示正規化に流用しない。
- これにより、`CanonicalColorId` は全行で一貫して「**遺伝的・概念的同一性**」を意味する (`alias` = 同じ遺伝概念の別名)。表示の寄せ (Van→-White) はそれとは独立。

### 12.8 C-locus / Wb-locus と normal_mode の関係

計算ロジックの正本は [`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) (§2.4 カテゴリC, §4.4 C Locus, §4.11 Wb Locus)。本節は master の Point/Mink/Sepia/Wb 分類がその方針とどう対応するかを示す。

**C-locus 方針**:

1. フルカラー表現型は `normal_mode` では `C/C` 相当として扱う。
2. `C/cs`・`C/cb` は表現型から判定できないため `normal_mode` では**自動展開しない** (カテゴリC)。
3. Point / Sepia / Mink は、入力色・猫種標準・血統/産子履歴・明示キャリアで確認される場合のみ `explicit_carrier_mode` または猫種制約 (breed constraint) で扱う。
4. 猫種正本 ([`cat_breed_genetic_map.csv`](./cat_breed_genetic_map.csv)) で固定: Siamese / Colorpoint 系 = `cs/cs`、Burmese 系 = `cb/cb`。Tonkinese は猫種内に Point / Mink / Solid(Sepia) class が併存するため、breed 全体では `cb/cs` 固定にしない。`cb/cs` は Tonkinese の Mink class/profile 指定時のみ扱う。
5. Ragdoll / Birman 等のポイント前提猫種は `cs/cs` 固定 (候補含む)。
6. 不可逆: `cs/cs × cs/cs` から `C/-` フルカラーは出ない (§4.4)。

**master での対応**: Point/Mink/Sepia 概念は `InputAllowed=true` (入力・猫種・明示キャリアで使用可) かつ `DisplayAllowed=false` (breed_unselected の `normal_mode` 一般結果には出さない)。Mink = `breed_specific(Tonkinese)`、Tonkinese Solid class = `breed_specific(Tonkinese)` かつ C座位上は `cb/cb`、Burmese Sepia = `breed_specific(Burmese)`、その他 Point は `general` または猫種別 class として扱う。これらが実際に出るかはエンジンの計算モード/猫種制約に従い、master は名前の可否のみ定義する。

**Wb-locus 方針**: Wb 系 (Shell / Chinchilla / Shaded / Golden) は `normal_mode` で **Wb キャリアを自動展開しない** (非ワイドバンド親から wide な子を生成しない。不可逆ルール: `wb/wb × wb/wb` から tipping 系は出ない / [`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §4.11)。ただし**親がワイドバンドで子が実際に `Wb/-` になる場合は、その子を命名する** (未分類にしない / 命名規則は 01 §6.4)。master では canonical または alias として保持し、`InputAllowed=true`、`GeneticRuleSource=review_required` を維持する (§12.2〜12.4)。

---

## 13. 用語定義 (Any 禁止語の置換)

機械可読な正本では曖昧語 `Any` を**仕様値・CSV値・モード名として使用しない**。意味別に以下を使う。

| 語 | 意味 |
|---|---|
| `breed_unselected` | 猫種が選ばれていない (入力状態) |
| `no_breed_filter` | 猫種制約を適用しない (フィルタ挙動) |
| `normal_mode` | 通常計算モード |
| `explicit_carrier_mode` | 明示キャリア計算モード |
| `general` | 表示文脈が一般用途 (`BreedContext=general`) |
| `unrestricted` | 性別制限なし (`SexRestriction=unrestricted`) |

> `breed_unselected` と `no_breed_filter` はいずれも「未明示キャリアを全て通常結果に混ぜる」という意味ではない。未明示キャリア由来の色は通常結果 (確定色) に混ぜず、推定色 `conditional_color_groups` として「もし出たら」提示する ([`01_シミュレーター正本_V9.md`](./01_シミュレーター正本_V9.md) §2.3 / §8.3)。
