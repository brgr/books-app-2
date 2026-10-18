import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const reservations = [];

async function selectPort(override) {
  const server = createServer();

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(Number(override ?? 0), "127.0.0.1", resolve);
  });
  reservations.push(server);

  return String(server.address().port);
}

const env = { ...process.env };
try {
  // Hold both sockets until selection finishes so the ports are distinct.
  const keys = ["E2E_BACKEND_PORT", "E2E_FRONTEND_PORT"];
  const explicit = keys.filter((key) => env[key] !== undefined);
  const automatic = keys.filter((key) => env[key] === undefined);

  for (const key of [...explicit, ...automatic]) {
    env[key] = await selectPort(env[key]);
  }
} finally {
  await Promise.all(
    reservations.map(
      (server) => new Promise((resolve) => server.close(resolve)),
    ),
  );
}

console.log(
  `E2E ports: backend ${env.E2E_BACKEND_PORT}, frontend ${env.E2E_FRONTEND_PORT}`,
);

const databaseDir = mkdtempSync(join(tmpdir(), "books-e2e-"));
env.E2E_DB_FILE = join(databaseDir, "books-e2e.db");

try {
  const result = spawnSync(
    process.execPath,
    [
      fileURLToPath(import.meta.resolve("@playwright/test/cli")),
      "test",
      ...process.argv.slice(2),
    ],
    { env, stdio: "inherit" },
  );

  if (result.error) throw result.error;

  process.exitCode = result.status ?? 1;
} finally {
  rmSync(databaseDir, { recursive: true, force: true });
}
