# cat_color_master.csv レビューレポート

> 自動生成: `scripts/build_cat_color_master.py`。人間レビュー用。数値・一覧はビルド時点のもの。

## 0. 設計確定事項

- **別名は独立行**で保持する (ユーザー確定)。各 alias は固有 `ColorId` + `Status=alias` を持ち、`Notes` に `resolves_to=<canonical_color_id>` を記録する。
- 1 行 = 1 色柄概念。`ColorId` は一意。`SourceCodes` / `SourceNames` に元データの全コード・全名を保持し、元データ名を失わない。
- `Any` は仕様値・モード名として使用しない (`breed_unselected` / `no_breed_filter` / `normal_mode` / `general` / `unrestricted` 等)。

## 1. 件数サマリー

- 元データ件数 (色柄データUTF8Ver.csv, 名前あり): **407**
- 現行正本件数 (cat_color_genetic_map.csv): **330**
- 生成した色柄概念 (ColorId) 件数: **383**

| Status | 件数 |
|---|---|
| canonical | 266 |
| alias | 25 |
| breed_specific | 84 |
| excluded | 2 |
| review | 6 |
| **合計** | **383** |

- `GeneticRuleSource=review_required` (遺伝子ルール要確認): **171** 件
- 正規化 (略称・タイポ展開) を適用した概念: **86** 件

### 1.1 CanonicalColorId と元データカバレッジ

- alias 解決件数 (`Status=alias` かつ `CanonicalColorId` あり): **25 / 25**
- alias 解決先が存在しない行数 (`CanonicalColorId` が空 or 実在しない): **0**
- 元データ 407 件のカバレッジ (SourceCode が master のいずれかの行に保持): **407 / 407** (100%)

**CanonicalColorId を追加した理由**: alias の解決先をこれまで `Notes` の `resolves_to=` という人間用メモに持たせていたが、機械可読な唯一正本としては危険 (パース依存・欠落検出不能)。`Notes` は人間用メモへ戻し、alias 解決に必要な情報は専用カラム `CanonicalColorId` に分離した。機械処理は必ず `CanonicalColorId` を参照する。`canonical` は自分自身、`alias` は解決先 canonical、`breed_specific` は原則自分自身、`review`/`excluded` は確定不能なら空欄 (理由は `Notes`)。

## 2. 差分: 元データ ↔ 現行正本

### 2.1 元データにあるが現行マップに無い Code (77)

313:Smoke Dilute Calico, 314:Red Point Bi-Color, 315:Cream Point Bi-Color, 316:Silver Classic Tobie, 317:Silver Mackerel Tobie, 318:Brown Mackerel Tobie, 319:Blue Tortie Point Mitted, 320:Lilac Point Mitted, 321:Blue Tortie Point Bi-Color, 322:Blue Silver Mc Tabby-White, 323:Red Point Mitted, 324:Smoke, 325:Ebony Silver, 326:Shaded Chocolate, 327:Chocolate Tortie, 328:Lilac Tortie, 329:Cream Cameo Tabby, 330:Cream Cameo Mc Tabby, 331:Cream Cameo Tabby-White, 332:Cream Cameo Mc Tabby-W, 333:Blue Silver Tabby-W Van, 334:Chocolate Lynx Point-White, 335:Cream Cameo, 336:Seal Tortie Point Bi-Color, 337:Seal Tortie Point Mitted, 338:Browm Classic Torbie-White, 339:Platinum Mink(Lilac Mink), 340:Blue Silver Classic Tabby, 341:Cream Shell Cameo, 342:Flame Lynx Point, 343:Shell Cream, 344:Shaded Cream, 345:Tortie Point Mitted, 346:Seal Tortie Point, 347:Blue Cream Point Bi-Color, 348:Sable Ticked Tabby, 349:Chocolate Cream P Bi-Color, 350:Shell Blue(Blue Chinchilla), 351:Seal Point (A.O.C), 391:Red Lynx Point-White, 392:Chocolate Silver Spotted Tabby, 393:Ebony Silver Ticked T, 394:Shaded Tortie-White, 395:Black Brown Spotted Tabby, 396:Ebony Silver Mc Tabby, 397:Red Silver(Cameo)Tabby-W, 398:Chocolate Tabby, 399:Blue Silver Spotted Tabby, 400:Cinnamon-White, 401:Blue Ticked Tabby-White, 402:Chestnut Tortie, 403:Flame Point Mitted, 404:Chestnut Tortie-White, 405:Chestnut Tortie Point-W, 406:Choco Silver Tortie Lynx Point, 407:Brown Sp Tabby (Rosettes), 408:Choco Tortie Lynx Point Mitted, 409:Shell Cameo-White, 410:Ebony Smoke, 411:Ebony Tabby, 412:Ebony Mackerel Tabby, 413:Red Point-White, 414:Chinchilla Silver-White, 415:Chinchilla Golden-White, 416:Red Ticked Tabby, 417:Cream Ticked Tabby, 418:Chocolate Lynx Point (AOC), 419:Chocolate Pt Tabby-White, 420:Cream Silver Tabby-White, 421:Smoke Calico Van, 422:Cameo Spotted Tabby, 423:Blue Silver Pt Sp Tabby, 424:Ebony Silver Spotted Tabby, 425:Silver Marbled Tabby, 426:Blue Silver Sp Tabby-W, 427:Cream Point-White, 428:Lilac-White

