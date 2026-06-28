import { defineConfig } from "vitest/config";

// lib/ の純粋ロジックを対象とするユニットテスト設定。
// DOM 非依存のため environment は node。カバレッジは lib/ のみを対象に絞る。
export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
    coverage: {
      provider: "v8",
      include: ["lib/**/*.ts"],
      exclude: ["lib/**/*.test.ts"],
      reporter: ["text", "text-summary"],
    },
  },
});
