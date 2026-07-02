export default function OfflinePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10 text-slate-900">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-sky-600">
          Cat Coat Planner
        </p>
        <h1 className="mt-2 text-xl font-bold">オフラインです</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          保存済みの画面や入力内容は確認できます。毛色計算や逆引き検索にはインターネット接続が必要です。
        </p>
        <a
          href="/"
          className="mt-5 inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700"
        >
          アプリへ戻る
        </a>
      </div>
    </main>
  );
}
