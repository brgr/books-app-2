import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { VueQueryPlugin } from "@tanstack/vue-query";
import BookShelfButton from "./BookShelfButton.vue";
import { setShelf } from "../../../api/books";
import { ReadingDatePrecision, ReadingShelf } from "../../../api/types";
import { queryClient } from "../../../query/client";
import { localDayValue } from "../../../utils/date";

enableAutoUnmount(afterEach);

vi.mock("../../../api/books", () => ({
  setShelf: vi.fn(),
}));

function mountButton(shelf: ReadingShelf = ReadingShelf.WANT_TO_READ) {
  return mount(BookShelfButton, {
    props: { bookId: 1, shelf },
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });
}

const today = () => ({ value: localDayValue(new Date()), precision: ReadingDatePrecision.DAY });

describe("BookShelfButton", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    queryClient.clear();
  });

  it("offers pausing only while a book is currently being read", async () => {
    const started = mountButton(ReadingShelf.STARTED);
    await started.find('[data-test="shelf-caret"]').trigger("click");
    await started.find('[data-test="pause-reading"]').trigger("click");

    expect(setShelf).toHaveBeenCalledWith(1, { shelf: ReadingShelf.PAUSED, reading_date: today() });

    const notStarted = mountButton();
    await notStarted.find('[data-test="shelf-caret"]').trigger("click");
    expect(notStarted.find('[data-test="pause-reading"]').exists()).toBe(false);
    expect(notStarted.find('[data-test="abandon-reading"]').exists()).toBe(false);
  });

  it("resumes a paused book today", async () => {
    const wrapper = mountButton(ReadingShelf.PAUSED);

    expect(wrapper.find('[data-test="shelf-button"]').text()).toBe("Resume Reading");
    await wrapper.find('[data-test="shelf-button"]').trigger("click");
    expect(setShelf).toHaveBeenCalledWith(1, { shelf: ReadingShelf.STARTED, reading_date: today() });
  });

  it.each([ReadingShelf.STARTED, ReadingShelf.PAUSED])("allows abandoning a %s book", async (shelf) => {
    const wrapper = mountButton(shelf);

    expect(wrapper.find('[data-test="shelf-caret"]').attributes("aria-label")).toBe("More reading actions");
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="abandon-reading"]').trigger("click");

    expect(setShelf).toHaveBeenCalledWith(1, { shelf: ReadingShelf.ABANDONED, reading_date: today() });
  });

  it("sends an exact-day reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-input"]').setValue("2026-04-15");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(setShelf).toHaveBeenCalledWith(1, {
      shelf: ReadingShelf.STARTED,
      reading_date: { value: "2026-04-15T12:00:00.000Z", precision: ReadingDatePrecision.DAY },
    });
  });

  it("sends a month-precision reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.MONTH);
    await wrapper.find('[data-test="shelf-month-input"]').setValue("04");
    await wrapper.find('[data-test="shelf-month-year-input"]').setValue("2026");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(setShelf).toHaveBeenCalledWith(1, {
      shelf: ReadingShelf.STARTED,
      reading_date: { value: "2026-04-01T12:00:00.000Z", precision: ReadingDatePrecision.MONTH },
    });
  });

  it("sends a year-precision reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.YEAR);
    await wrapper.find('[data-test="shelf-date-input"]').setValue("2025");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(setShelf).toHaveBeenCalledWith(1, {
      shelf: ReadingShelf.STARTED,
      reading_date: { value: "2025-01-01T12:00:00.000Z", precision: ReadingDatePrecision.YEAR },
    });
  });

  it.each([
    ["a fractional", "2025.5", "Enter a whole year."],
    ["a future", String(new Date().getUTCFullYear() + 1), `Enter a year from 1900 to ${new Date().getUTCFullYear()}.`],
  ])("explains why it cannot confirm %s year", async (_description, year, message) => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.YEAR);
    await wrapper.find('[data-test="shelf-date-input"]').setValue(year);

    const confirmButton = wrapper.find<HTMLButtonElement>('[data-test="shelf-date-confirm"]');
    expect(confirmButton.element.disabled).toBe(true);
    expect(wrapper.find('[data-test="shelf-date-error"]').text()).toBe(message);
    await confirmButton.trigger("click");
    expect(setShelf).not.toHaveBeenCalled();
  });

  it("sends an unknown reading date without a calendar value", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.UNKNOWN);

    expect(wrapper.find('[data-test="shelf-date-input"]').exists()).toBe(false);
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");
    expect(setShelf).toHaveBeenCalledWith(1, {
      shelf: ReadingShelf.STARTED,
      reading_date: { value: null, precision: ReadingDatePrecision.UNKNOWN },
    });
  });
});
