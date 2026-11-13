import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import BookRating from "./BookRating.vue";

enableAutoUnmount(afterEach);

describe("BookRating", () => {
  it("fills three whole stars and half of the fourth for a 3.5 rating", () => {
    const wrapper = mount(BookRating, { props: { modelValue: 3.5, editing: false } });
    expect(wrapper.findAll(".star-fill").map((path) => path.attributes("style"))).toEqual([
      "clip-path: inset(0 0% 0 0);",
      "clip-path: inset(0 0% 0 0);",
      "clip-path: inset(0 0% 0 0);",
      "clip-path: inset(0 50% 0 0);",
      "clip-path: inset(0 100% 0 0);",
    ]);
  });

  it("hides clearing until a rating exists", () => {
    const wrapper = mount(BookRating, { props: { modelValue: null, editing: true } });
    expect(wrapper.find("input:checked").exists()).toBe(false);
    expect(wrapper.find("button").exists()).toBe(false);
  });
});
