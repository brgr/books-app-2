import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import BookNotes from "./BookNotes.vue";

describe("BookNotes", () => {
  it("renders markdown when notes are present", () => {
    const wrapper = mount(BookNotes, { props: { modelValue: "**bold** text", editing: false } });
    expect(wrapper.html()).toContain("<strong>bold</strong>");
  });

  it("shows empty state when notes are blank", () => {
    const wrapper = mount(BookNotes, { props: { modelValue: "", editing: false } });
    expect(wrapper.text()).toContain("No notes yet");
  });

  it("sanitizes HTML and unsafe links while preserving Markdown formatting", () => {
    const wrapper = mount(BookNotes, {
      props: {
        modelValue:
          '**safe** [link](https://example.com) [unsafe](javascript:alert%281%29)\n\n<script>alert(1)</script><img src="x" onerror="alert(1)">',
        editing: false,
      },
    });

    const rendered = wrapper.get(".notes-rendered");

    expect(rendered.get("strong").text()).toBe("safe");
    expect(rendered.get('a[href="https://example.com"]').text()).toBe("link");
    expect(rendered.find("script").exists()).toBe(false);
    expect(rendered.get("img").attributes("onerror")).toBeUndefined();
    expect(rendered.find('a[href^="javascript:"]').exists()).toBe(false);
    expect(rendered.text()).toContain("unsafe");
  });

  it("edits the notes in a textarea and submits with Ctrl+Enter", async () => {
    const wrapper = mount(BookNotes, { props: { modelValue: "old", editing: true } });
    const textarea = wrapper.get("textarea");
    expect(textarea.element.value).toBe("old");
    await textarea.setValue("new note");
    await textarea.trigger("keydown", { key: "Enter", ctrlKey: true });
    expect(wrapper.emitted("update:modelValue")).toEqual([["new note"]]);
    expect(wrapper.emitted("submit")).toEqual([[]]);
  });
});
