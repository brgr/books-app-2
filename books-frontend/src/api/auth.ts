import { apiClient, setAuthToken as setClientAuth, clearAuthToken as clearClientAuth, isAuthenticated } from './client'
import type { User } from './types'

export { isAuthenticated }

type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  refresh_expires_in: number
}

type RefreshResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export async function login(username: string, password: string): Promise<void> {
  const payload = new URLSearchParams()
  payload.append('username', username)
  payload.append('password', password)

  const response = await apiClient.post<LoginResponse>('/token', payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  const token = response.data.access_token
  const refreshToken = response.data.refresh_token
  setClientAuth(token)
  // Store token in localStorage for persistence
  localStorage.setItem('auth_token', token)
  localStorage.setItem('refresh_token', refreshToken)
}

export function logout(): void {
  clearClientAuth()
  localStorage.removeItem('auth_token')
  localStorage.removeItem('refresh_token')
}

export function restoreAuthFromStorage(): boolean {
  const token = localStorage.getItem('auth_token')
  if (token) {
    setClientAuth(token)
    return true
  }

  localStorage.removeItem('auth_username')
  localStorage.removeItem('auth_password')
  return false
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null

  try {
    const response = await apiClient.post<RefreshResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    const token = response.data.access_token
    setClientAuth(token)
    localStorage.setItem('auth_token', token)
    return token
  } catch {
    return null
  }
}
