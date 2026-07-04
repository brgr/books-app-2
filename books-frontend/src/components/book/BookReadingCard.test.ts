import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookReadingCard from "./BookReadingCard.vue";
import { ReadingStatus } from "../../api/types";

function makeProps(
  overrides: Partial<{
    status: ReadingStatus | null;
    updating: boolean;
    currentPage: number | null;
    currentPercent: number | null;
    pageCount: number | null;
    startedAt: string | null;
    finishedAt: string | null;
    progressSaving: boolean;
  }> = {},
) {
  return {
    status: ReadingStatus.STARTED,
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
    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ page: 10 });
  });

  it('emits "update-progress" with new page after editing the input', async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="progress-input"]').setValue("42");
    await wrapper.find('[data-test="save-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ page: 42 });
  });

  it("emits a percent payload when the percent unit is selected", async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="unit-percent"]').trigger("click");
    await wrapper.find('[data-test="progress-input"]').setValue("75");
    await wrapper.find('[data-test="save-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ percent: 75 });
  });

  it("defaults the editor to the percent unit when progress was last a percent", async () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ currentPage: null, currentPercent: 30 }),
    });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    expect((wrapper.find('[data-test="progress-input"]').element as HTMLInputElement).value).toBe("30");
    await wrapper.find('[data-test="save-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")?.[0]?.[0]).toEqual({ percent: 30 });
  });

  it("Cancel exits edit mode without emitting", async () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    await wrapper.find('[data-test="edit-progress"]').trigger("click");
    await wrapper.find('[data-test="progress-input"]').setValue("99");
    await wrapper.find('[data-test="cancel-progress"]').trigger("click");
    expect(wrapper.emitted("update-progress")).toBeFalsy();
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false);
  });

  it('re-emits "change" from the status button', () => {
    const wrapper = mount(BookReadingCard, { props: makeProps() });
    wrapper.findComponent({ name: "BookStatusButton" }).vm.$emit("change", ReadingStatus.FINISHED);
    expect(wrapper.emitted("change")?.[0]?.[0]).toBe(ReadingStatus.FINISHED);
  });

  it('shows a "Finish" action while reading', () => {
    const wrapper = mount(BookReadingCard, { props: makeProps({ status: ReadingStatus.STARTED }) });
    expect(wrapper.find('[data-test="status-button"]').text()).toBe("Finish");
  });

  it("shows started and finished dates when provided", () => {
    const wrapper = mount(BookReadingCard, {
      props: makeProps({ startedAt: "2026-01-02", finishedAt: "2026-02-03" }),
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
});
