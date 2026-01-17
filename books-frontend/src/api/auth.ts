import { apiClient, isAuthenticated, setAuthenticated } from './client'
import type { User } from './types'

export { isAuthenticated }

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export async function login(username: string, password: string): Promise<void> {
  const payload = new URLSearchParams()
  payload.append('username', username)
  payload.append('password', password)

  // Server sets HttpOnly cookies on successful login
  await apiClient.post('/token', payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  setAuthenticated(true)
}

export async function logout(): Promise<void> {
  try {
    // Server clears HttpOnly cookies
    await apiClient.post('/auth/logout')
  } finally {
    setAuthenticated(false)
  }
}

export async function checkAuthStatus(): Promise<boolean> {
  /**
   * Verify authentication by calling /users/me.
   * If the HttpOnly cookie is valid, this will succeed.
   * Used on app startup to restore authentication state.
   */
  try {
    await apiClient.get('/users/me')
    setAuthenticated(true)
    return true
  } catch {
    setAuthenticated(false)
    return false
  }
}
