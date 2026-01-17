import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function getMediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined
  if (path.startsWith('http')) return path
  return `${API_BASE_URL}${path}`
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Send cookies with every request (HttpOnly auth cookies)
  withCredentials: true,
})

// Track authentication state (verified via /users/me endpoint)
let authenticated = false

export function setAuthenticated(value: boolean) {
  authenticated = value
}

export function isAuthenticated(): boolean {
  return authenticated
}

async function tryRefreshAccessToken(): Promise<boolean> {
  try {
    // Refresh endpoint reads refresh token from HttpOnly cookie
    await apiClient.post('/auth/refresh')
    return true
  } catch {
    return false
  }
}

// Setup response interceptor to handle authentication errors
export function setupAuthInterceptor(router: any) {
  apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      // Check if error is due to authentication failure
      if (error.response && (error.response.status === 401 || error.response.status === 403)) {
        const originalRequest = error.config as typeof error.config & { _retry?: boolean }

        // Don't retry refresh or logout endpoints to avoid loops
        const isAuthEndpoint = originalRequest?.url?.includes('/auth/')

        if (originalRequest && !originalRequest._retry && !isAuthEndpoint) {
          originalRequest._retry = true
          const refreshed = await tryRefreshAccessToken()
          if (refreshed) {
            // Retry the original request (cookies are sent automatically)
            return apiClient(originalRequest)
          }
        }

        // Clear authentication state after refresh failure
        authenticated = false

        // Redirect to login page if not already there
        if (router.currentRoute.value.name !== 'login') {
          router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      }

      return Promise.reject(error)
    }
  )
}
