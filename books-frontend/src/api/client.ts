import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Helper to set auth credentials
export function setAuthCredentials(username: string, password: string) {
  const credentials = btoa(`${username}:${password}`)
  apiClient.defaults.headers.common['Authorization'] = `Basic ${credentials}`
}

// Helper to clear auth credentials
export function clearAuthCredentials() {
  delete apiClient.defaults.headers.common['Authorization']
}

// Helper to check if user is authenticated
export function isAuthenticated(): boolean {
  return !!apiClient.defaults.headers.common['Authorization']
}

// Setup response interceptor to handle authentication errors
export function setupAuthInterceptor(router: any) {
  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      // Check if error is due to authentication failure
      if (error.response && (error.response.status === 401 || error.response.status === 403)) {
        // Clear authentication
        clearAuthCredentials()
        localStorage.removeItem('auth_username')
        localStorage.removeItem('auth_password')

        // Redirect to login page if not already there
        if (router.currentRoute.value.name !== 'login') {
          router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      }

      return Promise.reject(error)
    }
  )
}
