import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import {
  BACKEND_CWD,
  DEV_PASSWORD,
  DEV_USERNAME,
  E2E_DB_FILE,
  E2E_DB_URL,
  FIXTURE,
} from "./config";

const backendEnv = { ...process.env, DATABASE_URL: E2E_DB_URL };

function backend(args: string[]): void {
  execFileSync("uv", ["run", ...args], {
    cwd: BACKEND_CWD,
    env: backendEnv,
    stdio: "inherit",
  });
}

/**
 * Reset the e2e DB and seed the sample Reading List fixture as
 * the deterministic baseline.
 *
 * Runs once before the e2e servers start.
 */
// noinspection JSUnusedGlobalSymbols -- consumed by the Playwright runner
export default function globalSetup(): void {
  for (const suffix of ["", "-wal", "-shm"]) {
    rmSync(`${BACKEND_CWD}/${E2E_DB_FILE}${suffix}`, { force: true });
  }
  backend(["alembic", "upgrade", "head"]);
  backend([
    "python",
    "manage.py",
    "create-superuser",
    "--username",
    DEV_USERNAME,
    "--password",
    DEV_PASSWORD,
  ]);
  backend([
    "python",
    "manage.py",
    "seed-reading-list",
    "--username",
    DEV_USERNAME,
    "--zip",
    FIXTURE,
  ]);
}
