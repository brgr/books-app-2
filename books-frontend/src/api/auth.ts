import { apiClient, setAuthCredentials as setClientAuth, clearAuthCredentials as clearClientAuth, isAuthenticated } from './client'
import type { User } from './types'

export { isAuthenticated }

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/users/me')
  return response.data
}

export function login(username: string, password: string): void {
  setClientAuth(username, password)
  // Store credentials in localStorage for persistence
  localStorage.setItem('auth_username', username)
  localStorage.setItem('auth_password', password)
}

export function logout(): void {
  clearClientAuth()
  localStorage.removeItem('auth_username')
  localStorage.removeItem('auth_password')
}

export function restoreAuthFromStorage(): boolean {
  const username = localStorage.getItem('auth_username')
  const password = localStorage.getItem('auth_password')

  if (username && password) {
    setClientAuth(username, password)
    return true
  }

  return false
}
