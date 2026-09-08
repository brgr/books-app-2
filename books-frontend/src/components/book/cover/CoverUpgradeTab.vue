<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { startCoverUpgradeSearch, getCoverUpgradeSearch } from "../../../api/covers";
import type { CoverUpgradeCandidate } from "../../../api/types";
import { getMediaUrl } from "../../../api/client";
import CoverCandidateGrid from "./CoverCandidateGrid.vue";
import CoverCandidateTile from "./CoverCandidateTile.vue";

const props = defineProps<{
  bookId: number;
}>();

const emit = defineEmits<{
  select: [imageUrl: string];
}>();

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
    const job = await getCoverUpgradeSearch(props.bookId, jobId);
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
    const job = await startCoverUpgradeSearch(props.bookId);
    if (cancelled) return;
    jobId = job.job_id;
    status.value = "running";
    pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS);
  } catch (err: any) {
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
</script>

<template>
  <p class="mode-hint">Looking for a higher-resolution copy of the current cover.</p>

  <div v-if="status === 'starting' || status === 'running'" class="loading">
    Looking for a higher-resolution cover...
  </div>

  <div v-else-if="status === 'failed'" class="error">{{ errorMsg }}</div>

  <div v-else-if="status === 'empty'" class="empty-state">
    <p>No better cover found. The current one looks like the best available.</p>
  </div>

  <CoverCandidateGrid v-else-if="status === 'done'">
    <CoverCandidateTile
      v-for="(c, index) in results"
      :key="index"
      :thumbnail-url="getMediaUrl(c.thumbnail_url)"
      :alt="`Candidate ${index + 1}`"
      @select="emit('select', c.image_url)"
      :title="`${c.width}×${c.height} · ${c.source}`"
    >
      <span class="cover-size">{{ c.width }}&times;{{ c.height }}</span>
      <span class="cover-meta">
        {{ c.source }} &middot;
        <span :class="['quality', c.match_quality]">{{ c.match_quality }}</span>
        &middot; {{ c.size_ratio.toFixed(1) }}&times;
      </span>
    </CoverCandidateTile>
  </CoverCandidateGrid>
</template>

<style scoped>
.mode-hint {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-md);
}

.cover-size {
  color: var(--color-text);
  font-weight: 600;
}

.cover-meta {
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quality.exact {
  color: var(--color-success, #2a9d4a);
  font-weight: 600;
}

.quality.likely {
  color: var(--color-text-secondary);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
</style>
