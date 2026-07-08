# フェーズ指示書 — ライト/ダークテーマ化

位置づけ: **現在進行中のフェーズ指示書** (AGENTS.md §5.0 ローリング運用 / 0〜1件)。フェーズ完了時に本書の要点をサマリーへ反映し、本書は削除する。
起案日: 2026-07-08

---

## 0. ゴール

アプリ全体を **ライト/ダークテーマ対応**にする。結果レポート (ResultView) だけが暖色ダークの「島」になっていた状態を解消し、アプリ全体で一貫したテーマにする。

## 1. 確定した設計判断 (ユーザー承認済み)

| 項目 | 判断 |
|------|------|
| 進め方 | コミットで区切りつつ**全画面を1本のPRで一気に完了** (段階PRにすると完成が遅れ寄り道が増えるため) |
| トグル | **ライト / ダーク / システム の3択**。初期は `prefers-color-scheme` 追従、選択は localStorage 保存 |
| 切替方式 | Tailwind `darkMode: 'class'` (`<html>` の `.dark`)。FOUC回避のインラインスクリプトをペイント前に実行 |
| トークン | `globals.css` にセマンティックな CSS 変数 (RGB三つ組) を定義し、Tailwind color を `rgb(var(--x) / <alpha-value>)` にマップ。全ハードコード色を意味トークンへ移行 |
| 配色 | light=暖色パーチメント / dark=暖色ダーク (レポートのプロトタイプ配色を全体に採用) |

## 2. トークン設計

- 定義: `frontend/app/globals.css` の `:root` (light) と `.dark` (dark)。値は「R G B」チャンネル (`<alpha-value>` 対応のため)。
- 中立: `--bg` `--surface` `--surface-2` `--inset` `--ink` `--ink-soft` `--muted` `--line` `--line-soft`。
- 強調/意味: `--accent` `--accent-ink`(強色上の文字) `--male` `--female` `--confirmed(-bg)` `--conditional(-bg)` `--danger(-bg)`。
- Tailwind: `bg-surface` `text-ink` `border-line` `text-muted` `bg-accent` `text-accent-ink` 等 (`tailwind.config.ts`)。
- レポート互換: 既存 `ResultView` のインライン `var(--r-*)` は globals.css で上記トークンのエイリアス (`--r-surface: rgb(var(--surface))` 等) として供給し、テーマ連動させる。

## 3. 実装 (チケット=コミット)

1. **基盤**: `globals.css` トークン層 / `tailwind.config.ts` (darkMode+色) / `lib/theme.ts` (選択解決・適用・FOUC script) / `ThemeToggle` / layout に script+body トークン化 / ResultView の `--r-*` をトークン化。
2. **全画面スイープ**: 18ファイル約250箇所のハードコード色 (slate/white/sky/pink/amber/red/emerald/rose/blue 等) を意味トークンへ一掃。主要CTA=accent、モーダル暗幕=固定スクリム、色付きボタン文字=`text-accent-ink`。
3. **検証**: typecheck / lint / vitest。実機で全タブ (Parent/Target/Kitten) ＋ レポートを **light/dark 両方**スクショ確認。

## 4. 検証基準

- `tsc --noEmit` / `next lint` / `vitest` 緑。
- ハードコードのパレット色 (`(bg|text|border|ring|...)-(slate|sky|...)-\d+`) が **0** (全て意味トークン)。
- 両テーマでコンソールエラーなし、主要文字のコントラストが読めること。
- テーマ選択の localStorage 保存・リロード維持・system 追従・FOUC なし。

## 5. 今後の細部調整 (任意)

- コントラストの WCAG 厳密監査 (現状は目視確認)。
- `<meta name="theme-color">` (現状ダーク固定) のテーマ連動。
- 一部ボタンの hover 変化 (`bg-accent hover:bg-accent` になっている箇所) の微調整。
