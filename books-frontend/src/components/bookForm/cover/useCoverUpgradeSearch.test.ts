import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { getCoverUpgradeSearch, startCoverUpgradeSearch } from "../../../api/covers";
import type { CoverUpgradeJob } from "../../../api/types";
import { useCoverUpgradeSearch } from "./useCoverUpgradeSearch";

vi.mock("../../../api/covers", () => ({
  startCoverUpgradeSearch: vi.fn(),
  getCoverUpgradeSearch: vi.fn(),
}));

const running: CoverUpgradeJob = { job_id: "job-1", status: "running", results: [] };
const candidate = {
  image_url: "/cover.jpg",
  thumbnail_url: "/thumbnail.jpg",
  width: 600,
  height: 900,
  source: "Google Books",
  phash_distance: 0,
  match_quality: "exact" as const,
  size_ratio: 2,
};
const cleanups: Array<() => void> = [];

function mountSearch() {
  let search!: ReturnType<typeof useCoverUpgradeSearch>;

  const wrapper = mount(
    defineComponent({
      setup() {
        search = useCoverUpgradeSearch(42);
        return () => null;
      },
    }),
  );

  cleanups.push(() => wrapper.unmount());

  return { search, wrapper };
}

describe("useCoverUpgradeSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(startCoverUpgradeSearch).mockResolvedValue(running);
    vi.mocked(getCoverUpgradeSearch).mockResolvedValue(running);
  });

  afterEach(() => {
    cleanups.splice(0).forEach((cleanup) => cleanup());
    vi.useRealTimers();
    vi.resetAllMocks();
  });

  it.each([
    { job: { ...running, status: "done", results: [candidate] }, status: "done", error: "" },
    { job: { ...running, status: "done" }, status: "empty", error: "" },
    { job: { ...running, status: "failed", error: "Search failed" }, status: "failed", error: "Search failed" },
  ] satisfies Array<{ job: CoverUpgradeJob; status: string; error: string }>)(
    "polls until $status and then stops",
    async ({ job, status, error }) => {
      vi.mocked(getCoverUpgradeSearch).mockResolvedValueOnce(running).mockResolvedValueOnce(job);

      const { search } = mountSearch();

      expect(search.status.value).toBe("starting");

      await flushPromises();

      expect(startCoverUpgradeSearch).toHaveBeenCalledWith(42);
      expect(search.status.value).toBe("running");

      await vi.advanceTimersByTimeAsync(1500);

      expect(getCoverUpgradeSearch).toHaveBeenCalledWith(42, "job-1");
      expect(search.status.value).toBe("running");

      await vi.advanceTimersByTimeAsync(1500);

      expect(search.status.value).toBe(status);
      expect(search.results.value).toEqual(job.results);
      expect(search.errorMsg.value).toBe(error);

      await vi.advanceTimersByTimeAsync(4500);

      expect(getCoverUpgradeSearch).toHaveBeenCalledTimes(2);
    },
  );

  it("clears scheduled polling when unmounted", async () => {
    const { wrapper } = mountSearch();
    await flushPromises();
    wrapper.unmount();

    expect(vi.getTimerCount()).toBe(0);

    await vi.advanceTimersByTimeAsync(3000);

    expect(getCoverUpgradeSearch).not.toHaveBeenCalled();
  });

  it("ignores a poll response arriving after unmount", async () => {
    let resolve!: (job: CoverUpgradeJob) => void;
    vi.mocked(getCoverUpgradeSearch).mockReturnValue(new Promise((done) => (resolve = done)));
    const { search, wrapper } = mountSearch();
    await flushPromises();
    await vi.advanceTimersByTimeAsync(1500);
    wrapper.unmount();

    resolve({ ...running, status: "done", results: [candidate] });

    await flushPromises();

    expect(search.status.value).toBe("running");
    expect(search.results.value).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("ignores a start failure arriving after unmount", async () => {
    let reject!: (reason: Error) => void;
    vi.mocked(startCoverUpgradeSearch).mockReturnValue(new Promise((_, fail) => (reject = fail)));
    const { search, wrapper } = mountSearch();
    wrapper.unmount();
    reject(new Error("Request failed"));
    await flushPromises();

    expect(search.status.value).toBe("starting");
    expect(search.errorMsg.value).toBe("");
    expect(vi.getTimerCount()).toBe(0);
  });
});
