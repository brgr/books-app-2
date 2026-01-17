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
})

// Helper to set auth token
export function setAuthToken(token: string) {
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

// Helper to clear auth token
export function clearAuthToken() {
  delete apiClient.defaults.headers.common['Authorization']
}

// Helper to check if user is authenticated
export function isAuthenticated(): boolean {
  return !!apiClient.defaults.headers.common['Authorization']
}

type RefreshResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

async function tryRefreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null

  try {
    const response = await axios.post<RefreshResponse>(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    })
    const token = response.data.access_token
    setAuthToken(token)
    localStorage.setItem('auth_token', token)
    return token
  } catch {
    return null
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

        if (originalRequest && !originalRequest._retry) {
          originalRequest._retry = true
          const token = await tryRefreshAccessToken()
          if (token) {
            originalRequest.headers = originalRequest.headers || {}
            originalRequest.headers['Authorization'] = `Bearer ${token}`
            return apiClient(originalRequest)
          }
        }

        // Clear authentication after refresh failure
        clearAuthToken()
        localStorage.removeItem('auth_token')
        localStorage.removeItem('refresh_token')

        // Redirect to login page if not already there
        if (router.currentRoute.value.name !== 'login') {
          router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        }
      }

      return Promise.reject(error)
    }
  )
}