### 2.2 現行マップにあるが元データに無い Code (0)

(なし)

### 2.3 Code 一致だが名前不一致 (1)

| Code | 元データ名 | マップ名 |
|---|---|---|
| 312 | Calico Smoke | Calico |

### 2.4 マップのみに存在する色柄 (0)

(なし)

## 3. 同一概念として統合した別名 (alias)

| PrimaryName | CanonicalColorId | RegistryNotes |
|---|---|---|
| Blue Cream | `blue_tortie` | 同一概念: Blue Cream → Blue Tortie (blue_tortie) |
| Blue Cream Point | `blue_tortie_point` | 同一概念: Blue Cream Point → Blue Tortie Point (blue_tortie_point) |
| Blue Cream-White | `dilute_calico` | 同一概念: Blue Cream-White → Dilute Calico (dilute_calico) |
| Blue Gray | `blue` | 同一概念: Blue Gray → Blue (blue) |
| Blue Tortie-White | `dilute_calico` | 同一概念: Blue Tortie-White → Dilute Calico (dilute_calico) |
| Bronze | `brown_tabby` | 同一概念: Bronze → Brown Tabby (brown_tabby) |
| Brown Classic Torbie | `brown_patched_tabby` | TICA: Torbie = Patched Tabby (Brown Patched Tabby) |
| Brown Classic Torbie-White | `brown_patched_tabby_white` | TICA: Torbie = Patched Tabby (Brown Patched Tabby-White) |
| Brown Mackerel Torbie | `brown_patched_tabby` | TICA: Torbie = Patched Tabby (Brown Patched Tabby) |
| Brown Mackerel Torbie-White | `brown_patched_tabby_white` | TICA: Torbie = Patched Tabby (Brown Patched Tabby-White) |
| Chestnut | `chocolate` | 同一概念: Chestnut → Chocolate (chocolate) |
| Chestnut Tortie | `chocolate_tortie` | 同一概念: Chestnut Tortie → Chocolate Tortie (chocolate_tortie) |
| Ebony | `black` | 同一概念: Ebony → Black (black) |
| Lavender | `lilac` | 同一概念: Lavender → Lilac (lilac) |
| Lilac Cream | `lilac_tortie` | 同一概念: Lilac Cream → Lilac Tortie (lilac_tortie) |
| Mike Tri Color | `calico` | 同一概念: Mike Tri Color → Calico (calico) |
| Peke-Face Red | `red` | Peke-Face は形態/タイプ由来語: Peke-Face Red → Red (red) |
| Peke-Face Red Mackerel Tabby | `red_mackerel_tabby` | Peke-Face は形態/タイプ由来語: Peke-Face Red Mackerel Tabby → Red Mackerel Tabby (red_mackerel_tabby) |
| Peke-Face Red Mackerel Tabby-White | `red_mackerel_tabby_white` | Peke-Face は形態/タイプ由来語: Peke-Face Red Mackerel Tabby-White → Red Mackerel Tabby-White (red_mackerel_tabby_white) |
| Peke-Face Red Tabby | `red_tabby` | Peke-Face は形態/タイプ由来語: Peke-Face Red Tabby → Red Tabby (red_tabby) |
| Peke-Face Red Tabby-White | `red_tabby_white` | Peke-Face は形態/タイプ由来語: Peke-Face Red Tabby-White → Red Tabby-White (red_tabby_white) |
| Shell Blue | `blue_chinchilla_silver` | 団体/補足タグ: Blue Chinchilla / 同一概念: Shell Blue → Blue Chinchilla Silver (blue_chinchilla_silver) |
| Silver Classic Torbie | `silver_patched_tabby` | TICA: Torbie = Patched Tabby (Silver Patched Tabby) |
| Silver Mackerel Torbie | `silver_patched_tabby` | TICA: Torbie = Patched Tabby (Silver Patched Tabby) |
| Tortoiseshell-White | `calico` | 同一概念: Tortoiseshell-White → Calico (calico) |

