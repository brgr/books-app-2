<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated, logout } from '../api/auth'

const emit = defineEmits<{
  addBook: []
}>()

const router = useRouter()
const showLogout = ref(isAuthenticated())

async function handleLogout() {
  showLogout.value = false
  await logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar">
    <div class="navbar-content">
      <div class="navbar-left">
        <router-link to="/" class="navbar-brand">
          <svg class="navbar-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          BOOKS
        </router-link>
      </div>

      <div class="navbar-right">
        <button @click="emit('addBook')" class="btn-primary btn-add">
          Add book
        </button>
        <div v-if="showLogout" class="navbar-user">
          <button @click="handleLogout" class="navbar-link-btn">Logout</button>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background-color: var(--color-bg-card);
  overflow-x: hidden;
  width: 100%;
}

.navbar-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  overflow: hidden;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--color-text);
  text-decoration: none;
  text-transform: uppercase;
}

.navbar-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.navbar-links {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.navbar-link {
  color: var(--color-text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius);
  transition: background-color 0.15s ease;
}

.navbar-link:hover {
  background-color: var(--color-bg);
}

.navbar-link.router-link-active {
  color: var(--color-primary);
}

.navbar-link-btn {
  background: none;
  border: none;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  padding: var(--spacing-xs) var(--spacing-sm);
  cursor: pointer;
  border-radius: var(--border-radius);
  transition: background-color 0.15s ease;
}

.navbar-link-btn:hover {
  background-color: var(--color-bg);
}

.navbar-user {
  display: flex;
  align-items: center;
}

.btn-add {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-weight: 600;
}

@media (max-width: 768px) {
  .navbar-content {
    flex-wrap: nowrap;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }

  .navbar-left {
    flex: 0 1 auto;
    min-width: 0;
    gap: var(--spacing-sm);
  }

  .navbar-right {
    flex: 0 0 auto;
    gap: var(--spacing-sm);
  }

  .navbar-links {
    display: none;
  }

  .btn-add {
    font-size: 13px;
    padding: var(--spacing-xs) var(--spacing-sm);
    white-space: nowrap;
  }

  .navbar-link-btn {
    padding: var(--spacing-xs);
    font-size: 13px;
  }
}
</style>
