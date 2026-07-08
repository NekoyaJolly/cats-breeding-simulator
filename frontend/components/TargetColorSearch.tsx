"use client";

import type { ReactNode } from "react";
import type { RegisteredCat } from "@/lib/schema";
import { UI_TEXT, type Language } from "@/lib/i18n";
import { PARENT_GROUP_ACCENT_CLASS } from "@/lib/uiTone";
import { CarrierSelectorButton, type CarrierParent } from "./CarrierSelector";
import { ColorCombobox } from "./ColorCombobox";
import { FloatingSelect, FloatingTextInput } from "./FloatingField";
import { ResultsView } from "./targetColorSearch/ResultsView";
import { carriersText } from "./targetColorSearch/format";
import { useTargetColorSearch } from "./targetColorSearch/useTargetColorSearch";

const secondaryButtonClass =
  "rounded-md border border-line bg-surface px-3 py-2 text-sm font-medium text-ink-soft hover:bg-surface-2";
const sectionClass =
  "relative rounded-lg border border-line bg-surface px-4 pb-4 pt-5 shadow-sm sm:px-6 sm:pb-6 sm:pt-6";
const sectionTitleClass =
  "absolute -top-2.5 left-4 bg-surface px-1 text-sm font-semibold leading-5 text-ink-soft sm:left-6";

function SectionCard({
  title,
  children,
  tourId,
}: {
  title: string;
  children: ReactNode;
  tourId?: string;
}) {
  return (
    <section className={sectionClass} data-tour={tourId}>
      <h2 className={sectionTitleClass}>{title}</h2>
      {children}
    </section>
  );
}

