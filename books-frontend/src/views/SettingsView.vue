<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import NavigationBar from '../components/NavigationBar.vue'
import { deleteAllBooks } from '../api/books'

const router = useRouter()
const showConfirm = ref(false)
const isDeleting = ref(false)

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
</script>

<template>
  <NavigationBar />
  <div class="container-narrow">
    <h1>Settings</h1>

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
}
</style>
