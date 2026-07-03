---
document: pipeline-state
project: cats-breeding-simulator
created: 2026-06-29
---

# パイプライン状態

- **プロジェクト**: cats-breeding-simulator
- **開始日**: 2026-06-29
- **現在フェーズ**: Phase 1（事業検証）
- **ステータス**: AWAITING_APPROVAL

## フェーズ履歴

| フェーズ | ステータス | 開始 | 完了 | ゲート結果 |
|---------|----------|------|------|-----------|
| Phase 0 | DONE | 2026-06-29 | 2026-06-29 | アイディア＝逆引き/リター推定の優位性検証 |
| Phase 1 | IN_PROGRESS | 2026-06-29 | - | Gate 1 未実施 |

## 現在の指示

market-validation.md（実機・コード検証済み）を作成。優位性は「逆引き＋リター推定の組み合わせ」に確定。
「世界初」「独自アルゴリズムがモート」等の誇張は撤回済み。
次アクション：Nekoの判断（事業として進めるか）→ Gate 1（quality-reviewer）レビュー。

## 申し送り：Gate 1 正確性ゲート（White座位 + 往復整合）2026-07-03 完了

White（優性白）の展開ポリシー修正と、3モードを1本の正確性で束ねる往復整合ゲートを実装した。

- **実装**（WHITE-1〜4 / GATE-1〜2）
  - 順方向: 入力が White のときのみ W を W/w 展開（他色不変）。父White=§2.1（白50%+母の色+AOC）、
    母White=§2.2（白50%+AOC50%）を専用集計。AOC（Any Other Color）は集約カテゴリで命名パイプライン非対象。
  - リター推定: White 親の下地を全不明として開き、「矛盾」→「推定可能」へ。色付きの子から W/w を確定。
  - UI: AOC 行はフォーカス/タップ時のみ説明ツールチップ（explicit_carrier への導線）。
  - ゲート: `tests/test_roundtrip_consistency.py`（契約1〜3・代表12ケース・R1/R2固定）。
- **正本統合**: V9 §2.4（A''=White の条件付き W 展開）・§4.5（W Locus normal 割合）・§6.1（AOC 特例）へ反映済み。
  `NORMAL_OPENED_LOCI` は非White診断メタ用に据え置き、W 展開は `dominant_expandable`（White のみ作用）で実現。
- **検証**: バックエンド 369 / フロント 108 テスト緑（既存 golden/130x204/mendelian 不変、White|Black golden のみ意図的再生成）。
- **次アクション（保留座位の往復縛り）**: Wb系（Shell/Shaded/Chinchilla/Golden）と C系 review_required（Point/Mink/Sepia）が
  確定次第、REPRESENTATIVE_CASES に追加して往復で縛る。White×White・White＋猫種のリター、赤母×White父の
  「母の色」精緻化も次段の候補。
