<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { login, register, getCurrentUser } from '../api/auth'

const router = useRouter()
const route = useRoute()

const isRegistering = ref(false)
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    if (isRegistering.value) {
      // Register new user
      await register(username.value, password.value)
    }

    // Login
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

function toggleMode() {
  isRegistering.value = !isRegistering.value
  error.value = ''
}
</script>

<template>
  <div class="container-narrow">
    <div class="card" style="margin-top: 4rem;">
      <h2 class="text-center">{{ isRegistering ? 'Register' : 'Login' }}</h2>

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
          {{ loading ? 'Please wait...' : (isRegistering ? 'Register' : 'Login') }}
        </button>
      </form>

      <p class="text-center text-small mt-1">
        {{ isRegistering ? 'Already have an account?' : "Don't have an account?" }}
        <a href="#" @click.prevent="toggleMode">
          {{ isRegistering ? 'Login' : 'Register' }}
        </a>
      </p>
    </div>
  </div>
</template>

<style scoped>
a {
  color: var(--color-primary);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>
