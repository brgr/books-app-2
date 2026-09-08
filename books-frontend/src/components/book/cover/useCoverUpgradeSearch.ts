import { onBeforeUnmount, onMounted, ref } from "vue";
import { getCoverUpgradeSearch, startCoverUpgradeSearch } from "../../../api/covers";
import type { CoverUpgradeCandidate } from "../../../api/types";

// Each mounted upgrade tab owns one search job and its polling lifecycle.
export function useCoverUpgradeSearch(bookId: number) {
  const status = ref<"starting" | "running" | "done" | "failed" | "empty">("starting");
  const results = ref<CoverUpgradeCandidate[]>([]);
  const errorMsg = ref("");

  let jobId: string | null = null;
  let pollTimer: number | null = null;
  let cancelled = false;

  const POLL_INTERVAL_MS = 1500;

  async function poll() {
    if (cancelled || !jobId) return;

    try {
      const job = await getCoverUpgradeSearch(bookId, jobId);

      if (cancelled) return;

      if (job.status === "done") {
        results.value = job.results;
        status.value = job.results.length > 0 ? "done" : "empty";
        return;
      }

      if (job.status === "failed") {
        status.value = "failed";
        errorMsg.value = job.error || "Upgrade search failed.";
        return;
      }

      pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS);
    } catch (err: any) {
      if (cancelled) return;

      console.error("Cover upgrade poll failed:", err);
      status.value = "failed";
      errorMsg.value = err.response?.data?.detail || "Failed to check upgrade job.";
    }
  }

  onMounted(async () => {
    try {
      const job = await startCoverUpgradeSearch(bookId);

      if (cancelled) return;

      jobId = job.job_id;
      status.value = "running";
      pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS);
    } catch (err: any) {
      if (cancelled) return;

      console.error("Failed to start cover upgrade:", err);
      status.value = "failed";
      errorMsg.value = err.response?.data?.detail || "Failed to start upgrade search.";
    }
  });

  onBeforeUnmount(() => {
    cancelled = true;
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  });

  return { status, results, errorMsg };
}
