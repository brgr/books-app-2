import axios from "axios";
import type { Router } from "vue-router";
import { queryClient } from "../query/client";
import { cacheRestored, persister } from "../query/persister";

// The backend origin. Empty means same-origin.
// In dev, the Vite proxy (vite.config.ts) forwards /api and /uploads to the backend, which keeps covers and cookies on
// one origin.
export const BACKEND_ORIGIN = import.meta.env.VITE_API_URL || "";

export const API_BASE_URL = `${BACKEND_ORIGIN}/api`;

export function getMediaUrl(path: string | null | undefined): string | undefined {
  if (!path) {
    return undefined;
  }

  // Absolute (remote) and local object URLs (a not-yet-uploaded cover) are already usable as-is.
  if (path.startsWith("http") || path.startsWith("blob:")) {
    return path;
  }

  return `${BACKEND_ORIGIN}${path}`;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  // Send cookies with every request (HttpOnly auth cookies)
  withCredentials: true,
  responseType: "json",
  transitional: { silentJSONParsing: false },
});

// Track authentication state (verified via /users/me endpoint)
// We store it so a reload while offline can tell whether this browser had a session
const AUTHENTICATED_KEY = "authenticated";
let authenticated = localStorage.getItem(AUTHENTICATED_KEY) === "true";

export function setAuthenticated(value: boolean) {
  authenticated = value;

  if (value) {
    localStorage.setItem(AUTHENTICATED_KEY, "true");
  } else {
    localStorage.removeItem(AUTHENTICATED_KEY);
  }
}

export function isAuthenticated(): boolean {
  return authenticated;
}

/**
 * Ends the session locally: drops the authenticated flag and the cached API data with it.
 */
export async function endSession(): Promise<void> {
  setAuthenticated(false);
  // A restore that finished after the clear would bring back the ended session's data and save it again
  await cacheRestored();
  queryClient.clear();
  await persister.removeClient();
}

export function isAuthError(error: unknown): boolean {
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  return status === 401 || status === 403;
}

async function tryRefreshAccessToken(): Promise<boolean> {
  try {
    // Refresh endpoint reads refresh token from HttpOnly cookie
    await apiClient.post("/auth/refresh");
    return true;
  } catch {
    return false;
  }
}

// Setup response interceptor to handle authentication errors
export function setupAuthInterceptor(router: Router) {
  apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      // Check if error is due to authentication failure
      if (isAuthError(error)) {
        const originalRequest = error.config as typeof error.config & { _retry?: boolean };

        // Don't retry refresh or logout endpoints to avoid loops
        const isAuthEndpoint = originalRequest?.url?.includes("/auth/");

        if (originalRequest && !originalRequest._retry && !isAuthEndpoint) {
          originalRequest._retry = true;
          const refreshed = await tryRefreshAccessToken();
          if (refreshed) {
            // Retry the original request (cookies are sent automatically)
            return apiClient(originalRequest);
          }
        }

        // Clear authentication state (and cached data) after refresh failure
        await endSession();

        // Redirect to login page if not already there
        if (router.currentRoute.value.name !== "login") {
          router.push({ name: "login", query: { redirect: router.currentRoute.value.fullPath } });
        }
      }

      return Promise.reject(error);
    },
  );
}
