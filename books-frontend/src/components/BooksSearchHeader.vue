<script setup lang="ts">
import { ref } from 'vue'
import { ReadingStatus } from '../api/types'

const searchQuery = defineModel<string>('searchQuery', { required: true })
const filterStatus = defineModel<ReadingStatus | ''>('filterStatus', { required: true })
const viewMode = defineModel<'list' | 'grid'>('viewMode', { required: true })

const showFilterDropdown = ref(false)

function toggleFilterDropdown() {
  showFilterDropdown.value = !showFilterDropdown.value
}

function getStatusLabel(status: ReadingStatus): string {
  const labels = {
    [ReadingStatus.WANT_TO_READ]: 'Want to read',
    [ReadingStatus.STARTED]: 'Started',
    [ReadingStatus.FINISHED]: 'Finished',
    [ReadingStatus.ABANDONED]: 'Abandoned',
  }
  return labels[status] || status
}
</script>

<template>
  <div class="search-header">
    <div class="search-bar">
      <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search for words or #tags"
        class="search-input"
      />
    </div>

    <div class="search-actions">
      <div class="filter-dropdown-wrapper">
        <button @click="toggleFilterDropdown" class="filter-btn" title="Filter options">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
          </svg>
        </button>

        <div v-if="showFilterDropdown" class="filter-dropdown">
          <div class="filter-dropdown-section">
            <label class="filter-dropdown-label">Status</label>
            <select v-model="filterStatus" class="filter-dropdown-select" @change="showFilterDropdown = false">
              <option value="">All books</option>
              <option :value="ReadingStatus.WANT_TO_READ">
                {{ getStatusLabel(ReadingStatus.WANT_TO_READ) }}
              </option>
              <option :value="ReadingStatus.STARTED">
                {{ getStatusLabel(ReadingStatus.STARTED) }}
              </option>
              <option :value="ReadingStatus.FINISHED">
                {{ getStatusLabel(ReadingStatus.FINISHED) }}
              </option>
              <option :value="ReadingStatus.ABANDONED">
                {{ getStatusLabel(ReadingStatus.ABANDONED) }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <div class="view-toggle">
        <button
          @click="viewMode = 'list'"
          :class="['view-btn', { active: viewMode === 'list' }]"
          title="List view"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
          </svg>
        </button>

        <button
          @click="viewMode = 'grid'"
          :class="['view-btn', { active: viewMode === 'grid' }]"
          title="Grid view"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  align-items: center;
  justify-content: space-between;
  border-radius: var(--border-radius);
  max-width: 100%;
  overflow: visible;
}

.search-bar {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 500px;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background-color: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-bar:hover {
  border-color: var(--color-text-secondary);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(88, 86, 214, 0.35);
}

.search-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.search-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0 var(--spacing-xs);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border: none;
}

.filter-dropdown-wrapper {
  position: relative;
}

.filter-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-sm);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  min-width: 36px;
  min-height: 36px;
}

.filter-btn:hover {
  color: var(--color-text);
  background-color: var(--color-bg);
  border-color: var(--color-text-secondary);
}

.view-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  overflow: hidden;
  background-color: var(--color-bg-card);
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  min-width: 36px;
  min-height: 36px;
  position: relative;
}

.view-btn:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 60%;
  width: 1px;
  background-color: var(--color-border);
}

.view-btn:hover:not(.active) {
  color: var(--color-text);
  background-color: var(--color-bg);
}

.filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: var(--modal-shadow);
  padding: var(--spacing-md);
  min-width: 200px;
  z-index: 100;
}

.filter-dropdown-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.filter-dropdown-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 0;
}

.filter-dropdown-select {
  width: 100%;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background-color: var(--color-bg-card);
  color: var(--color-text);
}

.view-btn.active {
  background-color: var(--color-primary);
  color: white;
}

.view-btn.active::after {
  display: none;
}

.view-btn.active:hover {
  background-color: var(--color-primary-hover);
  color: white;
}

@media (max-width: 768px) {
  .search-header {
    flex-wrap: wrap;
  }

  .search-bar {
    flex: 1 1 100%;
    max-width: 100%;
    order: -1;
  }

  /* Prevent iOS Safari zooming inputs with font-size under 16px. */
  .search-input {
    font-size: 16px;
  }

  .filter-btn {
    flex: 1;
  }

  .view-toggle {
    flex: 1;
  }

  .view-btn {
    flex: 1;
  }
}
</style>
