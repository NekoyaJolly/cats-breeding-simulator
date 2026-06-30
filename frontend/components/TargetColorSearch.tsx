"use client";

import type { RegisteredCat } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { PARENT_GROUP_ACCENT_CLASS } from "@/lib/uiTone";
import { ColorCombobox } from "./ColorCombobox";
import { ResultsView } from "./targetColorSearch/ResultsView";
import { carriersText } from "./targetColorSearch/format";
import { useTargetColorSearch } from "./targetColorSearch/useTargetColorSearch";

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";
const labelClass = "block text-sm font-medium text-slate-700";
const secondaryButtonClass =
  "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50";
// 「目標カラーから探す」画面。状態とロジックは useTargetColorSearch に集約し、
// このコンポーネントは表示と入力ハンドラの結線に専念する。
export function TargetColorSearch({ language }: { language: Language }) {
  const text = UI_TEXT[language];
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
  } = useTargetColorSearch(text.common.geneticsAffects);

  function catSexLabel(sexValue: RegisteredCat["sex"]): string {
    return sexValue === "male"
      ? text.common.maleCandidate
      : text.common.femaleCandidate;
  }

  function renderCatList(groupCats: RegisteredCat[]) {
    if (groupCats.length === 0) {
      return (
        <p className="px-4 py-3 text-sm text-slate-500">
          {text.targetForm.emptyGroup}
        </p>
      );
    }
    return (
      <ul className="divide-y divide-slate-100">
        {groupCats.map((cat) => (
          <li key={cat.id} className="px-4 py-3 text-sm">
            {editingId === cat.id ? (
              <form onSubmit={handleSaveEdit} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label htmlFor={`edit-name-${cat.id}`} className={labelClass}>
                    {text.targetForm.name}
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
                    {text.common.sex}
                  </label>
                  <select
                    id={`edit-sex-${cat.id}`}
                    className={inputClass}
                    value={editSex}
                    onChange={(event) => setEditSex(event.target.value === "male" ? "male" : "female")}
                  >
                    <option value="female">{text.common.femaleCandidate}</option>
                    <option value="male">{text.common.maleCandidate}</option>
                  </select>
                </div>
                <ColorCombobox
                  id={`edit-color-${cat.id}`}
                  label={text.targetForm.coat}
                  value={editColor}
                  onValueChange={setEditColor}
                  onCommit={setEditColor}
                  colors={editColors}
                  recent={[]}
                  suggestionLayout="inline"
                  recentLabel={text.common.recent}
                  femaleOnlyLabel={text.common.femaleOnly}
                />
                <ColorCombobox
                  id={`edit-breed-${cat.id}`}
                  label={text.common.breed}
                  value={editBreed}
                  onValueChange={setEditBreed}
                  onCommit={setEditBreed}
                  colors={breedItems}
                  recent={[]}
                  recentLabel={text.common.recent}
                  femaleOnlyLabel={text.common.femaleOnly}
                />
                <div className="space-y-1 md:col-span-2">
                  <label htmlFor={`edit-carriers-${cat.id}`} className={labelClass}>
                    {text.targetForm.carriers}
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
                    {text.common.update}
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={cancelEdit}>
                    {text.common.cancel}
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-800">
                    {cat.name} <span className="text-slate-400">{catSexLabel(cat.sex)}</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    {cat.color}
                    {cat.breed ? ` / ${cat.breed}` : ""}
                    {cat.carriers
                      ? ` / ${text.targetForm.carriersLabel}: ${carriersText(cat.carriers)}`
                      : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button type="button" className={secondaryButtonClass} onClick={() => startEdit(cat)}>
                    {text.common.edit}
                  </button>
                  <button type="button" className={secondaryButtonClass} onClick={() => removeCat(cat.id)}>
                    {text.common.remove}
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
        <h2 className="text-lg font-semibold text-slate-800">
          {text.targetForm.registrationTitle}
        </h2>
        <form onSubmit={handleAddCat} className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <label htmlFor="registered-cat-name" className={labelClass}>
              {text.targetForm.name}
            </label>
            <input
              id="registered-cat-name"
              className={inputClass}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={text.targetForm.namePlaceholder}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="registered-cat-sex" className={labelClass}>
              {text.common.sex}
            </label>
            <select
              id="registered-cat-sex"
              className={inputClass}
              value={sex}
              onChange={(event) => setSex(event.target.value === "male" ? "male" : "female")}
            >
              <option value="female">{text.common.femaleCandidate}</option>
              <option value="male">{text.common.maleCandidate}</option>
            </select>
          </div>
          <div className="space-y-3 md:col-span-2">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
                <ColorCombobox
                  id="registered-cat-color"
                  label={text.targetForm.coat}
                  value={color}
                  onValueChange={setColor}
                  onCommit={setColor}
                  colors={registrationColors}
                  recent={[]}
                  placeholder={text.targetForm.coatPlaceholder}
                  suggestionLayout="inline"
                  recentLabel={text.common.recent}
                  femaleOnlyLabel={text.common.femaleOnly}
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={addColorInput}
                >
                  {text.targetForm.addCoat}
                </button>
              </div>
              <ColorCombobox
                id="registered-cat-breed"
                label={text.common.breed}
                value={breed}
                onValueChange={setBreed}
                onCommit={setBreed}
                colors={breedItems}
                recent={[]}
                placeholder={text.targetForm.breedPlaceholder}
                recentLabel={text.common.recent}
                femaleOnlyLabel={text.common.femaleOnly}
              />
            </div>
            {additionalColors.map((entryColor, index) => (
              <div
                key={entryColor.id}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2"
              >
                <ColorCombobox
                  id={`registered-cat-additional-color-${entryColor.id}`}
                  label={`${text.targetForm.additionalCoat} ${index + 1}`}
                  value={entryColor.value}
                  onValueChange={(value) => updateAdditionalColor(entryColor.id, value)}
                  onCommit={(value) => updateAdditionalColor(entryColor.id, value)}
                  colors={registrationColors}
                  recent={[]}
                  placeholder={language === "ja" ? "例: Lilac" : "e.g. Lilac"}
                  suggestionLayout="inline"
                  recentLabel={text.common.recent}
                  femaleOnlyLabel={text.common.femaleOnly}
                />
                <button
                  type="button"
                  className={`${secondaryButtonClass} mt-6 whitespace-nowrap`}
                  onClick={() => removeAdditionalColor(entryColor.id)}
                >
                  {text.common.delete}
                </button>
              </div>
            ))}
          </div>
          <div className="space-y-1 md:col-span-2">
            <label htmlFor="registered-cat-carriers" className={labelClass}>
              {text.targetForm.carriers}
            </label>
            <input
              id="registered-cat-carriers"
              className={inputClass}
              value={carriers}
              onChange={(event) => setCarriers(event.target.value)}
              placeholder={text.targetForm.carriersPlaceholder}
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={colorsToRegister.length === 0}
            >
              {text.targetForm.addCandidate}
            </button>
          </div>
        </form>
        {registrationError && (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {registrationError}
          </div>
        )}

        <div className="mt-5 space-y-2">
          <h3 className="text-sm font-semibold text-slate-700">
            {text.targetForm.savedTitle}
          </h3>
          {cats.length === 0 ? (
            <p className="text-sm text-slate-500">
              {text.targetForm.savedEmpty}
            </p>
          ) : (
            <div className="space-y-2">
              <details className={`rounded-md border ${PARENT_GROUP_ACCENT_CLASS.sire}`}>
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>{text.targetForm.sireGroup}</span>
                  <span className="text-slate-400">
                    {language === "ja" ? `${sires.length} 件` : sires.length}
                  </span>
                </summary>
                {renderCatList(sires)}
              </details>
              <details className={`rounded-md border ${PARENT_GROUP_ACCENT_CLASS.dam}`}>
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
                  <span>{text.targetForm.damGroup}</span>
                  <span className="text-slate-400">
                    {language === "ja" ? `${dams.length} 件` : dams.length}
                  </span>
                </summary>
                {renderCatList(dams)}
              </details>
            </div>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-800">
          {text.targetForm.targetTitle}
        </h2>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_180px_auto] md:items-end">
          <ColorCombobox
            id="target-color"
            label={text.targetForm.targetCoat}
            value={targetColor}
            onValueChange={setTargetColor}
            onCommit={setTargetColor}
            colors={targetColors}
            recent={[]}
            placeholder={text.targetForm.targetPlaceholder}
            recentLabel={text.common.recent}
            femaleOnlyLabel={text.common.femaleOnly}
          />
          <div className="space-y-1">
            <label htmlFor="target-sex" className={labelClass}>
              {text.targetForm.targetSex}
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
              <option value="any">{text.common.any}</option>
              <option value="male">{text.common.male}</option>
              <option value="female">{text.common.female}</option>
            </select>
          </div>
          <button
            type="button"
            onClick={handleSearch}
            disabled={!targetColor.trim() || cats.length < 2 || loading}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? text.targetForm.loading : text.targetForm.button}
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
          <ResultsView data={result} language={language} />
        </section>
      )}
    </div>
  );
}
