"use client";

import type { RegisteredCat } from "@/lib/schema";
import { ColorCombobox } from "./ColorCombobox";
import { ResultsView } from "./targetColorSearch/ResultsView";
import { carriersText, sexLabel } from "./targetColorSearch/format";
import { useTargetColorSearch } from "./targetColorSearch/useTargetColorSearch";

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";
const secondaryButtonClass =
  "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50";

// 「目標カラーから探す」画面。状態とロジックは useTargetColorSearch に集約し、
// このコンポーネントは表示と入力ハンドラの結線に専念する。
export function TargetColorSearch() {
  const {
    name,
    setName,
    sex,
    setSex,
    color,
    setColor,
    additionalColors,
    addColorInput,
    updateAdditionalColor,
    removeAdditionalColor,
    breed,
    setBreed,
    carriers,
    setCarriers,
    colorsToRegister,
    registrationColors,
    handleAddCat,
    registrationError,
    cats,
    sires,
    dams,
    removeCat,
    editingId,
    editName,
    setEditName,
    editSex,
    setEditSex,
    editColor,
    setEditColor,
    editBreed,
    setEditBreed,
    editCarriers,
    setEditCarriers,
    editColors,
    startEdit,
    cancelEdit,
    handleSaveEdit,
    targetColors,
    breedItems,
    targetColor,
    setTargetColor,
    targetSex,
    setTargetSex,
    loading,
    error,
    result,
    handleSearch,
  } = useTargetColorSearch();

  function renderCatList(groupCats: RegisteredCat[]) {
    if (groupCats.length === 0) {
      return <p className="px-4 py-3 text-sm text-slate-500">まだ登録されていません。</p>;
    }
    return (
      <ul className="divide-y divide-slate-100">
        {groupCats.map((cat) => (
          <li key={cat.id} className="px-4 py-3 text-sm">
            {editingId === cat.id ? (
              <form onSubmit={handleSaveEdit} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label htmlFor={`edit-name-${cat.id}`} className={labelClass}>
                    登録名
                  </label>
                  <input
                    id={`edit-name-${cat.id}`}
                    className={inputClass}
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor={`edit-sex-${cat.id}`} className={labelClass}>
                    性別
                  </label>
                  <select
                    id={`edit-sex-${cat.id}`}
                    className={inputClass}
                    value={editSex}
                    onChange={(event) => setEditSex(event.target.value === "male" ? "male" : "female")}
                  >
                    <option value="female">♀ 母猫候補</option>
                    <option value="male">♂ 父猫候補</option>
                  </select>
                </div>
                <ColorCombobox
                  id={`edit-color-${cat.id}`}
                  label="毛色"
                  value={editColor}
                  onValueChange={setEditColor}
                  onCommit={setEditColor}
                  colors={editColors}
                  recent={[]}
                  suggestionLayout="inline"
                />
                <ColorCombobox
                  id={`edit-breed-${cat.id}`}
                  label="猫種 (任意)"
                  value={editBreed}
                  onValueChange={setEditBreed}
                  onCommit={setEditBreed}
                  colors={breedItems}
                  recent={[]}
                />
                <div className="space-y-1 md:col-span-2">
                  <label htmlFor={`edit-carriers-${cat.id}`} className={labelClass}>
                    確認済み因子 (任意)
                  </label>
                  <input
                    id={`edit-carriers-${cat.id}`}
                    className={inputClass}
                    value={editCarriers}
                    onChange={(event) => setEditCarriers(event.target.value)}
                    placeholder="例: B:B/b, D:D/d"
                  />
                </div>
                <div className="flex gap-2 md:col-span-2">
                  <button
                    type="submit"
                    className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!editName.trim() || !editColor.trim()}
                  >
                    更新する
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={cancelEdit}>
                    キャンセル
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    {cat.name} <span className="text-slate-400">{sexLabel(cat.sex)}</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {cat.color}
                    {cat.breed ? ` / ${cat.breed}` : ""}
                    {cat.carriers ? ` / 確認済み因子: ${carriersText(cat.carriers)}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className={secondaryButtonClass} onClick={() => startEdit(cat)}>
                    編集
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={() => removeCat(cat.id)}>
                    登録から外す
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">両親猫のカラー登録</h2>
        <form onSubmit={handleAddCat} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <label htmlFor="registered-cat-name" className={labelClass}>
              登録名
            </label>
            <input
              id="registered-cat-name"
              className={inputClass}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例: 青系の父"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="registered-cat-sex" className={labelClass}>
              性別
            </label>
            <select
              id="registered-cat-sex"
              className={inputClass}
              value={sex}
              onChange={(event) => setSex(event.target.value === "male" ? "male" : "female")}
            >
              <option value="female">♀ 母猫候補</option>
              <option value="male">♂ 父猫候補</option>
            </select>
          </div>
          <div className="space-y-3 md:col-span-2">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
                <ColorCombobox
                  id="registered-cat-color"
                  label="毛色"
                  value={color}
                  onValueChange={setColor}
                  onCommit={setColor}
                  colors={registrationColors}
                  recent={[]}
                  placeholder="例: Blue / Chocolate"
                  suggestionLayout="inline"
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={addColorInput}
                >
                  ＋ カラー追加
                </button>
              </div>
              <ColorCombobox
                id="registered-cat-breed"
                label="猫種 (任意)"
                value={breed}
                onValueChange={setBreed}
                onCommit={setBreed}
                colors={breedItems}
                recent={[]}
                placeholder="例: British Shorthair"
              />
            </div>
            {additionalColors.map((entryColor, index) => (
              <div
                key={entryColor.id}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2"
              >
                <ColorCombobox
                  id={`registered-cat-additional-color-${entryColor.id}`}
                  label={`追加カラー ${index + 1}`}
                  value={entryColor.value}
                  onValueChange={(value) => updateAdditionalColor(entryColor.id, value)}
                  onCommit={(value) => updateAdditionalColor(entryColor.id, value)}
                  colors={registrationColors}
                  recent={[]}
                  placeholder="例: Lilac"
                  suggestionLayout="inline"
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={() => removeAdditionalColor(entryColor.id)}
                >
                  削除
                </button>
              </div>
            ))}
          </div>
          <div className="space-y-1 md:col-span-2">
            <label htmlFor="registered-cat-carriers" className={labelClass}>
              確認済み因子 (任意)
            </label>
            <input
              id="registered-cat-carriers"
              className={inputClass}
              value={carriers}
              onChange={(event) => setCarriers(event.target.value)}
              placeholder="例: B:B/b, D:D/d"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={colorsToRegister.length === 0}
            >
              登録する
            </button>
          </div>
        </form>
        {registrationError && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {registrationError}
          </div>
        )}

        <div className="mt-5 space-y-2">
          <h3 className="text-sm font-semibold text-slate-700">自舎カラー構成</h3>
          {cats.length === 0 ? (
            <p className="text-sm text-slate-500">
              父候補・母候補のカラーを追加すると、目標カラーの交配候補を検索できます。
            </p>
          ) : (
            <div className="space-y-2">
              <details className="rounded-md border border-slate-200 bg-white">
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>父候補</span>
                  <span className="text-slate-400">{sires.length} 件</span>
                </summary>
                {renderCatList(sires)}
              </details>
              <details className="rounded-md border border-slate-200 bg-white">
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>母候補</span>
                  <span className="text-slate-400">{dams.length} 件</span>
                </summary>
                {renderCatList(dams)}
              </details>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">目標カラーの選択</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_180px_auto] md:items-end">
          <ColorCombobox
            id="target-color"
            label="目標カラー"
            value={targetColor}
            onValueChange={setTargetColor}
            onCommit={setTargetColor}
            colors={targetColors}
            recent={[]}
            placeholder="例: Lilac / Cinnamon Golden Tabby"
          />
          <div className="space-y-1">
            <label htmlFor="target-sex" className={labelClass}>
              子猫の性別 (任意)
            </label>
            <select
              id="target-sex"
              className={inputClass}
              value={targetSex}
              onChange={(event) => {
                const value = event.target.value;
                setTargetSex(value === "male" || value === "female" ? value : "any");
              }}
            >
              <option value="any">指定なし</option>
              <option value="male">♂ オス</option>
              <option value="female">♀ メス</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleSearch}
            disabled={!targetColor.trim() || cats.length < 2 || loading}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "検索中…" : "交配候補を検索"}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </section>

      {result && (
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <ResultsView data={result} />
        </section>
      )}
    </div>
  );
}