## 4. 猫種固有呼称として分離 (breed_specific)

- **Abyssinian** (3): Ruddy, Sorrel, Sorrel Spotted Tabby
- **Bengal** (7): Black Silver Marbled Tabby, Blue Marble, Brown Marbled Tabby, Leopard, Silver Marbled Tabby, Snow, Snow Spotted Tabby
- **Burmese** (9): Champagne, Champagne Point, Champagne Solid, Platinum, Platinum Point, Platinum Solid, Sable, Sable Ticked Tabby, Sepia Agouti
- **Oriental** (19): Chestnut Patched Tabby, Chestnut Silver Tabby, Chestnut Tabby, Chestnut Tortie Point-White, Chestnut Tortie-White, Ebony Mackerel Tabby, Ebony Patched Tabby, Ebony Silver, Ebony Silver Mackerel Tabby, Ebony Silver Spotted Tabby, Ebony Silver Tabby-White, Ebony Silver Ticked T, Ebony Silver Ticked Tabby-White, Ebony Smoke, Ebony Tabby, Ebony-White, Lavender Patched Tabby, Lavender Spotted Tabby, Lavender Tabby
- **Ragdoll** (38): Blue Cream Point Bi-Color, Blue Cream Point Mitted, Blue Lynx Point Bi-Color, Blue Lynx Point Mitted, Blue Lynx Point Van Bi-Color, Blue Point Bi-Color, Blue Point Mitted, Blue Tortie Point Bi-Color, Blue Tortie Point Mitted, Chocolate Cream P Bi-Color, Chocolate Lynx Point Bi-Color, Chocolate Point Bi-Color, Chocolate Point Mitted, Chocolate Tortie Lynx Point Mitted, Chocolate Tortie Point Bi-Color, Chocolate Tortie Point Mitted, Cream Lynx Point Bi-Color, Cream Point Bi-Color, Cream Point Mitted, Flame Point Bi-Color, Flame Point Mitted, Lilac Point Bi-Color, Lilac Point Mitted, Lilac Tortie Lynx Point Mitted, Lilac Tortie Point Mitted, Red Point Bi-Color, Red Point Mitted, Seal Bi-Color, Seal Lynx Point Bi-Color, Seal Lynx Point Van Bi-Color, Seal Point Bi-Color, Seal Point Mitted, Seal Tortie Lynx Point Bi-Color, Seal Tortie Lynx Point Mitted, Seal Tortie Point Bi-Color, Seal Tortie Point Mitted, Tortie Point Bi-Color, Tortie Point Mitted
- **Tonkinese** (8): Blue Mink, Champagne Mink, Natural Mink, Natural Point, Natural Solid, Platinum Mink, Seal Mink, Seal Mink Spotted Tabby

## 5. タイポ・略称として正規化した色柄

