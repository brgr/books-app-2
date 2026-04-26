<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { startCoverUpgradeSearch, getCoverUpgradeSearch } from '../api/books'
import type { CoverUpgradeCandidate } from '../api/types'
import { getMediaUrl } from '../api/client'

const props = defineProps<{
  bookId: number
}>()

const emit = defineEmits<{
  close: []
  select: [imageUrl: string]
}>()

const status = ref<'starting' | 'running' | 'done' | 'failed' | 'empty'>('starting')
const results = ref<CoverUpgradeCandidate[]>([])
const errorMsg = ref('')

let jobId: string | null = null
let pollTimer: number | null = null
let cancelled = false

const POLL_INTERVAL_MS = 1500

async function poll() {
  if (cancelled || !jobId) return
  try {
    const job = await getCoverUpgradeSearch(props.bookId, jobId)
    if (cancelled) return
    if (job.status === 'done') {
      results.value = job.results
      status.value = job.results.length > 0 ? 'done' : 'empty'
      return
    }
    if (job.status === 'failed') {
      status.value = 'failed'
      errorMsg.value = job.error || 'Upgrade search failed.'
      return
    }
    pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS)
  } catch (err: any) {
    if (cancelled) return
    console.error('Cover upgrade poll failed:', err)
    status.value = 'failed'
    errorMsg.value = err.response?.data?.detail || 'Failed to check upgrade job.'
  }
}

onMounted(async () => {
  try {
    const job = await startCoverUpgradeSearch(props.bookId)
    if (cancelled) return
    jobId = job.job_id
    status.value = 'running'
    pollTimer = window.setTimeout(poll, POLL_INTERVAL_MS)
  } catch (err: any) {
    console.error('Failed to start cover upgrade:', err)
    status.value = 'failed'
    errorMsg.value = err.response?.data?.detail || 'Failed to start upgrade search.'
  }
})

onBeforeUnmount(() => {
  cancelled = true
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
})

function handleSelect(c: CoverUpgradeCandidate) {
  emit('select', c.image_url)
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal">
      <div class="modal-header">
        <h3>Upgrade Cover</h3>
        <button @click="handleClose" class="btn-small">Close</button>
      </div>

      <div class="modal-body">
        <div v-if="status === 'starting' || status === 'running'" class="loading">
          Looking for a higher-resolution cover...
        </div>

        <div v-else-if="status === 'failed'" class="error">{{ errorMsg }}</div>

        <div v-else-if="status === 'empty'" class="empty-state">
          <p>No better cover found. The current one looks like the best available.</p>
        </div>

        <div v-else-if="status === 'done'" class="cover-grid">
          <button
            v-for="(c, index) in results"
            :key="index"
            class="cover-tile"
            @click="handleSelect(c)"
            :title="`${c.width}×${c.height} · ${c.source}`"
          >
            <img :src="getMediaUrl(c.thumbnail_url)" :alt="`Candidate ${index + 1}`" loading="lazy" />
            <div class="cover-caption">
              <span class="cover-size">{{ c.width }}&times;{{ c.height }}</span>
              <span class="cover-meta">
                {{ c.source }} &middot;
                <span :class="['quality', c.match_quality]">{{ c.match_quality }}</span>
                &middot; {{ c.size_ratio.toFixed(1) }}&times;
              </span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cover-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--spacing-md);
  max-height: 60vh;
  overflow-y: auto;
}

.cover-tile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.cover-tile:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.cover-tile img {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-bg);
}

.cover-caption {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
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
