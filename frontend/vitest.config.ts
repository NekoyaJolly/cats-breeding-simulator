import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// このファイルが置かれている frontend/ ルートの絶対パス。
// tsconfig の paths "@/*" -> "./*" をテスト実行時にも解決するために使う。
const rootDir = dirname(fileURLToPath(import.meta.url));

// テスト二層構成:
// - lib/ の純粋ロジック: DOM 非依存なので environment=node (従来通り、高速)。
// - components/ の React コンポーネント/フック: jsdom 上で React Testing Library により検証する。
//   environmentMatchGlobs で対象パスごとに実行環境を割り当てる。
export default defineConfig({
  resolve: {
    // アプリコードが使う "@/..." エイリアスをテストでも解決する。
    alias: { "@": rootDir },
  },
  esbuild: {
    // テスト内 TSX を React 17+ の自動 JSX ランタイムで変換する
    // (各テストで React を明示 import しなくても JSX が動くようにする)。
    jsx: "automatic",
  },
  test: {
    // RTL の自動クリーンアップ (各テスト後の unmount) を有効化するためグローバル API を on にする。
    // 既存 lib テストは "vitest" から明示 import しており影響しない。
    globals: true,
    environment: "node",
    environmentMatchGlobs: [["components/**", "jsdom"]],
    include: ["lib/**/*.test.ts", "components/**/*.test.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
    coverage: {
      provider: "v8",
      include: ["lib/**/*.ts"],
      exclude: ["lib/**/*.test.ts"],
      reporter: ["text", "text-summary"],
    },
  },
});
