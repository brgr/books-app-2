import { describe, expect, it } from "vitest";
import { parseShelfRef, ReadingShelf } from "./types";

describe("parseShelfRef", () => {
  it("accepts valid reading and custom shelf refs", () => {
    expect(parseShelfRef("reading:started")).toBe("reading:started");
    expect(parseShelfRef("custom:12")).toBe("custom:12");
  });

  it.each(["reading:invalid-reading-state", "custom:0", "custom:-1", "custom:1.5", "not-a-shelf-ref"])(
    "rejects invalid shelf ref %s",
    (value) => {
      expect(() => parseShelfRef(value)).toThrow("Invalid shelf reference");
    },
  );

  it("keeps the built-in values separate from fully qualified refs", () => {
    expect(ReadingShelf.WANT_TO_READ).toBe("want_to_read");
    expect(parseShelfRef("reading:want_to_read")).toBe("reading:want_to_read");
  });
});
