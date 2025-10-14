import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated, restoreAuthFromStorage } from '../api/auth'
import { setupAuthInterceptor } from '../api/client'
import LoginView from '../views/LoginView.vue'
import BooksView from '../views/BooksView.vue'

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
  ],
})

// Restore authentication from localStorage on app start
restoreAuthFromStorage()

// Setup API client to handle authentication errors
setupAuthInterceptor(router)

// Navigation guard
router.beforeEach((to, _from, next) => {
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
