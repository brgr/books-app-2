<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import NavigationBar from '../components/NavigationBar.vue'
import { deleteAllBooks, getImports, importReadingList } from '../api/books'
import type { ImportRecord } from '../api/types'

const router = useRouter()
const showConfirm = ref(false)
const isDeleting = ref(false)

const importFile = ref<File | null>(null)
const isImporting = ref(false)
const importResult = ref<{ imported: number } | null>(null)
const importError = ref<string | null>(null)

const imports = ref<ImportRecord[]>([])
const importsError = ref<string | null>(null)

async function loadImports() {
  importsError.value = null
  try {
    imports.value = await getImports()
  } catch (e: any) {
    importsError.value = e.response?.data?.detail ?? 'Failed to load imports'
  }
}

onMounted(loadImports)

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return `${d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })} at ${d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
}

function handleDeleteAll() {
  showConfirm.value = true
}

function cancelDelete() {
  showConfirm.value = false
}

async function confirmDelete() {
  isDeleting.value = true
  try {
    await deleteAllBooks()
    router.push('/')
  } finally {
    isDeleting.value = false
    showConfirm.value = false
  }
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  importFile.value = input.files?.[0] ?? null
  importResult.value = null
  importError.value = null
}

async function handleImport() {
  if (!importFile.value) return
  isImporting.value = true
  importResult.value = null
  importError.value = null
  try {
    importResult.value = await importReadingList(importFile.value)
    await loadImports()
  } catch (e: any) {
    importError.value = e.response?.data?.detail ?? 'Import failed'
  } finally {
    isImporting.value = false
  }
}
</script>

<template>
  <NavigationBar />
  <div class="container-narrow">
    <h1>Settings</h1>

    <section class="settings-section">
      <h2>Import</h2>
      <div class="import-zone">
        <div class="import-item">
          <div>
            <strong>Import from Reading List</strong>
            <p class="text-muted">Import books from a Reading List app export (.zip file).</p>
          </div>
          <div class="import-controls">
            <input type="file" accept=".zip" @change="onFileSelected" :disabled="isImporting" />
            <button class="btn-primary" @click="handleImport" :disabled="!importFile || isImporting">
              {{ isImporting ? 'Importing...' : 'Import' }}
            </button>
          </div>
          <p v-if="importResult" class="import-success">
            Successfully imported {{ importResult.imported }} books.
          </p>
          <p v-if="importError" class="import-error">{{ importError }}</p>
        </div>

        <div v-if="imports.length > 0 || importsError" class="imports-history">
          <h3>Previous imports</h3>
          <p v-if="importsError" class="import-error">{{ importsError }}</p>
          <ul v-if="imports.length > 0" class="imports-list">
            <li v-for="imp in imports" :key="imp.id" class="imports-item">
              <div class="imports-item-main">
                <strong>{{ imp.filename ?? 'Unnamed import' }}</strong>
                <span class="imports-item-date">{{ formatTimestamp(imp.occurred_at) }}</span>
              </div>
              <div class="imports-item-counts text-muted">
                {{ imp.imported_count }} imported<span v-if="imp.skipped_count > 0">, {{ imp.skipped_count }} skipped</span>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="settings-section">
      <h2>Danger Zone</h2>
      <div class="danger-zone">
        <div class="danger-item">
          <div>
            <strong>Delete all books</strong>
            <p class="text-muted">Permanently remove all books from your library. This action cannot be undone.</p>
          </div>
          <button class="btn-danger" @click="handleDeleteAll">Delete All</button>
        </div>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="showConfirm" class="modal-overlay" @click.self="cancelDelete">
        <div class="modal">
          <div class="modal-header">
            <h3>Are you sure?</h3>
          </div>
          <div class="modal-body">
            <p>This will permanently delete <strong>all books</strong> from your library. This action cannot be undone.</p>
          </div>
          <div class="modal-footer">
            <button @click="cancelDelete" :disabled="isDeleting">Cancel</button>
            <button class="btn-danger" @click="confirmDelete" :disabled="isDeleting">
              {{ isDeleting ? 'Deleting...' : 'Delete All' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.settings-section {
  margin-top: var(--spacing-lg);
}

.settings-section h2 {
  font-size: 1.125rem;
  margin-bottom: var(--spacing-md);
}

.import-zone {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
}

.import-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.import-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.import-success {
  color: var(--color-success);
  margin: 0;
  font-weight: 500;
}

.import-error {
  color: var(--color-danger);
  margin: 0;
  font-weight: 500;
}

.imports-history {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.imports-history h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1rem;
}

.imports-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.imports-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.imports-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.imports-item-main {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  align-items: baseline;
  flex-wrap: wrap;
}

.imports-item-date {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.imports-item-counts {
  font-size: 13px;
}

.danger-zone {
  border: 1px solid var(--color-danger);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
}

.danger-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-lg);
}

.danger-item p {
  margin: var(--spacing-xs) 0 0;
  font-size: 13px;
}

.danger-item .btn-danger {
  flex-shrink: 0;
}

@media (max-width: 600px) {
  .danger-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .import-controls {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
