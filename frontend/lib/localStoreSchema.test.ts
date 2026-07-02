import { describe, expect, it } from "vitest";

import {
  CALCULATION_HISTORY_LIMIT,
  activeRegisteredCats,
  createEmptyLocalStoreState,
  exportLocalStoreState,
  importLocalStoreState,
  legacyRegisteredCatsToState,
  mergeRegisteredCatsForStorage,
  type CalculationHistoryEntry,
} from "./localStoreSchema";
import type { RegisteredCat } from "./schema";

const NOW = "2026-07-02T00:00:00.000Z";
const CAT: RegisteredCat = { id: "cat-1", name: "クロ", sex: "male", color: "Black" };

function historyEntry(index: number): CalculationHistoryEntry {
  return {
    id: `history-${index}`,
    kind: "parent-coat",
    title: `履歴 ${index}`,
    inputSummary: ["Black x Blue"],
    resultSummary: ["Black 50%"],
    createdAt: NOW,
    syncStatus: "local",
    updatedAt: NOW,
  };
}

describe("localStoreSchema", () => {
  it("空のStorage v1状態を作成する", () => {
    expect(createEmptyLocalStoreState()).toEqual({
      schemaVersion: 1,
      registeredCats: [],
      candidatePairs: [],
      breedingPlans: [],
      litterRecords: [],
      carrierFacts: [],
      calculationHistory: [],
      userSettings: { historyLimit: CALCULATION_HISTORY_LIMIT },
    });
  });

  it("旧登録猫データを同期予約フィールド付きへ移行する", () => {
    const state = legacyRegisteredCatsToState([CAT], NOW);
    expect(state.registeredCats[0]).toMatchObject({
      ...CAT,
      syncStatus: "local",
      updatedAt: NOW,
    });
    expect(activeRegisteredCats(state)).toEqual([CAT]);
  });

  it("登録猫の削除はdeletedAt付きで保持し、UI返却時は除外する", () => {
    const storedCats = mergeRegisteredCatsForStorage([CAT], [], NOW);
    const nextState = {
      ...createEmptyLocalStoreState(),
      registeredCats: mergeRegisteredCatsForStorage([], storedCats, NOW),
    };

    expect(nextState.registeredCats[0].deletedAt).toBe(NOW);
    expect(activeRegisteredCats(nextState)).toEqual([]);
  });

  it("import/exportはschemaVersion付きJSONを往復し、履歴上限を20件に丸める", () => {
    const state = {
      ...createEmptyLocalStoreState(),
      calculationHistory: Array.from({ length: 25 }, (_, index) => historyEntry(index)),
    };

    const imported = importLocalStoreState(exportLocalStoreState(state));

    expect(imported?.schemaVersion).toBe(1);
    expect(imported?.calculationHistory).toHaveLength(20);
  });

  it("不正JSONやスキーマ不一致のimportはnullを返す", () => {
    expect(importLocalStoreState("{壊れた")).toBeNull();
    expect(importLocalStoreState(JSON.stringify({ schemaVersion: 999 }))).toBeNull();
  });
});
