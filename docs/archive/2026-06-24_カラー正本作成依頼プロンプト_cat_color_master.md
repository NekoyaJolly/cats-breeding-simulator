# カラー正本作成依頼プロンプト：猫色柄マスター唯一正本 `cat_color_master.csv` 作成タスク

## 作業目的

猫の遺伝学シミュレーターで使用する、色柄マスターの唯一正本を作成してください。

現在、元データと現在の遺伝子座付きカラー正本に差分があり、さらにCFA/TICA/日本団体の呼称、猫種固有呼称、略称、タイポ、同一概念の別名が混ざっています。

このまま計算エンジンに使うと、以下のような事故が起きます。

* 同じ色柄概念が別カラーとして扱われる
* CFA名とTICA名が別物として計算される
* 猫種固有呼称が一般結果に出る
* `Pt` が `Point` と `Patched` で誤解釈される
* `Blue Cream` / `Blue Tortie` / `Dilute Tortoiseshell` のような同一概念が分裂する
* `Calico` / `Tortie-White` / `Tortie and White` が団体差のまま衝突する
* `Ebony`, `Sable`, `Champagne`, `Platinum`, `Lavender`, `Ruddy` などが猫種文脈なしに通常結果へ出る

このタスクでは、単なる名前一覧ではなく、機械可読で実務上使える色柄概念マスターを作成してください。

---

## 作業ディレクトリ

以下のリポジトリで作業してください。

```bash
cd "C:/Users/Nekoya2/appprojects/cats-breeding-simulator"
```

---

## 入力ファイル

以下の2つを必ず比較してください。

```text
docs/architecture/色柄データUTF8Ver.csv
docs/architecture/cat_color_genetic_map.csv
```

もし現在のファイル名が異なる場合は、リポジトリ内を検索して該当ファイルを見つけてください。

---

## 用語ルール：曖昧語の使用禁止

このタスクでは、仕様文書・CSV・レビュー資料内で `Any` という語を原則使用しないでください。

この語は以下の意味が混同されやすいため、機械可読な正本では禁止します。

* 猫種が未選択である
* 猫種制約を適用しない
* すべてのキャリアを探索する
* 性別制限がない
* 表示文脈が一般用途である

それぞれ以下の語に置き換えてください。

| 意味          | 使用する語                      |
| ----------- | -------------------------- |
| 猫種が未選択      | `breed_unselected`         |
| 猫種制約を適用しない  | `no_breed_filter`          |
| 通常計算モード     | `normal_mode`              |
| 明示キャリア計算モード | `explicit_carrier_mode`    |
| 全キャリア探索モード  | `carrier_exploration_mode` |
| 表示文脈が一般用途   | `general`                  |
| 性別制限なし      | `unrestricted`             |

重要：

`breed_unselected` は「猫種が選ばれていない」という意味です。
`no_breed_filter` は「猫種制約を適用しない」という意味です。
どちらも「未明示キャリアをすべて通常結果に混ぜる」という意味ではありません。

未明示キャリアを総当たりする処理は、必ず `carrier_exploration_mode` として通常計算から分離してください。

---

## 重要方針

### 1. 元データを盲信しない

`色柄データUTF8Ver.csv` は現場・既存システム由来の色柄名一覧です。

これは重要な原本ですが、以下を含む可能性があります。

* 略称
* タイポ
* CFA/TICA/日本団体の混在
* 猫種固有呼称
* 古い呼称
* 現在の標準名とは異なる呼称
* 同一概念の別名
* 通常計算結果に出すべきではない表示名

したがって、元データの全行をそのまま canonical として扱わないでください。

### 2. 現在の `cat_color_genetic_map.csv` も盲信しない

現在の `cat_color_genetic_map.csv` は、遺伝子座付きの作業版です。

ただし、元データから抜けている色柄があり、TICA/CFA/猫種固有呼称の整理も不十分です。

したがって、現在の `cat_color_genetic_map.csv` を唯一正本とはみなさず、比較対象・遺伝子ルール案として扱ってください。

### 3. 目的は「全部を残すこと」ではなく「正しく機械可読にすること」

