export default function OfflinePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10 text-ink">
      <div className="rounded-lg border border-line bg-surface p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">
          Cat Coat Planner
        </p>
        <h1 className="mt-2 text-xl font-bold">オフラインです</h1>
        <p className="mt-3 text-sm leading-6 text-ink-soft">
          保存済みの画面や入力内容は確認できます。毛色計算や逆引き検索にはインターネット接続が必要です。
        </p>
        <a
          href="/"
          className="mt-5 inline-flex rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink shadow-sm hover:bg-accent/90"
        >
          アプリへ戻る
        </a>
      </div>
    </main>
  );
}
