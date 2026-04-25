import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated, checkAuthStatus } from '../api/auth'
import { setupAuthInterceptor } from '../api/client'
import LoginView from '../views/LoginView.vue'
import BooksView from '../views/BooksView.vue'
import BookDetailView from '../views/BookDetailView.vue'
import BookEditView from '../views/BookEditView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'books',
      component: BooksView,
      meta: { requiresAuth: true },
    },
    {
      path: '/books/:id',
      name: 'book-detail',
      component: BookDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/books/:id/edit',
      name: 'book-edit',
      component: BookEditView,
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true },
    },
  ],
})

// Setup API client to handle authentication errors
setupAuthInterceptor(router)

// Track if initial auth check has completed
let authCheckComplete = false
let authCheckPromise: Promise<boolean> | null = null

// Navigation guard
router.beforeEach(async (to, _from, next) => {
  // On first navigation, verify auth status via API (HttpOnly cookies)
  if (!authCheckComplete) {
    if (!authCheckPromise) {
      authCheckPromise = checkAuthStatus()
    }
    await authCheckPromise
    authCheckComplete = true
  }

  const requiresAuth = to.meta.requiresAuth

  if (requiresAuth && !isAuthenticated()) {
    // Redirect to login if route requires auth and user is not authenticated
    next({ name: 'login' })
  } else if (to.name === 'login' && isAuthenticated()) {
    // Redirect to books if user is already authenticated and trying to access login
    next({ name: 'books' })
  } else {
    next()
  }
})

export default router
