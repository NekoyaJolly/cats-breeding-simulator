import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import { z } from "zod";
import {
  activeRegisteredCats,
  createEmptyLocalStoreState,
  exportLocalStoreState,
  importLocalStoreState,
  legacyRegisteredCatsToState,
  mergeRegisteredCatsForStorage,
  normalizeLocalStoreState,
  parseJsonValue,
  type LocalStoreState,
} from "./localStoreSchema";
import { registeredCatSchema, type RegisteredCat } from "./schema";

const DB_NAME = "cats-breeding-simulator";
const DB_VERSION = 1;
const STORE_NAME = "localStore";
const STATE_KEY = "state-v1";
const FALLBACK_STORAGE_KEY = "cbs:localStore:v1";
const LEGACY_REGISTERED_CATS_KEY = "cbs:registeredCats";

interface CatsLocalStoreDb extends DBSchema {
  localStore: {
    key: typeof STATE_KEY;
    value: LocalStoreState;
  };
}

/** Local Store v1全体を読み書きするRepository抽象。 */
export type LocalStoreRepository = {
  loadState: () => Promise<LocalStoreState>;
  saveState: (state: LocalStoreState) => Promise<void>;
  updateState: (updater: (state: LocalStoreState) => LocalStoreState) => Promise<LocalStoreState>;
  exportJson: () => Promise<string>;
  importJson: (raw: string) => Promise<LocalStoreState | null>;
};

let dbPromise: Promise<IDBPDatabase<CatsLocalStoreDb>> | null = null;

function hasIndexedDb(): boolean {
  return typeof window !== "undefined" && "indexedDB" in window;
}

function hasLocalStorage(): boolean {
  return typeof window !== "undefined" && "localStorage" in window;
}

function nowIsoString(): string {
  return new Date().toISOString();
}

function openLocalStoreDb(): Promise<IDBPDatabase<CatsLocalStoreDb>> {
  dbPromise ??= openDB<CatsLocalStoreDb>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    },
  });
  return dbPromise;
}

function resetIndexedDbConnection(): void {
  dbPromise = null;
}

async function openLocalStoreDbOrNull(): Promise<IDBPDatabase<CatsLocalStoreDb> | null> {
  if (!hasIndexedDb()) return null;
  try {
    return await openLocalStoreDb();
  } catch {
    resetIndexedDbConnection();
    return null;
  }
}

function loadLegacyRegisteredCats(now: string): LocalStoreState | null {
  if (!hasLocalStorage()) return null;
  const raw = window.localStorage.getItem(LEGACY_REGISTERED_CATS_KEY);
  if (raw === null) return null;
  const parsedJson = parseJsonValue(raw);
  if (parsedJson === null) return null;
  const parsedCats = z.array(registeredCatSchema).safeParse(parsedJson);
  if (!parsedCats.success) return null;
  return legacyRegisteredCatsToState(parsedCats.data, now);
}

function loadFallbackState(): LocalStoreState {
  if (!hasLocalStorage()) return createEmptyLocalStoreState();
  const raw = window.localStorage.getItem(FALLBACK_STORAGE_KEY);
  if (raw !== null) {
    const parsedJson = parseJsonValue(raw);
    if (parsedJson !== null) return normalizeLocalStoreState(parsedJson);
  }
  return loadLegacyRegisteredCats(nowIsoString()) ?? createEmptyLocalStoreState();
}

function saveFallbackState(state: LocalStoreState): void {
  if (!hasLocalStorage()) return;
  try {
    window.localStorage.setItem(FALLBACK_STORAGE_KEY, exportLocalStoreState(state));
  } catch {
    // fallback保存も失敗する環境では、画面状態の維持を優先して永続化だけ諦める。
  }
}

export function createLocalStoreRepository(): LocalStoreRepository {
  async function loadState(): Promise<LocalStoreState> {
    const db = await openLocalStoreDbOrNull();
    if (db === null) return loadFallbackState();
    try {
      const stored = await db.get(STORE_NAME, STATE_KEY);
      if (stored) return normalizeLocalStoreState(stored);
      const initialState = loadLegacyRegisteredCats(nowIsoString()) ?? createEmptyLocalStoreState();
      await db.put(STORE_NAME, initialState, STATE_KEY);
      return initialState;
    } catch {
      resetIndexedDbConnection();
      return loadFallbackState();
    }
  }

  async function saveState(state: LocalStoreState): Promise<void> {
    const normalizedState = normalizeLocalStoreState(state);
    const db = await openLocalStoreDbOrNull();
    if (db === null) {
      saveFallbackState(normalizedState);
      return;
    }
    try {
      await db.put(STORE_NAME, normalizedState, STATE_KEY);
    } catch {
      resetIndexedDbConnection();
      saveFallbackState(normalizedState);
    }
  }

  return {
    loadState,
    saveState,
    async updateState(updater) {
      const currentState = await loadState();
      const nextState = normalizeLocalStoreState(updater(currentState));
      await saveState(nextState);
      return nextState;
    },
    async exportJson() {
      return exportLocalStoreState(await loadState());
    },
    async importJson(raw: string) {
      const importedState = importLocalStoreState(raw);
      if (importedState === null) return null;
      await saveState(importedState);
      return importedState;
    },
  };
}

export function createMemoryLocalStoreRepository(
  initialState: LocalStoreState = createEmptyLocalStoreState(),
): LocalStoreRepository {
  let state = normalizeLocalStoreState(initialState);
  return {
    async loadState() {
      return state;
    },
    async saveState(nextState) {
      state = normalizeLocalStoreState(nextState);
    },
    async updateState(updater) {
      state = normalizeLocalStoreState(updater(state));
      return state;
    },
    async exportJson() {
      return exportLocalStoreState(state);
    },
    async importJson(raw) {
      const importedState = importLocalStoreState(raw);
      if (importedState === null) return null;
      state = importedState;
      return state;
    },
  };
}

/** Target Coat画面が登録猫だけを扱うためのRepository抽象。 */
export type RegisteredCatRepository = {
  load: () => Promise<RegisteredCat[]>;
  save: (cats: RegisteredCat[]) => Promise<void>;
};

export function createRegisteredCatRepository(
  localStore: LocalStoreRepository = createLocalStoreRepository(),
): RegisteredCatRepository {
  return {
    async load() {
      try {
        return activeRegisteredCats(await localStore.loadState());
      } catch {
        return [];
      }
    },
    async save(cats) {
      try {
        await localStore.updateState((state) => ({
          ...state,
          registeredCats: mergeRegisteredCatsForStorage(
            cats,
            state.registeredCats,
            nowIsoString(),
          ),
        }));
      } catch {
        // 保存できない環境でも、呼び出し側の画面状態は維持する。
      }
    },
  };
}
