import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { act, renderHook } from "@testing-library/react";
import type { FormEvent } from "react";
import type { ReverseLookupResponse } from "@/lib/schema";

// API 通信はモックし、フックの状態遷移ロジックだけを検証する。
vi.mock("@/lib/api", () => ({
  fetchColors: vi.fn().mockResolvedValue([]),
  fetchBreeds: vi.fn().mockResolvedValue([]),
  searchTargetColor: vi.fn(),
}));

import { searchTargetColor } from "@/lib/api";
import { useTargetColorSearch } from "./useTargetColorSearch";

// submit イベントの最小スタブ (フックは preventDefault しか使わない)。
function submitEvent(): FormEvent<HTMLFormElement> {
  return { preventDefault: () => {} } as unknown as FormEvent<HTMLFormElement>;
}

// フックを描画し、マウント時の色/猫種ロード (モック Promise) を act 内で流してから返す。
// これをしないと解決時の state 更新が act 外になり警告が出る。
async function renderFlushed() {
  const utils = renderHook(() => useTargetColorSearch());
  await act(async () => {});
  return utils;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("useTargetColorSearch", () => {
  it("毛色を入力して登録すると cats に追加され、入力がクリアされる", async () => {
    const { result } = await renderFlushed();

    act(() => result.current.setColor("Blue"));
    act(() => result.current.handleAddCat(submitEvent()));

    expect(result.current.cats).toHaveLength(1);
    expect(result.current.cats[0].color).toBe("Blue");
    expect(result.current.cats[0].sex).toBe("female");
    expect(result.current.color).toBe("");
  });

  it("登録猫が無くても目標条件案内を検索 API から取得する", async () => {
    const response: ReverseLookupResponse = {
      status: "ok",
      target_color: "Blue",
      target_sex: null,
      response_category: "現在の情報では判定が難しい",
      target_conditions: ["D座位: d/d"],
      unchecked_conditions: ["父猫・母猫の両方が登録されていないため、交配候補を評価できません。"],
      recommended_checks: ["D座位（ダイリュート）の遺伝子検査"],
      candidates: [],
    };
    (searchTargetColor as Mock).mockResolvedValue({ ok: true, data: response });

    const { result } = await renderFlushed();

    act(() => result.current.setTargetColor("Blue"));
    await act(async () => {
      await result.current.handleSearch();
    });

    expect(searchTargetColor).toHaveBeenCalledWith({
      target_color: "Blue",
      target_sex: undefined,
      cats: [],
      limit: 20,
    });
    expect(result.current.result).toEqual(response);
  });

  it("2頭以上 + 目標カラーありで検索すると結果がセットされる", async () => {
    const response: ReverseLookupResponse = {
      status: "ok",
      target_color: "Blue",
      target_sex: null,
      response_category: "ok",
      target_conditions: [],
      unchecked_conditions: [],
      recommended_checks: [],
      candidates: [],
    };
    (searchTargetColor as Mock).mockResolvedValue({ ok: true, data: response });

    const { result } = await renderFlushed();

    act(() => result.current.setColor("Blue"));
    act(() => result.current.handleAddCat(submitEvent()));
    act(() => result.current.setColor("Black"));
    act(() => result.current.handleAddCat(submitEvent()));
    act(() => result.current.setTargetColor("Blue"));

    expect(result.current.cats).toHaveLength(2);

    await act(async () => {
      await result.current.handleSearch();
    });

    expect(searchTargetColor).toHaveBeenCalledTimes(1);
    expect(result.current.result).toEqual(response);
  });
});
