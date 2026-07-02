import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { OnboardingGuide } from "./OnboardingGuide";

describe("OnboardingGuide", () => {
  it("ヘルプを開くとモーダル内の閉じるボタンへフォーカスし、閉じる操作ができる", async () => {
    const user = userEvent.setup();
    render(<OnboardingGuide activeView="parent" language="ja" />);

    expect(
      screen.getByText("父母の毛色から子猫の出現割合を計算します。"),
    ).toBeInTheDocument();
    const helpButton = screen.getByRole("button", { name: "ヘルプ" });
    await user.click(helpButton);

    expect(
      screen.getByRole("dialog", { name: "使い方のガイド" }),
    ).toBeInTheDocument();
    const closeButton = screen.getByRole("button", { name: "閉じる" });
    await waitFor(() => expect(closeButton).toHaveFocus());

    await user.tab();
    expect(closeButton).toHaveFocus();

    await user.click(closeButton);
    expect(screen.queryByRole("dialog", { name: "使い方のガイド" })).toBeNull();
    expect(helpButton).toHaveFocus();
  });

  it("Escape と背景クリックでヘルプを閉じる", async () => {
    const user = userEvent.setup();
    render(<OnboardingGuide activeView="kitten" language="ja" />);

    await user.click(screen.getByRole("button", { name: "ヘルプ" }));
    expect(
      screen.getByRole("dialog", { name: "使い方のガイド" }),
    ).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "使い方のガイド" })).toBeNull();

    await user.click(screen.getByRole("button", { name: "ヘルプ" }));
    await user.click(screen.getByTestId("onboarding-help-overlay"));
    expect(screen.queryByRole("dialog", { name: "使い方のガイド" })).toBeNull();
  });
});