すべての元データ名を通常結果に出す必要はありません。

ただし、元データに存在した名称は、以下のどれかに分類して、失われないようにしてください。

* `canonical`: 通常計算結果として表示してよい正規色柄概念
* `alias`: 入力名・別名として受け付けるが、出力時はcanonicalへ寄せる
* `breed_specific`: 特定猫種や特定団体文脈でのみ表示する呼称
* `excluded`: 元データにはあるが、通常計算にも入力候補にも使わない
* `review`: 自動判断できないため人間レビュー待ち

---

## 最終成果物

以下を作成してください。

### 1. `docs/architecture/cat_color_master.csv`

唯一正本となるCSVです。

1行は「表示名」ではなく、計算上の色柄概念を表します。

必須カラムは以下です。

```csv
ColorId,Status,PrimaryName,Aliases,RegistryNotes,BreedContext,ColorGroup,BaseSeries,OrangeState,Dilution,AgoutiState,SilverState,WhiteState,PointState,PatternState,SexRestriction,DisplayAllowed,InputAllowed,OutputPriority,SourceCodes,SourceNames,GeneticRuleSource,Notes
```

#### カラム定義

| カラム                 | 意味                                                                                                                           |       |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----- |
| `ColorId`           | 機械が使う一意ID。snake_case                                                                                                         |       |
| `Status`            | `canonical` / `alias` / `breed_specific` / `excluded` / `review`                                                             |       |
| `PrimaryName`       | 通常表示名                                                                                                                        |       |
| `Aliases`           | 別名。`                                                                                                                         | ` 区切り |
| `RegistryNotes`     | CFA/TICA/日本団体等の呼称差メモ                                                                                                         |       |
| `BreedContext`      | `general` / `Oriental` / `Burmese` / `Tonkinese` / `Abyssinian` / `Somali` / `Ragdoll` / `Birman` / `Siamese` / `Persian` など |       |
| `ColorGroup`        | `solid` / `tabby` / `patched_tabby` / `tortie` / `calico` / `smoke` / `silver_tabby` / `point` / `mink` / `sepia` など         |       |
| `BaseSeries`        | `black` / `chocolate` / `cinnamon` / `red` / `unknown`                                                                       |       |
| `OrangeState`       | `non_orange` / `orange` / `tortie` / `unknown`                                                                               |       |
| `Dilution`          | `dense` / `dilute` / `unknown`                                                                                               |       |
| `AgoutiState`       | `agouti` / `solid` / `not_applicable` / `unknown`                                                                            |       |
| `SilverState`       | `silver` / `smoke` / `non_silver` / `cameo` / `unknown`                                                                      |       |
| `WhiteState`        | `none` / `white` / `high_white` / `mitted` / `bicolor` / `van` / `unknown`                                                   |       |
| `PointState`        | `full` / `point` / `mink` / `sepia` / `unknown`                                                                              |       |
| `PatternState`      | `none` / `tabby` / `mackerel` / `classic` / `spotted` / `ticked` / `shaded` / `shell` / `unknown`                            |       |
| `SexRestriction`    | `unrestricted` / `female_only` / `male_only`                                                                                 |       |
| `DisplayAllowed`    | `true` / `false`                                                                                                             |       |
| `InputAllowed`      | `true` / `false`                                                                                                             |       |
| `OutputPriority`    | 数値。高いほど優先                                                                                                                    |       |
| `SourceCodes`       | 元データCodeを `                                                                                                                  | ` 区切り |
| `SourceNames`       | 元データ名を `                                                                                                                     | ` 区切り |
| `GeneticRuleSource` | `current_map` / `inferred` / `review_required`                                                                               |       |
| `Notes`             | 人間向けメモ                                                                                                                       |       |

---

### 2. `docs/architecture/cat_color_master_review.md`

人間レビュー用レポートです。

以下を必ず含めてください。

