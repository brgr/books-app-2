import { describe, it, expect, beforeEach, vi } from "vitest";
import { ShelfName, type Shelf } from "../api/types";
import { cacheClear } from "../cache/store";
import { resetShelves, useShelves } from "./useShelves";

const getShelves = vi.fn();
vi.mock("../api/books", () => ({ getShelves: () => getShelves() }));

const shelves: Shelf[] = [
  { id: 7, name: ShelfName.STARTED, display_name: "Reading" },
  { id: 8, name: ShelfName.FINISHED, display_name: "Finished" },
];

async function flushPromises() {
  for (let i = 0; i < 5; i++) {
    await new Promise<void>((r) => setTimeout(r, 0));
  }
}

describe("useShelves", () => {
  beforeEach(async () => {
    await cacheClear();
    resetShelves();
    getShelves.mockReset();
    getShelves.mockResolvedValue(shelves);
  });

  it("returns the shelves once they arrive, and an empty list until then", async () => {
    const { shelves: loaded } = useShelves();

    expect(loaded.value).toEqual([]);

    await flushPromises();

    expect(loaded.value).toEqual(shelves);
  });

  it("fetches once however many callers ask, so a page of shelves makes one request", async () => {
    const first = useShelves();
    const second = useShelves();
    const third = useShelves();

    await flushPromises();

    expect(getShelves).toHaveBeenCalledTimes(1);
    expect(first.shelves.value).toEqual(shelves);
    expect(second.shelves.value).toEqual(shelves);
    expect(third.shelves.value).toEqual(shelves);
  });
});
