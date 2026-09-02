import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import BookShelfButton from "./BookShelfButton.vue";
import { ReadingDatePrecision, ReadingShelf } from "../../../api/types";

function mountButton() {
  return mount(BookShelfButton, {
    props: { shelf: ReadingShelf.WANT_TO_READ, updating: false },
  });
}

function mountStartedButton() {
  return mount(BookShelfButton, {
    props: { shelf: ReadingShelf.STARTED, updating: false },
  });
}

describe("BookShelfButton", () => {
  it("offers pausing only while a book is currently being read", async () => {
    const started = mountStartedButton();
    await started.find('[data-test="shelf-caret"]').trigger("click");
    await started.find('[data-test="pause-reading"]').trigger("click");

    expect(started.emitted("change")?.[0]).toEqual([ReadingShelf.PAUSED]);

    const notStarted = mountButton();
    await notStarted.find('[data-test="shelf-caret"]').trigger("click");
    expect(notStarted.find('[data-test="pause-reading"]').exists()).toBe(false);
  });

  it("resumes a paused book", async () => {
    const wrapper = mount(BookShelfButton, {
      props: { shelf: ReadingShelf.PAUSED, updating: false },
    });

    expect(wrapper.find('[data-test="shelf-button"]').text()).toBe("Resume Reading");
    await wrapper.find('[data-test="shelf-button"]').trigger("click");
    expect(wrapper.emitted("change")?.[0]).toEqual([ReadingShelf.STARTED]);
  });

  it("sends an exact-day reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-input"]').setValue("2026-04-15");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(wrapper.emitted("change")?.[0]).toEqual([
      ReadingShelf.STARTED,
      { value: "2026-04-15T12:00:00.000Z", precision: ReadingDatePrecision.DAY },
    ]);
  });

  it("sends a month-precision reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.MONTH);
    await wrapper.find('[data-test="shelf-month-input"]').setValue("04");
    await wrapper.find('[data-test="shelf-month-year-input"]').setValue("2026");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(wrapper.emitted("change")?.[0]).toEqual([
      ReadingShelf.STARTED,
      { value: "2026-04-01T12:00:00.000Z", precision: ReadingDatePrecision.MONTH },
    ]);
  });

  it("sends a year-precision reading date", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.YEAR);
    await wrapper.find('[data-test="shelf-date-input"]').setValue("2025");
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");

    expect(wrapper.emitted("change")?.[0]).toEqual([
      ReadingShelf.STARTED,
      { value: "2025-01-01T12:00:00.000Z", precision: ReadingDatePrecision.YEAR },
    ]);
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
    expect(wrapper.emitted("change")).toBeUndefined();
  });

  it("sends an unknown reading date without a calendar value", async () => {
    const wrapper = mountButton();
    await wrapper.find('[data-test="shelf-caret"]').trigger("click");
    await wrapper.find('[data-test="shelf-date-precision"]').setValue(ReadingDatePrecision.UNKNOWN);

    expect(wrapper.find('[data-test="shelf-date-input"]').exists()).toBe(false);
    await wrapper.find('[data-test="shelf-date-confirm"]').trigger("click");
    expect(wrapper.emitted("change")?.[0]).toEqual([
      ReadingShelf.STARTED,
      { value: null, precision: ReadingDatePrecision.UNKNOWN },
    ]);
  });
});