* 元データ件数
* 現行 `cat_color_genetic_map.csv` 件数
* 元データにあるが現行正本にない色柄一覧
* 現行正本にあるが元データにない色柄一覧
* 同一概念として統合した色柄一覧
* CFA/TICA差として扱った色柄一覧
* 猫種固有呼称として分離した色柄一覧
* タイポ・略称として正規化した色柄一覧
* `review` にした色柄一覧
* `excluded` にした色柄一覧
* まだ遺伝子ルールが不確かな項目一覧
* Codexが判断した根拠と、不確かな点

---

### 3. `docs/architecture/cat_color_master_schema.md`

`cat_color_master.csv` の仕様書です。

以下を含めてください。

* このCSVが唯一正本であること
* 1行が「表示名」ではなく「色柄概念」であること
* `Aliases` の使い方
* `Status` の意味
* `BreedContext` の意味
* `DisplayAllowed` / `InputAllowed` の違い
* `ColorId` の命名ルール
* CFA/TICA差の扱い
* 猫種固有呼称の扱い
* 通常計算結果に出してよい色柄と出してはいけない色柄の基準
* `review` の運用方法
* `breed_unselected`, `no_breed_filter`, `normal_mode`, `explicit_carrier_mode`, `carrier_exploration_mode`, `general`, `unrestricted` の用語定義

---

## 呼称差の重要ルール

以下は特に注意してください。

### CFA / TICA / 実務呼称の差

以下は別カラーとして扱わず、原則として同一概念の別名として扱ってください。

| CFA寄り・日本実務寄り         | TICA寄り                                  | 内部概念                        |
| -------------------- | --------------------------------------- | --------------------------- |
| Blue Cream           | Blue Tortie                             | `blue_tortie`               |
| Dilute Tortoiseshell | Blue Tortie                             | `blue_tortie`               |
| Patched Tabby        | Torbie                                  | `patched_tabby` / `torbie`  |
| Blue Patched Tabby   | Blue Torbie                             | `blue_patched_tabby`        |
| Calico               | Tortie-White / Tortie and White         | `calico` / `tortie_white` 系 |
| Dilute Calico        | Blue Tortie-White / Dilute Tortie-White | `dilute_calico` 系           |

ただし、呼称差が本当に同一概念か不確かな場合は、無理に統合せず `review` にしてください。

### Oriental系

以下は猫種文脈に注意してください。

| 呼称       | 一般概念               |
| -------- | ------------------ |
| Ebony    | Black              |
| Chestnut | Chocolate 相当の可能性あり |
| Lavender | Lilac 相当の可能性あり     |

`Ebony` は一般結果では `Black` とし、Oriental文脈では `Ebony` 表示を許可する設計にしてください。

### Burmese / Tonkinese系

以下は一般カラーとして扱わず、猫種文脈付きで扱ってください。

* Sable
* Champagne
* Platinum
* Blue Mink
* Champagne Mink
* Platinum Mink
* Natural Mink
* Sepia系
* Mink系

不確かなものは `review` または `breed_specific` にしてください。

### Abyssinian / Somali系

以下は猫種文脈付きで扱ってください。

* Ruddy
* Usual
* Sorrel
* Fawn
* Blue
* Cinnamon
* Red
* Silver系Abyssinian/Somali呼称

猫種未選択、または `no_breed_filter` の通常計算結果で `Ruddy` や `Sorrel` を出さないでください。

### Lilac / Lavender

`Lilac` と `Lavender` は、多くの文脈で同系統の呼称として扱われますが、猫種・団体によって使い分けがあります。

扱いは以下にしてください。

* 一般正規名は `Lilac`
* `Lavender` は alias
* Oriental等の文脈で必要なら `BreedContext=Oriental` として表示名に使う
* 不確かなものは `review`

### Pt の扱い

`Pt` は非常に危険です。

以下のルールを守ってください。

* `Pt Tabby` は原則 `Patched Tabby` の略として扱う
* `Point` は必ず `Point` と明示されている場合のみPoint系として扱う
* `Pt` を無条件に `Point` に変換しない
* `Blue Pt Tabby-White` は `Blue Patched Tabby-White` として扱う
* ただし不確かなものは `review`

### 略称・タイポ正規化

以下は自動正規化候補です。

