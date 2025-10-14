<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentUser, logout } from '../api/auth'
import type { User } from '../api/types'

const router = useRouter()
const user = ref<User | null>(null)

onMounted(async () => {
  try {
    user.value = await getCurrentUser()
  } catch (error) {
    console.error('Failed to get current user:', error)
  }
})

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar">
    <div class="navbar-content">
      <router-link to="/" class="navbar-brand">Books</router-link>
      <div v-if="user" class="navbar-user">
        <span class="text-small">{{ user.username }}</span>
        <button @click="handleLogout" class="btn-small">Logout</button>
      </div>
    </div>
  </nav>
</template>
