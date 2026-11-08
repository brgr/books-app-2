import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import BookReadingCard from "./BookReadingCard.vue";
import { ReadingDatePrecision, type ReadingDateValue, ReadingShelf } from "../../../api/types";

enableAutoUnmount(afterEach);

function makeProps(
  overrides: Partial<{
    shelf: ReadingShelf | null;
    updating: boolean;
    currentPage: number | null;
    currentPercent: number | null;
    pageCount: number | null;
    startedAt: ReadingDateValue | null;
    finishedAt: ReadingDateValue | null;
    progressSaving: boolean;
  }> = {},
) {
  return {
    shelf: ReadingShelf.STARTED,
    updating: false,
    currentPage: 10,
    currentPercent: null,
    pageCount: 200,
    startedAt: null,
    finishedAt: null,
    progressSaving: false,
    ...overrides,
  };
}

describe("BookReadingCard", () => {
  it("shows current progress summary", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ currentPage: 50, pageCount: 200 }),
    });
    expect(wrapper.text()).toContain("Page 50");
    expect(wrapper.text()).toContain("of 200");
  });

  it('shows "No progress yet" when current page is null', () => {
    const wrapper = mount(BookReadingCard, { props: makeProps({ currentPage: null }) });
    expect(wrapper.text()).toContain("No progress yet");
  });

  it("shows the percentage summary when progress was last set as a percent", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ currentPage: null, currentPercent: 42 }),
    });
    expect(wrapper.text()).toContain("42%");
    expect(wrapper.text()).not.toContain("Page");
  });

  it("shows the page alongside a percentage derived from page count", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ currentPage: 50, pageCount: 200 }),
    });
    expect(wrapper.text()).toContain("Page 50 of 200");
    expect(wrapper.text()).toContain("25%");
  });

  it("omits the percentage when page count is missing", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ currentPage: 50, pageCount: null }),
    });
    expect(wrapper.text()).toContain("Page 50");
    expect(wrapper.text()).not.toContain("%");
  });

  it("hides progress input until Update is clicked", async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(true);
  });

  it('emits "update-progress" with the current page when Save is clicked', async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="save-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ unit: "page", value: 10 });
  });

  it.each([
    { currentPage: 10, currentPercent: null, unit: "page", value: "10", expected: { unit: "page", value: 10 } },
    {
      currentPage: null,
      currentPercent: 3.5,
      unit: "percent",
      value: "3.5",
      expected: { unit: "percent", value: 3.5 },
    },
    { currentPage: 0, currentPercent: null, unit: "page", value: "0", expected: { unit: "page", value: 0 } },
    { currentPage: null, currentPercent: 0, unit: "percent", value: "0", expected: { unit: "percent", value: 0 } },
  ])("edits the recorded $unit value $value", async ({ currentPage, currentPercent, unit, value, expected }) => {
    const wrapper = mount(BookReadingCard, { props: makeProps({ currentPage, currentPercent }) });
    const otherUnit = unit === "page" ? "percent" : "page";

    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.get(`[data-test="unit-${unit}"]`).classes()).toContain("active");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
    await wrapper.get(`[data-test="unit-${otherUnit}"]`).trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("");
    await wrapper.get(`[data-test="unit-${unit}"]`).trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.emitted("update-progress")).toEqual([[expected]]);
  });

  it("forwards the saving state and closes the editor when saved progress changes", async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    await wrapper.get('[data-test="progress-input"]').setValue("42");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ unit: "page", value: 42 });
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(true);
    await wrapper.setProps({ progressSaving: true });
    expect(wrapper.get('[data-test="save-progress"]').text()).toBe("Saving…");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.disabled).toBe(true);

    await wrapper.setProps({ currentPage: 42, progressSaving: false });
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Page 42 of 200");
  });

  it("Cancel exits edit mode without emitting", async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="progress-input"]').setValue("99");
    await wrapper.find('[data-test="cancel-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")).toBeFalsy();
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);

    await wrapper.get('[data-test="edit-progress"]').trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("10");
  });

  it('re-emits "change" from the shelf button', () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    wrapper.findComponent({ name: "BookShelfButton" }).vm.$emit("change", ReadingShelf.FINISHED);
    expect(wrapper.emitted("change")?.[0]?.[0]).toBe(ReadingShelf.FINISHED);
  });

  it('shows a "Finish" action while reading', () => {
    const wrapper = mount(BookReadingCard, { props: makeProps({ shelf: ReadingShelf.STARTED }) });
    expect(wrapper.find('[data-test="shelf-button"]').text()).toBe("Finish");
  });

  it("shows started and finished dates when provided", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({
        startedAt: { value: "2026-01-02", precision: ReadingDatePrecision.DAY },
        finishedAt: { value: "2026-02-03", precision: ReadingDatePrecision.DAY },
      }),
    });
    expect(wrapper.text()).toContain("since");
    expect(wrapper.find(".dates").exists()).toBe(true);
    expect(wrapper.text()).toContain("Finished");
  });

  it("hides the dates block when no dates are set", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ startedAt: null, finishedAt: null }),
    });
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
      const wrapper = mount(BookReadingCard, {
        props: makeProps({
          startedAt: { value: "2026-01-01T12:00:00Z", precision: ReadingDatePrecision.MONTH },
        }),
      });
      expect(wrapper.text()).toContain("Jan 2026");
      expect(wrapper.text()).not.toContain("Jan 1, 2026");
    } finally {
      dateTimeFormat.mockRestore();
    }
  });
});
