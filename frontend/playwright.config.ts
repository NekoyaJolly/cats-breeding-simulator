import { defineConfig, devices } from "@playwright/test";

// E2E (ゴールデンパス) 用設定。
// バックエンド API はテスト内の page.route で差し替えるため、ここでは起動しない。
// dev サーバーを 3100 番で立ち上げ、その URL に対して Chromium で検証する。
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // CI で test.only の取り残しを防ぐ。
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3100",
    // 失敗(再試行)時のみトレースを残す。
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- -p 3100",
    url: "http://localhost:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
