import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Config } from "driver.js";
import { APP_TOUR_COMPLETED_KEY, AppTour } from "./AppTour";

const driverMock = vi.hoisted(() => ({
  create: vi.fn(),
  destroy: vi.fn(),
  drive: vi.fn(),
  moveNext: vi.fn(),
}));

vi.mock("driver.js", () => ({
  driver: driverMock.create,
}));

describe("AppTour", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.useRealTimers();
    vi.clearAllMocks();
    driverMock.create.mockReturnValue({
      destroy: driverMock.destroy,
      drive: driverMock.drive,
      moveNext: driverMock.moveNext,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("初回表示では自動でツアーを開始する", () => {
    vi.useFakeTimers();
    const onViewChange = vi.fn();

    render(
      <AppTour
        language="ja"
        languageReady
        activeView="target"
        onViewChange={onViewChange}
      />,
    );

    act(() => {
      vi.advanceTimersByTime(900);
    });

    expect(onViewChange).toHaveBeenCalledWith("parent");
    expect(driverMock.create).toHaveBeenCalledTimes(1);
    expect(driverMock.drive).toHaveBeenCalledTimes(1);
    const [config] = driverMock.create.mock.calls[0] as [Config];
    const closeButton = document.createElement("button");
    config.onPopoverRender?.(
      {
        wrapper: document.createElement("div"),
        arrow: document.createElement("div"),
        title: document.createElement("div"),
        description: document.createElement("div"),
        footer: document.createElement("div"),
        progress: document.createElement("div"),
        previousButton: document.createElement("button"),
        nextButton: document.createElement("button"),
        closeButton,
        footerButtons: document.createElement("div"),
      },
      {
        config,
        state: {},
        driver: driverMock.create.mock.results[0].value,
      },
    );
    expect(closeButton).toHaveTextContent("スキップ");
  });

  it("完了済みなら初回の自動開始は行わない", () => {
    vi.useFakeTimers();
    window.localStorage.setItem(APP_TOUR_COMPLETED_KEY, "true");

    render(
      <AppTour
        language="ja"
        languageReady
        activeView="parent"
        onViewChange={vi.fn()}
      />,
    );

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(driverMock.create).not.toHaveBeenCalled();
    expect(driverMock.drive).not.toHaveBeenCalled();
  });

  it("使い方ボタンから手動でツアーを再表示できる", () => {
    vi.useFakeTimers();
    const onViewChange = vi.fn();

    render(
      <AppTour
        language="ja"
        languageReady={false}
        activeView="kitten"
        onViewChange={onViewChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "使い方" }));
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(onViewChange).toHaveBeenCalledWith("kitten");
    expect(driverMock.create).toHaveBeenCalledTimes(1);
    expect(driverMock.drive).toHaveBeenCalledTimes(1);
    const [config] = driverMock.create.mock.calls[0] as [Config];
    expect(config.steps?.[0]?.element).toBe("[data-tour='kitten-panel']");
    const closeButton = document.createElement("button");
    config.onPopoverRender?.(
      {
        wrapper: document.createElement("div"),
        arrow: document.createElement("div"),
        title: document.createElement("div"),
        description: document.createElement("div"),
        footer: document.createElement("div"),
        progress: document.createElement("div"),
        previousButton: document.createElement("button"),
        nextButton: document.createElement("button"),
        closeButton,
        footerButtons: document.createElement("div"),
      },
      {
        config,
        state: {},
        driver: driverMock.create.mock.results[0].value,
      },
    );
    expect(closeButton).toHaveTextContent("閉じる");
  });
});