| PrimaryName | SourceNames | 正規化内容 |
|---|---|---|
| Blue Mackerel Tabby-White | Blue Mc Tabby-White | Mc→Mackerel |
| Blue Patched Mackerel Tabby | Blue Patched Mc Tabby | Mc→Mackerel |
| Blue Patched Mackerel Tabby-White | Blue Pt Mc Tabby-White | Mc→Mackerel, Pt→Patched (Point ではない) |
| Blue Patched Spotted Tabby | Blue Pt Sp Tabby | Pt→Patched (Point ではない), Sp→Spotted |
| Blue Patched Spotted Tabby-White | Blue Pt Sp Tabby-White | Pt→Patched (Point ではない), Sp→Spotted |
| Blue Patched Tabby-White | Blue Pt Tabby-White | Pt→Patched (Point ではない) |
| Blue Spotted Tabby-White | Blue Sp Tabby-White | Sp→Spotted |
| Blue Ticked Tabby-White | Blue Tc Tabby-White, Blue Ticked Tabby-White | Tc→Ticked |
| Brown Mackerel Tabby-White | Brown Mc Tabby-White | Mc→Mackerel |
| Brown Patched Mackerel Tabby | Brown Patched Mc Tabby | Mc→Mackerel |
| Brown Patched Mackerel Tabby-White | Brown Pt Mc Tabby-White | Mc→Mackerel, Pt→Patched (Point ではない) |
| Brown Patched Spotted Tabby | Brown Pt Sp Tabby, Brown Patched Sp Tabby | Pt→Patched (Point ではない), Sp→Spotted |
| Brown Patched Spotted Tabby-White | Brown Pt Sp Tabby-White | Pt→Patched (Point ではない), Sp→Spotted |
| Brown Patched Tabby-White | Brown Pt Tabby-White | Pt→Patched (Point ではない) |
| Brown Patched Ticked Tabby | Brown Pt Ticked Tabby | Pt→Patched (Point ではない) |
| Brown Patched Ticked Tabby-White | Brown Pt Ticked Tabby-W | Pt→Patched (Point ではない), Tabby-W→Tabby-White |
| Brown Spotted Tabby | Brown Spotted Tabby, Brown Sp Tabby (Rosettes) | Sp→Spotted |
| Brown Spotted Tabby-White | Brown Sp Tabby-White | Sp→Spotted |
| Brown Ticked Patched Tabby | Brown Ticked Pt Tabby | Pt→Patched (Point ではない) |
| Brown Ticked Tabby-White | Brown Tc Tabby-White, Brown Ticked Tabby-White | Tc→Ticked |
| Chocolate Patched Tabby-White | Chocolate Pt Tabby-White | Pt→Patched (Point ではない) |
| Cream Mackerel Tabby-White | Cream Mc Tabby-White | Mc→Mackerel |
| Cream Spotted Tabby-White | Cream Sp Tabby-White | Sp→Spotted |
| Golden Mackerel Tabby | Golden Mc Tabby | Mc→Mackerel |
| Red Mackerel Tabby-White | Red Mc Tabby-White | Mc→Mackerel |
| Red Spotted Tabby-White | Red Sp Tabby-White | Sp→Spotted |
| Blue Silver Mackerel Tabby | Blue Silver Mc Tabby | Mc→Mackerel |
| Blue Silver Mackerel Tabby-White | Blue Silver Mc Tabby-White | Mc→Mackerel |
| Blue Silver Patched Mackerel Tabby | Blue Silver Pt Mc Tabby | Mc→Mackerel, Pt→Patched (Point ではない) |
| Blue Silver Patched Mackerel Tabby-White | Blue Silver Pt Mc Tabby-W | Mc→Mackerel, Pt→Patched (Point ではない), Tabby-W→Tabby-White |
| Blue Silver Patched Spotted Tabby | Blue Silver Pt Sp Tabby | Pt→Patched (Point ではない), Sp→Spotted |
| Blue Silver Patched Tabby-White | Blue Silver Pt Tabby-White | Pt→Patched (Point ではない) |
| Blue Silver Spotted Tabby-White | Blue Silver Sp Tabby-W | Sp→Spotted, Tabby-W→Tabby-White |
| Cameo Mackerel Tabby-White | Cameo Mc Tabby-White | Mc→Mackerel |
| Cream Cameo Mackerel Tabby | Cream Cameo Mc Tabby | Mc→Mackerel |
| Cream Cameo Mackerel Tabby-White | Cream Cameo Mc Tabby-W | Mc→Mackerel, Tabby-W→Tabby-White |
| Red Silver Tabby-White | Red Silver(Cameo)Tabby-W | Tabby-W→Tabby-White |
| Silver Mackerel Tabby-White | Silver Mc Tabby-White | Mc→Mackerel |
| Silver Patched Mackerel Tabby | Silver Patched Mc Tabby | Mc→Mackerel |
| Silver Patched Mackerel Tabby-White | Silver Pt Mc Tabby-White | Mc→Mackerel, Pt→Patched (Point ではない) |
| Silver Patched Spotted Tabby | Silver Pt Sp Tabby | Pt→Patched (Point ではない), Sp→Spotted |
| Silver Patched Spotted Tabby-White | Silver Pt Sp Tabby-White | Pt→Patched (Point ではない), Sp→Spotted |
| Silver Patched Tabby-White | Silver Pt Tabby-White | Pt→Patched (Point ではない) |
| Silver Patched Ticked Tabby | Silver Pt Ticked Tabby, Silver Patched Ticked Tabby | Pt→Patched (Point ではない) |
| Silver Patched Ticked Tabby-White | Silver Pt Tc Tabby-White | Pt→Patched (Point ではない), Tc→Ticked |
| Silver Spotted Tabby-White | Silver Sp Tabby-White | Sp→Spotted |
| Silver Ticked Tabby-White | Silver Tc Tabby-White, Silver Ticked Tabby-White | Tc→Ticked |
| Chocolate Cream Lynx Point-White | Choco Cream Lynx Point-W | -W→-White, Choco→Chocolate |
| Chocolate Cream Point | Choco Cream Point | Choco→Chocolate |
| Chocolate Silver Lynx Point-White | Choco Silver Lynx Point-W | -W→-White, Choco→Chocolate |
| Chocolate Silver Tortie Lynx Point | Choco Silver Tortie Lynx Point | Choco→Chocolate |
| Chocolate Tortie Lynx Point | Choco Tortie Lynx Point, Chocolate Tortie Lynx Point | Choco→Chocolate |
| Chocolate Tortie Lynx Point-White | Choco Tortie Lynx Point-W, Chocolate Tortie Lynx Point-White | -W→-White, Choco→Chocolate |
| Chocolate Tortie Point | Choco Tortie Point | Choco→Chocolate |
| Seal Tortie Lynx Point-White | Seal Tortie Lynx Point-W, Seal Tortie Lynx Point-White | -W→-White |
| Blue Mackerel Tabby-White Van | Blue Mc Tabby-White Van | Mc→Mackerel |
| Blue Patched Mackerel Tabby-White Van | Blue Pt Mc Tabby-W Van | -W Van→-White Van, Mc→Mackerel, Pt→Patched (Point ではない) |
| Blue Patched Tabby-White Van | Blue Pt Tabby-White Van | Pt→Patched (Point ではない) |
| Blue Silver Patched T-White Van | Blue Silver Pt T-W Van | -W Van→-White Van, Pt→Patched (Point ではない) |
| Blue Silver Patched Tabby-White Van | Blue Silver Pt Tabby-White Van | Pt→Patched (Point ではない) |
| Blue Silver Tabby-White Van | Blue Silver Tabby-W Van | -W Van→-White Van |
| Brown Mackerel Tabby-White Van | Brown Mc Tabby-White Van | Mc→Mackerel |
| Brown Patched Mackerel Tabby-White Van | Brown Pt Mc Tabby-W Van | -W Van→-White Van, Mc→Mackerel, Pt→Patched (Point ではない) |
| Brown Patched Tabby-White Van | Brown Pt Tabby-White Van | Pt→Patched (Point ではない) |
| Cameo Mackerel Tabby-White Van | Cameo Mc Tabby-White Van | Mc→Mackerel |
| Cream Mackerel Tabby-White Van | Cream Mc Tabby-White Van | Mc→Mackerel |
| Red Mackerel Tabby-White Van | Red Mc Tabby-White Van | Mc→Mackerel |
| Silver Mackerel Tabby-White Van | Silver Mc Tabby-W Van | -W Van→-White Van, Mc→Mackerel |
| Silver Patched Mackerel Tabby-White Van | Silver Pt Mc Tabby-W Van | -W Van→-White Van, Mc→Mackerel, Pt→Patched (Point ではない) |
| Silver Patched Tabby-White Van | Silver Pt Tabby-W Van | -W Van→-White Van, Pt→Patched (Point ではない) |
| Blue Lynx Point Van Bi-Color | Blue Lynx Point Van Bi-C | Bi-C→Bi-Color |
| Chestnut Tortie Point-White | Chestnut Tortie Point-W | -W→-White |
| Chocolate Tortie Lynx Point Mitted | Choco Tortie Lynx Point Mitted | Choco→Chocolate |
| Chocolate Tortie Point Mitted | Choco Tortie Point Mitted | Choco→Chocolate |
| Ebony Silver Mackerel Tabby | Ebony Silver Mc Tabby | Mc→Mackerel |
| Ebony Silver Ticked Tabby-White | Ebony Silver Ticked T-W | T-W→Tabby-White |
| Seal Lynx Point Van Bi-Color | Seal Lynx Point Van Bi-C | Bi-C→Bi-Color |
| Brown Classic Torbie | Brown Classic Tobie | Tobie→Torbie |
| Brown Classic Torbie-White | Browm Classic Torbie-White | Browm→Brown |
| Brown Mackerel Torbie | Brown Mackerel Tobie | Tobie→Torbie |
| Brown Mackerel Torbie-White | Brown Mc Tobie-White | Mc→Mackerel, Tobie→Torbie |
| Peke-Face Red Mackerel Tabby | Peke-Face Red Mc Tabby | Mc→Mackerel |
| Peke-Face Red Mackerel Tabby-White | P-F Red Mc Tabby-White | Mc→Mackerel, P-F→Peke-Face |
| Peke-Face Red Tabby-White | P-F Red Tabby-White | P-F→Peke-Face |
| Silver Classic Torbie | Silver Classic Tobie | Tobie→Torbie |
| Silver Mackerel Torbie | Silver Mackerel Tobie | Tobie→Torbie |

