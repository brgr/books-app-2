import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { VueQueryPlugin } from "@tanstack/vue-query";
import BookProgressEditor from "./BookProgressEditor.vue";
import type { ReadingProgress } from "./types";
import { addBookProgress } from "../../../api/books";
import { queryClient } from "../../../query/client";

enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());

vi.mock("../../../api/books", () => ({
  addBookProgress: vi.fn(),
}));

function mountEditor(props: { progress: ReadingProgress; pageCount?: number }) {
  return mount(BookProgressEditor, {
    props: { bookId: 1, ...props },
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  });
}

describe("BookProgressEditor", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    queryClient.clear();
  });

  it("requires a known unit and a value in its type", () => {
    expectTypeOf<{ unit: "page"; value: number }>().toExtend<ReadingProgress>();
    expectTypeOf<{ unit: "percent"; value: number }>().toExtend<ReadingProgress>();
    expectTypeOf<{ unit: "unknown"; value: number }>().not.toExtend<ReadingProgress>();
    expectTypeOf<{ unit: "page" }>().not.toExtend<ReadingProgress>();
  });

  it.each<{ progress: ReadingProgress; unit: string; value: string }>([
    { progress: { unit: "page", value: 10 }, unit: "page", value: "10" },
    { progress: { unit: "percent", value: 30 }, unit: "percent", value: "30" },
    { progress: { unit: "page", value: 0 }, unit: "page", value: "0" },
    { progress: { unit: "percent", value: 0 }, unit: "percent", value: "0" },
  ])("initializes $progress with the $unit unit", ({ progress, unit, value }) => {
    const wrapper = mountEditor({ progress });

    expect(wrapper.get(`[data-test="unit-${unit}"]`).classes()).toContain("active");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe(value);
  });

  it("saves the edited page and emits saved", async () => {
    const wrapper = mountEditor({ progress: { unit: "page", value: 10 } });

    await wrapper.get('[data-test="progress-input"]').setValue("42");
    await wrapper.get('[data-test="save-progress"]').trigger("click");
    await flushPromises();

    expect(addBookProgress).toHaveBeenCalledWith(1, { unit: "page", value: 42 });
    expect(wrapper.emitted("saved")).toEqual([[]]);
  });

  it("saves a fractional percentage after switching units", async () => {
    const wrapper = mountEditor({ progress: { unit: "page", value: 10 }, pageCount: 200 });

    expect(wrapper.get(".progress-suffix").text()).toBe("of 200");
    await wrapper.get('[data-test="unit-percent"]').trigger("click");
    expect(wrapper.get(".progress-suffix").text()).toBe("%");
    expect(wrapper.get('[data-test="progress-input"]').attributes("aria-label")).toBe("Percentage read");
    await wrapper.get('[data-test="progress-input"]').setValue("75.5");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(addBookProgress).toHaveBeenCalledWith(1, { unit: "percent", value: 75.5 });
  });

  it("restores the recorded value when switching back to its unit", async () => {
    const wrapper = mountEditor({ progress: { unit: "percent", value: 30 } });

    await wrapper.get('[data-test="unit-page"]').trigger("click");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("");
    await wrapper.get('[data-test="unit-percent"]').trigger("click");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(addBookProgress).toHaveBeenCalledWith(1, { unit: "percent", value: 30 });
  });

  it("emits cancel without saving the draft", async () => {
    const wrapper = mountEditor({ progress: { unit: "page", value: 10 } });

    await wrapper.get('[data-test="progress-input"]').setValue("99");
    await wrapper.get('[data-test="cancel-progress"]').trigger("click");

    expect(wrapper.emitted("cancel")).toEqual([[]]);
    expect(addBookProgress).not.toHaveBeenCalled();
  });

  it.each([
    { unit: "page", value: "", message: "Please enter a page number." },
    { unit: "page", value: "-1", message: "Please enter a valid page number." },
    { unit: "percent", value: "", message: "Please enter a percentage." },
    { unit: "percent", value: "-1", message: "Please enter a percentage between 0 and 100." },
    { unit: "percent", value: "101", message: "Please enter a percentage between 0 and 100." },
  ])("rejects '$value' in $unit mode", async ({ unit, value, message }) => {
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const wrapper = mountEditor({ progress: { unit: "page", value: 0 } });

    await wrapper.get(`[data-test="unit-${unit}"]`).trigger("click");
    await wrapper.get('[data-test="progress-input"]').setValue(value);
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(alert).toHaveBeenCalledWith(message);
    expect(addBookProgress).not.toHaveBeenCalled();
  });

  it("disables controls while saving and keeps the draft after a failed save", async () => {
    let fail!: (error: Error) => void;
    vi.mocked(addBookProgress).mockReturnValue(new Promise((_, reject) => (fail = reject)));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const wrapper = mountEditor({ progress: { unit: "page", value: 10 } });
    await wrapper.get('[data-test="progress-input"]').setValue("42");
    await wrapper.get('[data-test="save-progress"]').trigger("click");

    expect(wrapper.get('[data-test="save-progress"]').text()).toBe("Saving…");
    for (const control of wrapper.findAll<HTMLInputElement | HTMLButtonElement>("input, button")) {
      expect(control.element.disabled).toBe(true);
    }
    await wrapper.get('[data-test="save-progress"]').trigger("click");
    await wrapper.get('[data-test="cancel-progress"]').trigger("click");
    expect(addBookProgress).toHaveBeenCalledOnce();
    expect(wrapper.emitted("cancel")).toBeUndefined();

    fail(new Error("Network error"));
    await flushPromises();

    expect(alert).toHaveBeenCalledWith("Failed to save progress");
    expect(wrapper.emitted("saved")).toBeUndefined();
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.value).toBe("42");
    expect(wrapper.get<HTMLInputElement>('[data-test="progress-input"]').element.disabled).toBe(false);
  });
});
