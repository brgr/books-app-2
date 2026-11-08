import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import BookProgressEditor from "./BookProgressEditor.vue";
import type { ReadingProgress } from "./types";

enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());

describe("BookProgressEditor", () => {
  it.each<{ progress: ReadingProgress | null; unit: string; value: string }>([
    { progress: { page: 10 }, unit: "page", value: "10" },
    { progress: { percent: 30 }, unit: "percent", value: "30" },
    { progress: { page: 0 }, unit: "page", value: "0" },
    { progress: { percent: 0 }, unit: "percent", value: "0" },
    { progress: null, unit: "page", value: "" },
  ])("initializes $progress with the $unit unit", ({ progress, unit, value }) => {
    const wrapper = mount(BookProgressEditor, { props: { progress } });

    expect(wrapper.get(`[data-test="unit-${unit}"]`).classes()).toContain("active");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
  });

  it("emits the edited page on save", async () => {
    const wrapper = mount(BookProgressEditor, { props: { progress: { page: 10 } } });

    await wrapper.get('[data-test="progress-input"]').setValue("42");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.emitted("save")).toEqual([[{ page: 42 }]]);
  });

  it("emits a fractional percentage after switching units", async () => {
    const wrapper = mount(BookProgressEditor, { props: { progress: { page: 10 }, pageCount: 200 } });

    expect(wrapper.get(".progress-suffix").text()).toBe("of 200");
    await wrapper.get('[data-test="unit-percent"]').trigger("click");
    expect(wrapper.get(".progress-suffix").text()).toBe("%");
    expect(wrapper.get('[data-test="progress-input"]').attributes("aria-label")).toBe("Percentage read");
    await wrapper.get('[data-test="progress-input"]').setValue("75.5");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.emitted("save")).toEqual([[{ percent: 75.5 }]]);
  });

  it("restores the recorded value when switching back to its unit", async () => {
    const wrapper = mount(BookProgressEditor, { props: { progress: { percent: 30 } } });

    await wrapper.get('[data-test="unit-page"]').trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("");
    await wrapper.get('[data-test="unit-percent"]').trigger("click");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.emitted("save")).toEqual([[{ percent: 30 }]]);
  });

  it("emits cancel without saving the draft", async () => {
    const wrapper = mount(BookProgressEditor, { props: { progress: { page: 10 } } });

    await wrapper.get('[data-test="progress-input"]').setValue("99");
    await wrapper.get('[data-test="cancel-progress"]').trigger("click");

    expect(wrapper.emitted("cancel")).toEqual([[]]);
    expect(wrapper.emitted("save")).toBeUndefined();
  });

  it.each([
    { unit: "page", value: "", message: "Please enter a page number." },
    { unit: "page", value: "-1", message: "Please enter a valid page number." },
    { unit: "percent", value: "", message: "Please enter a percentage." },
    { unit: "percent", value: "-1", message: "Please enter a percentage between 0 and 100." },
    { unit: "percent", value: "101", message: "Please enter a percentage between 0 and 100." },
  ])("rejects '$value' in $unit mode", async ({ unit, value, message }) => {
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const wrapper = mount(BookProgressEditor, { props: { progress: null } });

    await wrapper.get(`[data-test="unit-${unit}"]`).trigger("click");
    await wrapper.get('[data-test="progress-input"]').setValue(value);
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(alert).toHaveBeenCalledWith(message);
    expect(wrapper.emitted("save")).toBeUndefined();
  });

  it("disables controls while saving and preserves the draft when saving ends", async () => {
    const wrapper = mount(BookProgressEditor, { props: { progress: { page: 10 } } });
    await wrapper.get('[data-test="progress-input"]').setValue("42");
    await wrapper.setProps({ isCurrentlySaving: true });

    expect(wrapper.get('[data-test="save-progress"]').text()).toBe("Saving…");
    for (const control of wrapper.findAll<HTMLInputElement | HTMLButtonElement>("input, button")) {
      expect(control.element.disabled).toBe(true);
    }
    await wrapper.get('[data-test="save-progress"]').trigger("click");
    await wrapper.get('[data-test="cancel-progress"]').trigger("click");
    expect(wrapper.emitted("save")).toBeUndefined();
    expect(wrapper.emitted("cancel")).toBeUndefined();

    await wrapper.setProps({ isCurrentlySaving: false });
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("42");
    await wrapper.get('[data-test="save-progress"]').trigger("click");
    expect(wrapper.emitted("save")).toEqual([[{ page: 42 }]]);
  });
});
