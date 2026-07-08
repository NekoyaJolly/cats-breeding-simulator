// 見出し付きの箇条書きを表示する小さな表示用コンポーネント。
// 成立条件・確認が必要な条件・推奨検査など、複数箇所で再利用する。
export function InfoList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-bg p-3 text-sm">
      <p className="font-medium text-ink-soft">{title}</p>
      <ul className="mt-1 space-y-1 text-xs leading-5 text-ink-soft">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
