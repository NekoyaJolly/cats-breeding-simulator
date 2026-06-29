import { describe, expect, it } from "vitest";

import { BREED_READING_JA } from "./breedReadingJa";

describe("BREED_READING_JA", () => {
  it("代表的な猫種の読みを持つ", () => {
    expect(BREED_READING_JA["Munchkin"]).toBe("マンチカン");
    expect(BREED_READING_JA["Siamese"]).toBe("シャム");
    expect(BREED_READING_JA["Maine Coon"]).toBe("メインクーン");
  });

  it("全エントリの値はカタカナ表記 (長音符・括弧を許容) で非空", () => {
    for (const reading of Object.values(BREED_READING_JA)) {
      expect(reading.length).toBeGreaterThan(0);
      expect(reading).toMatch(/^[゠-ヿ（）]+$/);
    }
  });
});
