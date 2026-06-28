<script setup lang="ts">
import {computed, onBeforeUnmount} from 'vue'
import {ReadingStatus, type Book} from '../api/types'
import {getMediaUrl} from '../api/client'

const props = withDefaults(
  defineProps<{
    book: Book
    showProgress?: boolean
  }>(),
  {showProgress: false}
)

const emit = defineEmits<{
  (e: 'click', bookId: number): void
  (e: 'menu', payload: { bookId: number; x: number; y: number }): void
}>()

const LONG_PRESS_MS = 500
const MOVE_THRESHOLD = 10
let pressTimer: ReturnType<typeof setTimeout> | null = null
let longPressed = false
let startX = 0
let startY = 0

function clearPressTimer() {
  if (pressTimer !== null) {
    clearTimeout(pressTimer)
    pressTimer = null
  }
}

function onContextMenu(e: MouseEvent) {
  e.preventDefault()
  emit('menu', { bookId: props.book.id, x: e.clientX, y: e.clientY })
}

function onTouchStart(e: TouchEvent) {
  longPressed = false
  const touch = e.touches[0]
  if (!touch) return
  startX = touch.clientX
  startY = touch.clientY
  clearPressTimer()
  pressTimer = setTimeout(() => {
    longPressed = true
    emit('menu', { bookId: props.book.id, x: startX, y: startY })
  }, LONG_PRESS_MS)
}

function onTouchMove(e: TouchEvent) {
  const touch = e.touches[0]
  if (!touch) return
  if (
    Math.abs(touch.clientX - startX) > MOVE_THRESHOLD ||
    Math.abs(touch.clientY - startY) > MOVE_THRESHOLD
  ) {
    clearPressTimer()
  }
}

function onTouchEnd() {
  clearPressTimer()
}

function onClick() {
  if (longPressed) {
    longPressed = false
    return
  }
  emit('click', props.book.id)
}

onBeforeUnmount(clearPressTimer)

const coverUrl = computed(() =>
  getMediaUrl(props.book.cover_thumbnail_url || props.book.cover_image_url)
)

const showBadge = computed(() => {
  if (!props.showProgress) return false
  const status = props.book.user_status
  return (
    status?.status === ReadingStatus.STARTED &&
    Boolean(props.book.page_count) &&
    status?.current_page !== null &&
    status?.current_page !== undefined
  )
})

const progressPercent = computed(() => {
  const pageCount = props.book.page_count ?? 0
  const currentPage = props.book.user_status?.current_page ?? 0
  if (pageCount <= 0) return 0
  const percent = Math.round((currentPage / pageCount) * 100)
  return Math.min(100, Math.max(0, percent))
})
</script>

<template>
  <div class="grid-item">
    <button
      type="button"
      class="grid-cover-link"
      @click="onClick"
      @contextmenu="onContextMenu"
      @touchstart.passive="onTouchStart"
      @touchmove.passive="onTouchMove"
      @touchend="onTouchEnd"
      @touchcancel="onTouchEnd"
    >
      <span v-if="showBadge" class="grid-progress-badge">
        {{ progressPercent }}%
      </span>
      <img
        v-if="coverUrl"
        :src="coverUrl"
        :alt="book.title"
        :title="book.title + ' by ' + book.author"
        class="grid-cover"
      />
      <div
        v-else
        class="grid-cover-placeholder"
        :title="book.title + ' by ' + book.author"
      >
        <div class="grid-no-cover-text">{{ book.title }}</div>
      </div>
    </button>
  </div>
</template>

<style scoped>
.grid-item {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: visible;
}

.grid-cover-link {
  padding: 0;
  border: none;
  background: transparent;
  text-decoration: none;
  display: block;
  cursor: grab;
  width: 100%;
  text-align: left;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
  position: relative;
}

.grid-cover {
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: var(--shadow);
  display: block;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.grid-cover:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.grid-cover-placeholder {
  width: 100%;
  max-width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: var(--shadow);
  padding: var(--spacing-md);
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.grid-cover-placeholder:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.grid-no-cover-text {
  text-align: center;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  word-break: break-word;
  line-height: 1.4;
}

.grid-progress-badge {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 2;
  background: rgba(20, 24, 31, 0.85);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 7px;
  border-radius: 999px;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
  pointer-events: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.grid-cover-link:hover .grid-progress-badge {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.25);
}
</style>
