import { beforeEach, describe, expect, it, vi } from "vitest";

import { createLocalStoreRepository } from "./localStoreRepository";
import {
  activeRegisteredCats,
  createEmptyLocalStoreState,
  legacyRegisteredCatsToState,
  type LocalStoreState,
} from "./localStoreSchema";
import type { RegisteredCat } from "./schema";

const openDbMock = vi.hoisted(() => vi.fn());

vi.mock("idb", () => ({
  openDB: openDbMock,
}));

type StorageStub = {
  store: Record<string, string>;
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
};

type MockDb = {
  objectStoreNames: {
    contains: ReturnType<typeof vi.fn>;
  };
  createObjectStore: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  readState: () => LocalStoreState | undefined;
};

const CAT: RegisteredCat = { id: "cat-1", name: "クロ", sex: "male", color: "Black" };
const LEGACY_KEY = "cbs:registeredCats";
const FALLBACK_KEY = "cbs:localStore:v1";

function makeStorage(initial: Record<string, string> = {}): StorageStub {
  const store: Record<string, string> = { ...initial };
  return {
    store,
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = value;
    },
  };
}

function stubWindow(storage: StorageStub, indexedDbAvailable = true): void {
  vi.stubGlobal("window", {
    indexedDB: indexedDbAvailable ? {} : undefined,
    localStorage: storage,
  });
}

function configureOpenDb(initialState?: LocalStoreState): MockDb {
  let state = initialState;
  const db: MockDb = {
    objectStoreNames: {
      contains: vi.fn(() => false),
    },
    createObjectStore: vi.fn(),
    get: vi.fn(async () => state),
    put: vi.fn(async (_storeName: string, value: LocalStoreState) => {
      state = value;
    }),
    readState: () => state,
  };
  openDbMock.mockImplementation(
    async (
      _name: string,
      _version: number,
      options?: { upgrade?: (database: MockDb) => void },
    ) => {
      options?.upgrade?.(db);
      return db;
    },
  );
  return db;
}

beforeEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  openDbMock.mockReset();
});

describe("createLocalStoreRepository", () => {
  it("初回loadStateで旧登録猫localStorageから移行してIndexedDBへputする", async () => {
    const storage = makeStorage({ [LEGACY_KEY]: JSON.stringify([CAT]) });
    stubWindow(storage);
    const db = configureOpenDb();

    const state = await createLocalStoreRepository().loadState();

    expect(activeRegisteredCats(state)).toEqual([CAT]);
    expect(db.createObjectStore).toHaveBeenCalledWith("localStore");
    expect(db.put).toHaveBeenCalledTimes(1);
    expect(activeRegisteredCats(db.readState() ?? createEmptyLocalStoreState())).toEqual([CAT]);
  });

  it("2回目以降のloadStateはIndexedDBへ保存済みの状態から復元する", async () => {
    const storage = makeStorage({ [LEGACY_KEY]: JSON.stringify([CAT]) });
    stubWindow(storage);
    const db = configureOpenDb();
    const repo = createLocalStoreRepository();

    await repo.loadState();
    storage.store[LEGACY_KEY] = JSON.stringify([
      { id: "cat-2", name: "別猫", sex: "female", color: "Blue" },
    ]);
    const secondState = await repo.loadState();

    expect(openDbMock).toHaveBeenCalledTimes(1);
    expect(db.get).toHaveBeenCalledTimes(2);
    expect(activeRegisteredCats(secondState)).toEqual([CAT]);
  });

  it("openDBが失敗した後はfallbackし、次回loadStateでIndexedDBを再試行する", async () => {
    const storage = makeStorage({ [LEGACY_KEY]: JSON.stringify([CAT]) });
    stubWindow(storage);
    openDbMock.mockRejectedValueOnce(new Error("indexedDB blocked"));
    const db = configureOpenDb();
    const repo = createLocalStoreRepository();

    const fallbackState = await repo.loadState();
    const retriedState = await repo.loadState();

    expect(activeRegisteredCats(fallbackState)).toEqual([CAT]);
    expect(activeRegisteredCats(retriedState)).toEqual([CAT]);
    expect(openDbMock).toHaveBeenCalledTimes(2);
    expect(db.put).toHaveBeenCalledTimes(1);
  });

  it("IndexedDBのput失敗時はlocalStorage fallbackへ保存する", async () => {
    const storage = makeStorage();
    stubWindow(storage);
    const db = configureOpenDb();
    db.put.mockRejectedValueOnce(new Error("put failed"));
    const state = legacyRegisteredCatsToState([CAT], "2026-07-02T00:00:00.000Z");

    await createLocalStoreRepository().saveState(state);

    expect(storage.store[FALLBACK_KEY]).toContain("cat-1");
  });
});