## 6. review にした色柄

Calico Smoke (`calico_smoke`), Smoke (`smoke`), Smoke Calico (`smoke_calico`), Smoke Calico Van (`smoke_calico_van`), Smoke Dilute Calico (`smoke_dilute_calico`), Smoke Tortoiseshell (`smoke_tortoiseshell`)

## 7. excluded にした色柄

AOV (`aov`), Any Other Color (`any_other_color`)

## 8. 遺伝子ルールがまだ不確かな項目 (GeneticRuleSource=review_required)

計 171 件。代表: 
Golden Mackerel Tabby, Golden Tabby, Blue Chinchilla Golden, Blue Chinchilla Silver, Blue Shaded, Blue Shaded Golden, Blue Shaded Silver, Chinchilla Golden, Chinchilla Golden-White, Chinchilla Silver, Chinchilla Silver-White, Cream Shell Cameo, Shaded Cameo, Shaded Cameo-White, Shaded Chocolate, Shaded Cream, Shaded Golden, Shaded Golden-White, Shaded Silver, Shaded Silver-White, Shaded Tortie, Shaded Tortie-White, Shell Cameo, Shell Cameo-White, Shell Cream, Shell Tortoiseshell, Shell Tortoiseshell-White, Blue Cream Lynx Point, Blue Cream Lynx Point-White, Blue Cream Point-White, Blue Lynx Point, Blue Lynx Point-White, Blue Point, Blue Point-White, Blue Tortie Point, Brown Lynx Point, Chocolate Cream Lynx Point-White, Chocolate Cream Point, Chocolate Lynx Point, Chocolate Lynx Point-White, Chocolate Point, Chocolate Point-White, Chocolate Silver Lynx Point-White, Chocolate Silver Tortie Lynx Point, Chocolate Tortie Lynx Point, Chocolate Tortie Lynx Point-White, Chocolate Tortie Point, Cream Lynx Point, Cream Point, Cream Point-White, Flame Lynx Point, Flame Point, Flame Point-White, Lilac Cream Lynx Point, Lilac Cream Point, Lilac Cream Point-White, Lilac Lynx Point, Lilac Point, Lilac Point-White, Red Lynx Point ...

