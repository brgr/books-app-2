import { apiClient, endSession, isAuthError, isAuthenticated, setAuthenticated } from "./client";
import type { User } from "./types";

export { isAuthenticated };

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("/users/me");
  return response.data;
}

export async function login(username: string, password: string): Promise<void> {
  const payload = new URLSearchParams();
  payload.append("username", username);
  payload.append("password", password);

  // Server sets HttpOnly cookies on successful login
  await apiClient.post("/token", payload, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  setAuthenticated(true);
}

export async function logout(): Promise<void> {
  try {
    // Server clears HttpOnly cookies
    await apiClient.post("/auth/logout");
  } finally {
    await endSession();
  }
}

export async function checkAuthStatus(): Promise<boolean> {
  /**
   * Verify authentication by calling /users/me.
   * If the HttpOnly cookie is valid, this will succeed.
   * Used on app startup to restore authentication state.
   */
  try {
    await apiClient.get("/users/me");
    setAuthenticated(true);
    return true;
  } catch (error) {
    // A rejected session was already ended by the auth interceptor. Any other failure, such as being offline, says
    // nothing about the session, so it is kept along with the cached data until the server rejects it.
    const valid = !isAuthError(error);
    setAuthenticated(valid);
    return valid;
  }
}
