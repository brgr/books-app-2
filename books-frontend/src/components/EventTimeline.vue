<script setup lang="ts">
import {BookEventType, type BookEvent} from '../api/types'

defineProps<{
  events: BookEvent[]
}>()

function formatEventType(event: BookEvent): string {
  switch (event.event_type) {
    case BookEventType.ADDED_TO_LIBRARY:
      return event.import_id != null ? 'Imported to library' : 'Added to library'
    case BookEventType.STARTED_READING:
      return 'Started reading'
    case BookEventType.FINISHED_READING:
      return 'Finished reading'
    case BookEventType.NOTE_SET:
      return event.note ? 'Note updated' : 'Note cleared'
    case BookEventType.PROGRESS_SET:
      return 'Progress updated'
    default:
      return event.event_type
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="event-timeline">
    <h3>Activity</h3>
    <div v-if="events.length === 0" class="no-events">
      No activity yet
    </div>
    <div v-else class="timeline">
      <div
          v-for="event in events"
          :key="event.id"
          class="timeline-item"
      >
        <div class="timeline-dot"></div>
        <div class="timeline-content">
          <div class="event-label">{{ formatEventType(event) }}</div>
          <div class="event-date">{{ formatDate(event.occurred_at) }} at {{ formatTime(event.occurred_at) }}</div>
          <div v-if="event.event_type === BookEventType.NOTE_SET && event.note" class="event-note">
            {{ event.note }}
          </div>
          <div v-if="event.event_type === BookEventType.PROGRESS_SET && event.page !== null && event.page !== undefined" class="event-note">
            Page {{ event.page }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.event-timeline {
  margin-top: var(--spacing-xl);
}

.event-timeline h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.no-events {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.timeline {
  position: relative;
  padding-left: var(--spacing-lg);
}

.timeline-item {
  position: relative;
  padding-bottom: var(--spacing-md);
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--spacing-lg) + 5px);
  top: 14px;
  bottom: 0;
  width: 2px;
  background-color: var(--color-border);
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-item:last-child::before {
  display: none;
}

.timeline-dot {
  position: absolute;
  left: calc(-1 * var(--spacing-lg) + 1px);
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--color-primary);
  border: 2px solid var(--color-bg-card);
  box-shadow: 0 0 0 2px var(--color-primary);
}

.timeline-content {
  padding-left: var(--spacing-sm);
  position: relative;
  top: -3px;
}

.event-label {
  font-weight: 500;
  color: var(--color-text);
  font-size: 14px;
}

.event-date {
  color: var(--color-text-secondary);
  font-size: 12px;
  margin-top: 2px;
}

.event-note {
  margin-top: var(--spacing-xs);
  white-space: pre-wrap;
  color: var(--color-text);
  font-size: 0.95rem;
  line-height: 1.5;
}
</style>