| 元       | 正規化                       |
| ------- | ------------------------- |
| `-W`    | `-White`                  |
| `Mc`    | `Mackerel`                |
| `Sp`    | `Spotted`                 |
| `Choco` | `Chocolate`               |
| `Browm` | `Brown`                   |
| `Tobie` | `Torbie`                  |
| `T-W`   | `Tabby-White` または文脈に応じて確認 |

正規化した場合でも、元名は `SourceNames` または `Aliases` に残してください。

---

## 通常結果に出してはいけないもの

猫種未選択 `breed=None`、または仕様上の `breed_unselected` で実行される `normal_mode` の結果では、以下は原則として出してはいけません。

* `breed_specific` の呼称
* `Mitted`
* `Bi-Color`
* `Van`
* `Sable`
* `Champagne`
* `Platinum`
* `Ruddy`
* `Sorrel`
* `Ebony`
* `Lavender`
* `Mink`
* `Sepia`
* `Point`
* Burmese / Tonkinese / Oriental / Abyssinian / Somali 固有名

ただし、猫種指定または表示体系指定がある場合は、aliasとして表示に使ってよいです。

---

## 通常結果に出してよいもの

一般表示として使ってよい標準名は、原則として以下のような汎用カラーです。

* Black
* Blue
* Chocolate
* Lilac
* Cinnamon
* Fawn
* Red
* Cream
* Brown Tabby
* Blue Tabby
* Silver Tabby
* Blue Silver Tabby
* Red Tabby
* Cream Tabby
* Cameo Tabby
* Cream Cameo Tabby
* Tortoiseshell
* Blue Tortie
* Calico
* Dilute Calico
* Brown Patched Tabby
* Blue Patched Tabby
* Silver Patched Tabby
* Blue Silver Patched Tabby
* Smoke系
* Silver系
* `-White` 系

ただし、`A/a` や `C/cs` などが未明示の場合に出してよいかは、エンジン側の計算モードに従います。

このタスクでは、名前の正本化に集中し、計算モードの挙動までは変更しないでください。

---

## 遺伝子座ルールについて

今回のタスクでは、遺伝子座の完全確定は目的ではありません。

ただし、既存 `cat_color_genetic_map.csv` にある遺伝子座情報は参考として `cat_color_master.csv` に取り込んでください。

不確かな場合は、以下を使ってください。

```text
GeneticRuleSource=review_required
```

勝手に確定しないでください。

特に以下はレビュー対象にしてください。

* Burmese / Tonkinese系
* Oriental系
* Abyssinian / Somali系
* Point / Mink / Sepia系
* Mitted / Bi-Color / Van系
* Shell / Shaded / Chinchilla / Wide Band系
* Cameo / Silver / Smoke の境界が曖昧なもの
* `Calico Smoke` のような登録上は存在しても一般計算で扱いづらいもの

---

## 実装方針

必要であれば、Pythonスクリプトを作成して差分・正規化・初期CSV生成を行ってください。

作成する場合は以下に置いてください。

```text
scripts/build_cat_color_master.py
```

ソースコード内コメントは日本語で書いてください。

### 実行場所

```bash
cd "C:/Users/Nekoya2/appprojects/cats-breeding-simulator"
```

### 想定実行コマンド

```bash
PYTHONPATH=. python scripts/build_cat_color_master.py
```

Windows環境で動くようにしてください。
必要に応じてPowerShellでも動くように配慮してください。

---

## 禁止事項

以下は禁止です。

1. 元データを削除すること
2. 元データ名を失うこと
3. `Pt` を無条件に `Point` へ変換すること
4. CFA/TICA差を別カラーとして増殖させること
5. 猫種固有呼称を一般カラーとして `DisplayAllowed=true` にすること
6. 不確かなものを勝手に canonical 確定すること
7. 全ての色柄に無理やり遺伝子座を埋めること
8. `engine.py` やAPIロジックを今回のタスクで変更すること
9. Cloud Run / GitHub Actions / Docker など運用系ファイルを触ること
10. 既存のCSVを上書き破壊すること
11. `Any` を新規の仕様値・CSV値・モード名として使うこと

---

## 作業手順

### Step 1. 入力ファイルの読み込み

