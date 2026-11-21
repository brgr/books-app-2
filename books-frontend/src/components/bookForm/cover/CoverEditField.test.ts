import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import CoverEditField from "./CoverEditField.vue";

const fullUrl = "https://books.google.com/books/content?id=X&zoom=2";
const images: FakeImage[] = [];
class FakeImage {
  src = "";
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor() {
    images.push(this);
  }
}

function mountField() {
  return mount(CoverEditField, {
    props: { modelValue: fullUrl, title: "Book", author: "Author", isbn: "" },
    global: { stubs: { CoverModal: true } },
  });
}

describe("cover preview", () => {
  beforeEach(() => {
    images.length = 0;
    vi.stubGlobal("Image", FakeImage);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("loads the thumbnail before requesting and displaying the validated full image", async () => {
    const wrapper = mountField();

    expect(wrapper.get("img").attributes("src")).toBe(fullUrl.replace("zoom=2", "zoom=1"));
    expect(images).toHaveLength(0);

    await wrapper.get("img").trigger("load");

    expect(images).toHaveLength(1);
    expect(images[0]!.src).toBe(`/api/books/cover-preview?url=${encodeURIComponent(fullUrl)}`);
    expect(wrapper.get("img").attributes("src")).toContain("zoom=1");

    images[0]!.onload!();
    await nextTick();

    expect(wrapper.get("img").attributes("src")).toBe(images[0]!.src);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();

    wrapper.unmount();
  });

  it("keeps the thumbnail on failure and cancels obsolete image callbacks", async () => {
    const wrapper = mountField();
    await wrapper.get("img").trigger("load");

    images[0]!.onerror?.();

    expect(wrapper.get("img").attributes("src")).toContain("zoom=1");

    await wrapper.setProps({ modelValue: "/uploads/new.jpg" });

    expect(images[0]!.onload).toBeNull();
    expect(wrapper.get("img").attributes("src")).toBe("/uploads/new.jpg");

    await wrapper.get("img").trigger("load");

    expect(images).toHaveLength(1);

    wrapper.unmount();
  });
});