## 9. 判断の根拠と不確かな点

- **Pt の扱い**: 元データの `Pt` は全て Tabby 文脈であり `Patched` と解釈した (例: `Blue Pt Tabby-White` → `Blue Patched Tabby-White`)。`Point` は `Point` と明示された名のみ Point 系とした。各行 `Notes` に正規化内容を残している。
- **CFA/TICA 差**: `Blue Cream`=`Blue Tortie`, `Lilac Cream`=`Lilac Tortie`, `Tortoiseshell-White`/`Mike Tri Color`=`Calico`, `Blue Tortie-White`/`Blue Cream-White`=`Dilute Calico`, `Torbie`=`Patched Tabby` を同一概念の alias として統合した。
- **猫種固有呼称**: Ruddy/Sorrel(Aby), Sable/Champagne/Platinum/Sepia(Burmese), 各種 Mink(Tonkinese), Ebony/Chestnut/Lavender(Oriental), Leopard/Snow/Marble(Bengal), Mitted/Bi-Color(Ragdoll) を breed_specific とし `DisplayAllowed=false`。
- **白斑**: `Van`(S/S) は一般表示で `-White` に正規化する方針のため `DisplayAllowed=false`。`Mitted`/`Bi-Color` も同様に一般非表示。
- **遺伝子座**: マップに同一 Code・同一名で存在する座のみ `current_map` として取り込み、それ以外は名前から `inferred`。Point/Mink/Sepia/Shaded/WideBand 系と alias/breed_specific は `review_required`。
- **既知のマップ不整合 (要確認)**: `Blue Cream`(code31) はマップ上 `O/O` (ホモ接合オレンジ) だがトーティは `O/o` のはず。master では `OrangeState=tortie` に補正した。エンジン側 CSV は本タスクでは変更していない。
- **未確定で review に残したもの**: 単独 `Smoke`、`Calico Smoke`/`Smoke Calico`/`Smoke Dilute Calico` 等のスモーク×トーティ/キャリコ、`Shell Cream`/`Shell Blue`/`Cream Shell Cameo` 等の基色不明な Shell 系。

