<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { login, getCurrentUser } from '../api/auth'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    login(username.value, password.value)

    // Verify login worked
    await getCurrentUser()

    // Redirect to original page or books list
    const redirect = route.query.redirect as string
    router.push(redirect || '/')
  } catch (err: any) {
    console.error('Authentication error:', err)
    error.value = err.response?.data?.detail || 'Authentication failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container-narrow">
    <div class="card" style="margin-top: 4rem;">
      <h2 class="text-center">Login</h2>

      <div v-if="error" class="error">
        {{ error }}
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="Enter username"
            required
            minlength="3"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="Enter password"
            required
            minlength="6"
            :disabled="loading"
          />
        </div>

        <button type="submit" class="btn-primary" style="width: 100%;" :disabled="loading">
          {{ loading ? 'Please wait...' : 'Login' }}
        </button>
      </form>

      <p class="text-center text-small mt-1">
        The account is created via <code>python manage.py create-superuser</code> on the backend.
      </p>
    </div>
  </div>
</template>