function parentFromSex(sex: RegisteredCat["sex"]): CarrierParent {
  return sex === "male" ? "sire" : "dam";
}

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
    carrierSelection,
    setCarrierSelection,
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
    editCarrierSelection,
    setEditCarrierSelection,
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
    return sexValue === "male" ? text.common.male : text.common.female;
  }

  function carrierButtonLabel(sexValue: RegisteredCat["sex"]): string {
    return sexValue === "male"
      ? text.parentForm.carrierSelector.sireButton
      : text.parentForm.carrierSelector.damButton;
  }

  function renderCatList(groupCats: RegisteredCat[]) {
    if (groupCats.length === 0) {
      return (
        <p className="px-4 py-3 text-sm text-muted">
          {text.targetForm.emptyGroup}
        </p>
      );
    }
    return (
      <ul className="divide-y divide-line-soft">
        {groupCats.map((cat) => (
          <li key={cat.id} className="px-4 py-3 text-sm">
            {editingId === cat.id ? (
              <form onSubmit={handleSaveEdit} className="grid grid-cols-1 gap-3">
                <FloatingTextInput
                  id={`edit-name-${cat.id}`}
                  label={text.targetForm.name}
                  value={editName}
                  onChange={(event) => setEditName(event.target.value)}
                />
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <FloatingSelect
                    id={`edit-sex-${cat.id}`}
                    label={text.common.sex}
                    value={editSex}
                    onChange={(event) => setEditSex(event.target.value === "male" ? "male" : "female")}
                  >
                    <option value="female">{text.common.female}</option>
                    <option value="male">{text.common.male}</option>
                  </FloatingSelect>
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
                </div>
                <ColorCombobox
                  id={`edit-color-${cat.id}`}
                  label={text.targetForm.coat}
                  labelAction={
                    <CarrierSelectorButton
                      parent={parentFromSex(editSex)}
                      value={editCarrierSelection}
                      onChange={setEditCarrierSelection}
                      language={language}
                      buttonLabel={carrierButtonLabel(editSex)}
                      modalTitle={text.targetForm.carriersLabel}
                    />
                  }
                  value={editColor}
                  onValueChange={setEditColor}
                  onCommit={setEditColor}
                  colors={editColors}
                  recent={[]}
                  suggestionLayout="inline"
                  recentLabel={text.common.recent}
                  femaleOnlyLabel={text.common.femaleOnly}
                />
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink shadow-sm hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
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
                  <p className="font-medium text-ink">
                    {cat.name} <span className="text-muted">{catSexLabel(cat.sex)}</span>
                  </p>
                  <p className="text-xs text-muted">
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
    <div className="space-y-4 sm:space-y-6">
      <SectionCard title={text.targetForm.targetTitle} tourId="target-panel">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px_auto] md:items-start">
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
          <FloatingSelect
            id="target-sex"
            label={text.targetForm.targetSex}
            value={targetSex}
            onChange={(event) => {
              const value = event.target.value;
              setTargetSex(value === "male" || value === "female" ? value : "any");
            }}
          >
            <option value="any">{text.common.any}</option>
            <option value="male">{text.common.male}</option>
            <option value="female">{text.common.female}</option>
          </FloatingSelect>
          <button
            type="button"
            onClick={handleSearch}
            disabled={!targetColor.trim() || loading}
            className="h-11 rounded-md bg-accent px-4 text-sm font-semibold text-accent-ink shadow-sm hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? text.targetForm.loading : text.targetForm.button}
          </button>
        </div>
        {error && (
          <div className="mt-4 rounded-md border border-danger/30 bg-danger-bg p-3 text-sm text-danger">
            {error}
          </div>
        )}
      </SectionCard>

      {result && (
        <section className="rounded-lg border border-line bg-surface p-4 shadow-sm sm:p-6">
          <ResultsView data={result} language={language} />
        </section>
      )}

      <SectionCard title={text.targetForm.registrationTitle}>
        <form onSubmit={handleAddCat} className="grid grid-cols-1 gap-3">
          <FloatingTextInput
            id="registered-cat-name"
            label={text.targetForm.name}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={text.targetForm.namePlaceholder}
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <FloatingSelect
              id="registered-cat-sex"
              label={text.common.sex}
              value={sex}
              onChange={(event) => setSex(event.target.value === "male" ? "male" : "female")}
            >
              <option value="female">{text.common.female}</option>
              <option value="male">{text.common.male}</option>
            </FloatingSelect>
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
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
            <ColorCombobox
              id="registered-cat-color"
              label={text.targetForm.coat}
              labelAction={
                <CarrierSelectorButton
                  parent={parentFromSex(sex)}
                  value={carrierSelection}
                  onChange={setCarrierSelection}
                  language={language}
                  buttonLabel={carrierButtonLabel(sex)}
                  modalTitle={text.targetForm.carriersLabel}
                />
              }
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
              className={`${secondaryButtonClass} h-11 whitespace-nowrap`}
              onClick={addColorInput}
            >
              {text.targetForm.addCoat}
            </button>
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
                placeholder={text.targetForm.coatPlaceholder}
                suggestionLayout="inline"
                recentLabel={text.common.recent}
                femaleOnlyLabel={text.common.femaleOnly}
              />
              <button
                type="button"
                className={`${secondaryButtonClass} h-11 whitespace-nowrap`}
                onClick={() => removeAdditionalColor(entryColor.id)}
              >
                {text.common.delete}
              </button>
            </div>
          ))}
          <button
            type="submit"
            className="w-full rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-ink shadow-sm hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            disabled={colorsToRegister.length === 0}
          >
            {text.targetForm.addCandidate}
          </button>
        </form>
        {registrationError && (
          <div className="mt-4 rounded-md border border-danger/30 bg-danger-bg p-3 text-sm text-danger">
            {registrationError}
          </div>
        )}

        <div className="mt-5 space-y-2">
          <h3 className="text-sm font-semibold text-ink-soft">
            {text.targetForm.savedTitle}
          </h3>
          {cats.length === 0 ? (
            <p className="text-sm text-muted">
              {text.targetForm.savedEmpty}
            </p>
          ) : (
            <div className="space-y-2">
              <details className={`rounded-md border ${PARENT_GROUP_ACCENT_CLASS.sire}`}>
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-ink-soft">
                  <span>{text.targetForm.sireGroup}</span>
                  <span className="text-muted">
                    {language === "ja" ? `${sires.length} 件` : sires.length}
                  </span>
                </summary>
                {renderCatList(sires)}
              </details>
              <details className={`rounded-md border ${PARENT_GROUP_ACCENT_CLASS.dam}`}>
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-ink-soft">
                  <span>{text.targetForm.damGroup}</span>
                  <span className="text-muted">
                    {language === "ja" ? `${dams.length} 件` : dams.length}
                  </span>
                </summary>
                {renderCatList(dams)}
              </details>
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
