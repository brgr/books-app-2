import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { VueQueryPlugin } from "@tanstack/vue-query";
import BookReadingCard from "./BookReadingCard.vue";
import type { ReadingProgress } from "./types";
import { addBookProgress } from "../../../api/books";
import { ReadingDatePrecision, type ReadingDateValue, ReadingShelf, type UserBook } from "../../../api/types";
import { queryClient } from "../../../query/client";

enableAutoUnmount(afterEach);

vi.mock("../../../api/books", () => ({
  addBookProgress: vi.fn(),
}));

const userBook: UserBook = {
  id: 1,
  user_id: 1,
  book_id: 1,
  shelf: ReadingShelf.STARTED,
  started_at: null,
  finished_at: null,
  notes: null,
  progress: { unit: "page", value: 42 },
  rating: null,
};

function makeProps(
  overrides: Partial<{
    bookId: number;
    shelf: ReadingShelf;
    progress: ReadingProgress;
    pageCount: number | null;
    startedAt: ReadingDateValue | null;
    finishedAt: ReadingDateValue | null;
  }> = {},
) {
  return {
    bookId: 1,
    shelf: ReadingShelf.STARTED,
    progress: { unit: "page", value: 10 } satisfies ReadingProgress,
    pageCount: 200,
    startedAt: null,
    finishedAt: null,
    ...overrides,
  };
}

function mountCard(overrides: Parameters<typeof makeProps>[0] = {}) {
  return mount(BookReadingCard, {
    props: makeProps(overrides),
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });
}

describe("BookReadingCard", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    queryClient.clear();
  });

  it("shows current progress summary", () => {
    const wrapper = mountCard({ progress: { unit: "page", value: 50 }, pageCount: 200 });
    expect(wrapper.text()).toContain("Page 50");
    expect(wrapper.text()).toContain("of 200");
  });

  it("shows zero progress for a newly started book", () => {
    const wrapper = mountCard({ progress: { unit: "page", value: 0 } });
    expect(wrapper.text()).toContain("Page 0 of 200");
    expect(wrapper.text()).toContain("0%");
  });

  it("shows the percentage summary when progress was last set as a percent", () => {
    const wrapper = mountCard({ progress: { unit: "percent", value: 42 } });
    expect(wrapper.text()).toContain("42%");
    expect(wrapper.text()).not.toContain("Page");
  });

  it("shows the page alongside a percentage derived from page count", () => {
    const wrapper = mountCard({ progress: { unit: "page", value: 50 }, pageCount: 200 });
    expect(wrapper.text()).toContain("Page 50 of 200");
    expect(wrapper.text()).toContain("25%");
  });

  it("omits the percentage when page count is missing", () => {
    const wrapper = mountCard({ progress: { unit: "page", value: 50 }, pageCount: null });
    expect(wrapper.text()).toContain("Page 50");
    expect(wrapper.text()).not.toContain("%");
  });

  it("hides progress input until Update is clicked", async () => {
    const wrapper = mountCard();
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(true);
  });

  it.each<ReadingProgress>([
    { unit: "page", value: 10 },
    { unit: "percent", value: 3.5 },
    { unit: "page", value: 0 },
    { unit: "percent", value: 0 },
  ])("edits the recorded $unit value $value", async (progress) => {
    const wrapper = mountCard({ progress });
    const { unit } = progress;
    const value = String(progress.value);
    const otherUnit = unit === "page" ? "percent" : "page";

    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.get(`[data-test="unit-${unit}"]`).classes()).toContain("active");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
    await wrapper.get(`[data-test="unit-${otherUnit}"]`).trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("");
    await wrapper.get(`[data-test="unit-${unit}"]`).trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(vi.mocked(addBookProgress).mock.calls).toEqual([[1, progress]]);
  });

  it("closes the editor once saved, even when the progress didn't change", async () => {
    vi.mocked(addBookProgress).mockResolvedValue(userBook);
    const wrapper = mountCard();
    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    await vi.waitFor(() => expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false));
  });

  it("preserves the draft when a refresh returns the same progress", async () => {
    const wrapper = mountCard();
    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    await wrapper.get('[data-test="progress-input"]').setValue("42");

    await wrapper.setProps({ progress: { unit: "page", value: 10 } });

    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("42");
  });

  it("Cancel exits edit mode without saving", async () => {
    const wrapper = mountCard();
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="progress-input"]').setValue("99");
    await wrapper.find('[data-test="cancel-progress"]').trigger("click");
    expect(addBookProgress).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);

    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("10");
  });

  it('shows a "Finish" action while reading', () => {
    const wrapper = mountCard({ shelf: ReadingShelf.STARTED });
    expect(wrapper.find('[data-test="shelf-button"]').text()).toBe("Finish");
  });

  it("shows started and finished dates when provided", () => {
    const wrapper = mountCard({
      startedAt: { value: "2026-01-02", precision: ReadingDatePrecision.DAY },
      finishedAt: { value: "2026-02-03", precision: ReadingDatePrecision.DAY },
    });
    expect(wrapper.text()).toContain("since");
    expect(wrapper.find(".dates").exists()).toBe(true);
    expect(wrapper.text()).toContain("Finished");
  });

  it("hides the dates block when no dates are set", () => {
    const wrapper = mountCard({ startedAt: null, finishedAt: null });
    expect(wrapper.find(".dates").exists()).toBe(false);
  });

  it("shows an imprecise reading date without inventing a day", () => {
    // First, we need to make sure the locale is set; otherwise this test would fail in environments with
    // different default locales.
    const NativeDateTimeFormat = Intl.DateTimeFormat;
    const dateTimeFormat = vi.spyOn(Intl, "DateTimeFormat").mockImplementation(function (locales, options) {
      return new NativeDateTimeFormat(locales ?? "en-US", options);
    } as typeof Intl.DateTimeFormat);

    try {
      const wrapper = mountCard({
        startedAt: { value: "2026-01-01T12:00:00Z", precision: ReadingDatePrecision.MONTH },
      });
      expect(wrapper.text()).toContain("Jan 2026");
      expect(wrapper.text()).not.toContain("Jan 1, 2026");
    } finally {
      dateTimeFormat.mockRestore();
    }
  });
});
