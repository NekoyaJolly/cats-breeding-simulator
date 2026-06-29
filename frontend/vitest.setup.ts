// React Testing Library のカスタムマッチャ (toBeInTheDocument 等) を
// Vitest の expect に登録する。全テストの実行前に読み込まれる (vitest.config.ts の setupFiles)。
// 理由: jest-dom のマッチャが無いとコンポーネントの表示検証を簡潔に書けないため。
import "@testing-library/jest-dom/vitest";