* `色柄データUTF8Ver.csv`
* `cat_color_genetic_map.csv`

を読み込む。

文字コードは UTF-8 BOM の可能性を考慮してください。

### Step 2. 差分レポート作成

以下を抽出してください。

* 元データにあるが現行正本にない色柄
* 現行正本にあるが元データにない色柄
* Code一致だが名前が違うもの
* 名前は似ているが表記揺れと思われるもの
* タイポ候補
* 略称候補

### Step 3. 正規化

以下を実施してください。

* 空白の正規化
* `-W` → `-White`
* `Mc` → `Mackerel`
* `Sp` → `Spotted`
* `Choco` → `Chocolate`
* 明確なタイポ修正
* `Pt Tabby` → `Patched Tabby` 候補。ただし要注意としてNotesに記録
* `Point` は `Point` と明示されている場合だけPoint扱い

### Step 4. ColorId割り当て

色柄概念ごとに `ColorId` を作成してください。

命名例：

```text
blue_tortie
blue_tortie_white
blue_patched_tabby
blue_patched_tabby_white
brown_tabby
silver_tabby
cream_cameo_tabby
black_smoke
seal_point
blue_mink
```

別名は同じ `ColorId` に紐づけてください。

### Step 5. Status分類

各概念を以下に分類してください。

* `canonical`
* `alias`
* `breed_specific`
* `excluded`
* `review`

迷ったものは必ず `review` にしてください。
レビュー行は `DisplayAllowed=false`, `InputAllowed=false` を原則としてください。

### Step 6. 出力ファイル作成

以下を生成してください。

```text
docs/architecture/cat_color_master.csv
docs/architecture/cat_color_master_review.md
docs/architecture/cat_color_master_schema.md
```

既存ファイルは上書き前にバックアップするか、新規作成してください。

### Step 7. バリデーション

以下を検証してください。

* `ColorId` が重複していない
* `PrimaryName` が空でない
* `Status` が許可値のみ
* `DisplayAllowed` と `InputAllowed` が true/false のみ
* `SexRestriction` が `unrestricted` / `female_only` / `male_only` のみ
* `ColorId` が snake_case
* `SourceNames` に元データ名が残っている
* `Pt` を含む項目がすべてレビューまたは明確にPatched/Point分類されている
* `breed_specific` なのに `DisplayAllowed=true` になっているものがない、または理由がNotesにある
* `review` がゼロである必要はない。不確かなものは必ずreviewに残す
* CSV値や仕様値として `Any` が残っていない

---

## 期待する最終報告

作業完了後、以下を報告してください。

1. 作成したファイル
2. 元データ件数
3. 現行正本件数
4. 作成した `ColorId` 件数
5. `canonical` 件数
6. `alias` 件数
7. `breed_specific` 件数
8. `excluded` 件数
9. `review` 件数
10. 自動統合した代表例
11. 判断を保留した代表例
12. 危険だった表記例
13. 今後人間がレビューすべきポイント
14. 実行したコマンド
15. 変更したファイル一覧
16. `Any` を置換・排除した箇所

---

## 成功条件

このタスクは、以下を満たしたら成功です。

* 元データと現行正本の差分が可視化されている
* 既存色柄名が失われていない
* 同一概念のCFA/TICA/日本実務呼称がaliasとして統合されている
* 猫種固有呼称が一般カラーとして混ざらない
* `Pt` の扱いが明示されている
* 不確かなものが勝手に確定されず `review` に残っている
* `cat_color_master.csv` を今後の唯一正本として育てられる形になっている
* `engine.py` など計算ロジックは変更していない
* `Any` が新規仕様値として残っていない
* `breed_unselected`, `no_breed_filter`, `normal_mode`, `explicit_carrier_mode`, `carrier_exploration_mode`, `general`, `unrestricted` が意味別に使い分けられている

## 補足

このタスクでは、完璧な最終確定版を一発で作る必要はありません。

重要なのは、今後どこで事故っているか分からなくならないように、色柄名・別名・団体差・猫種固有呼称・遺伝属性を機械可読に整理することです。

不確かなものは無理に決めず、必ず `review` に残してください。