### 9.1 追加レビュー判断 (2026-06-24 反映)

1. **Peke-Face / P-F**: 形態・タイプ由来語で色柄概念ではない。canonical にせず、`Peke-Face` を除去した汎用カラーへ alias 解決 (例: `Peke-Face Red`→`red`, `Peke-Face Red Tabby`→`red_tabby`)。`DisplayAllowed=false`、旧データ互換のため `InputAllowed=true`。
2. **Chinchilla / Shell**: 計算上は**同一の shell tipping 概念**(別々の遺伝子計算概念にしない)。表示名のみ基色で使い分ける — 黒系/ブルー系は **Chinchilla 表記を canonical** (Shell 表記を Aliases に併記)、赤系/クリーム系は **Shell / Shell Cameo を canonical**。`PatternState=shell`、`GeneticRuleSource=review_required`。ブルー系の `Shell Blue` は `Blue Chinchilla Silver` へ alias。最終表示は PrimaryName/Aliases/BreedContext/RegistryNotes に従う。
3. **Shaded**: Shell/Chinchilla とは tipping 量が異なる別概念として canonical 維持。`PatternState=shaded`、`GeneticRuleSource=review_required` を維持 (`Shaded Chocolate`/`Shaded Tortie` 等も review から canonical へ移動)。
4. **Golden**: 単なる non_silver ではなく non_silver + wideband/tipping 系概念。`i/i` のみ・`Wb/-` のみでは確定しない。`SilverState=non_silver`・`PatternState=shell または shaded` に保持し `GeneticRuleSource=review_required` を維持。
5. **Smoke**: Shell/Shaded/Chinchilla/Golden(Wb系) とは別系統。`solid(a/a) + inhibitor I/-` の概念として `AgoutiState=solid`・`SilverState=smoke` に固定し、Wb/tipping 系と分離。

## 10. 今後人間がレビューすべきポイント

1. `review` 行を canonical / alias / breed_specific のいずれへ確定するか。
2. `review_required` の遺伝子座 (特に Wb 系 Shaded/Chinchilla/Golden、Point/Mink/Sepia の C 系)。
3. alias の `CanonicalColorId` 解決先が妥当か (特に Torbie→Patched Tabby のパターン語処理)。
4. breed_specific の BreedContext 割り当て (Oriental/Burmese/Tonkinese の境界)。
5. `Tortoiseshell-White` を `Calico` へ寄せた判断 (CFA は白量で区別する場合あり)。
