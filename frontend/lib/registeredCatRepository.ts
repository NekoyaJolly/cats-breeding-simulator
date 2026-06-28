import { z } from "zod";
import { registeredCatSchema, type RegisteredCat } from "./schema";

// 登録猫保存の抽象。将来DB/API保存へ移す場合もUI側の呼び出し口を変えずに済ませる。
export type RegisteredCatRepository = {
  load: () => RegisteredCat[];
  save: (cats: RegisteredCat[]) => void;
};

const REGISTERED_CATS_KEY = "cbs:registeredCats";
const registeredCatsSchema = z.array(registeredCatSchema);

export function createLocalRegisteredCatRepository(): RegisteredCatRepository {
  return {
    load() {
      try {
        const raw = window.localStorage.getItem(REGISTERED_CATS_KEY);
        if (raw === null) return [];
        const parsed = registeredCatsSchema.safeParse(JSON.parse(raw));
        return parsed.success ? parsed.data : [];
      } catch {
        return [];
      }
    },
    save(cats: RegisteredCat[]) {
      try {
        window.localStorage.setItem(REGISTERED_CATS_KEY, JSON.stringify(cats));
      } catch {
        // 保存できない環境でも、呼び出し側の画面状態は維持する。
      }
    },
  };
}
