// Shared identity of the throwaway e2e environment.

export const BACKEND_CWD = "../books-backend";
export const E2E_DB_FILE = "books-e2e.db";
export const E2E_DB_URL = `sqlite:///./${E2E_DB_FILE}`;

export const DEV_USERNAME = "dev";
export const DEV_PASSWORD = "devpassword";

export const FIXTURE = "fixtures/reading_list_sample.zip";

export const BACKEND_PORT = 8001;
export const FRONTEND_PORT = 5174;
export const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
export const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;
