import { type BrowserContext, request } from "@playwright/test";
import { BACKEND_URL, DEV_PASSWORD, DEV_USERNAME } from "./config";

/**
 * Log in through the real OAuth2 password flow and return a signed access token.
 *
 * The token is fetched from the running backend (the same one the browser would hit).
 */
export async function login(
  username = DEV_USERNAME,
  password = DEV_PASSWORD,
): Promise<string> {
  const context = await request.newContext();

  try {
    let options = { form: { username, password } };
    const response = await context.post(`${BACKEND_URL}/api/token`, options);

    if (!response.ok()) {
      throw new Error(
        `Login failed: ${response.status()} ${await response.text()}`,
      );
    }

    return (await response.json()).access_token;
  } finally {
    await context.dispose();
  }
}

/** Authenticate the browser as the seeded user by putting the access-token cookie. */
export async function authenticate(
  context: BrowserContext,
  username = DEV_USERNAME,
): Promise<void> {
  const token = await login(username);
  await context.addCookies([
    { name: "access_token", value: token, domain: "localhost", path: "/" },
  ]);
}
