import { describe, expect, it } from "vitest";

import { describeError } from "./api";

describe("describeError", () => {
  describe("文字列 detail (自前 BreedingCalculationError)", () => {
    it("Unsupported color の長い一覧を簡潔な日本語へ整形する", () => {
      const detail = "Unsupported color 'Foo'. Supported colors: Black, Blue, ...";
      expect(describeError(detail)).toBe(
        "「Foo」は対応していない毛色です。候補から選んでください。",
      );
    });

    it("性別不適合カラーをオス親向けに整形する", () => {
      const detail = "Color 'Blue Cream' is not valid for a male.";
      expect(describeError(detail)).toBe(
        "「Blue Cream」はオス親（♀限定の毛色）には指定できない毛色です。",
      );
    });

    it("性別不適合カラーをメス親向けに整形する", () => {
      const detail = "Color 'Foo' is not valid for a female.";
      expect(describeError(detail)).toBe("「Foo」はメス親には指定できない毛色です。");
    });

    it("既に日本語のメッセージはそのまま返す", () => {
      const detail = "「Foo」は通常の計算では入力できない色区分です。";
      expect(describeError(detail)).toBe(detail);
    });
  });

  describe("配列 detail (pydantic 検証エラー)", () => {
    it("日本語の検証メッセージ (入力上限超過) を表示し Value error 接頭辞を除去する", () => {
      const detail = [{ msg: "Value error, 登録猫は最大50頭までです。頭数を減らしてください。" }];
      expect(describeError(detail)).toBe("登録猫は最大50頭までです。頭数を減らしてください。");
    });

    it("リター子猫上限の日本語メッセージを表示する", () => {
      const detail = [{ msg: "Value error, 観察できる子猫は最大12頭までです。" }];
      expect(describeError(detail)).toBe("観察できる子猫は最大12頭までです。");
    });

    it("英語のみの検証エラーは総括文言にフォールバックする", () => {
      const detail = [{ msg: "String should have at least 1 character" }];
      expect(describeError(detail)).toBe(
        "入力内容に誤りがあります。毛色が正しく入力されているか確認してください。",
      );
    });

    it("英語と日本語が混在する場合は最初の日本語メッセージを採用する", () => {
      const detail = [
        { msg: "Field required" },
        { msg: "Value error, 登録猫は最大50頭までです。頭数を減らしてください。" },
      ];
      expect(describeError(detail)).toBe("登録猫は最大50頭までです。頭数を減らしてください。");
    });
  });
});
