import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LocusChip } from "./LocusChip";

// FE-1 スモーク兼用テスト: jsdom + React Testing Library + jest-dom + user-event の
// 一連が動作することを、実コンポーネント LocusChip の挙動で確認する。
describe("LocusChip", () => {
  it("既知の座位はボタンとして描画され、クリックで解説が開く (aria-expanded)", async () => {
    render(<LocusChip locus="A" />);

    const button = screen.getByRole("button");
    // 初期状態は閉じている。
    expect(button).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(button);

    // クリックで開く (閉じるは外側クリック/Escape に委譲しているため、ここでは開のみ検証)。
    expect(button).toHaveAttribute("aria-expanded", "true");
  });

  it("解説が未登録の座位はボタンにせずプレーンテキストで出す", () => {
    render(<LocusChip locus="ZZ-未登録" />);

    // ボタン化されない (解説ポップオーバーを持たない)。
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("ZZ-未登録")).toBeInTheDocument();
  });
});
