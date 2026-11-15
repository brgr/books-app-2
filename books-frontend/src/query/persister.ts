import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { persistQueryClient } from "@tanstack/query-persist-client-core";
import type { QueryClient } from "@tanstack/vue-query";
import { type IDBPDatabase, openDB } from "idb";
import { CACHE_MAX_AGE } from "./client";

const DB_NAME = "books-cache";
const STORE_NAME = "cache";
// Bump when the shape of a cached API response changes: the upgrade drops everything persisted so far
const DB_VERSION = 5;

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (db.objectStoreNames.contains(STORE_NAME)) {
          db.deleteObjectStore(STORE_NAME);
        }

        db.createObjectStore(STORE_NAME);
      },
    });
  }

  return dbPromise;
}

export const persister = createAsyncStoragePersister({
  storage: {
    getItem: async (key) => (await getDb()).get(STORE_NAME, key),
    setItem: async (key, value) => (await getDb()).put(STORE_NAME, value, key),
    removeItem: async (key) => {
      await (await getDb()).delete(STORE_NAME, key);
    },
  },
});

let restoring: Promise<void> = Promise.resolve();

/**
 * Restores the persisted cache into the client, then keeps saving the client's changes. Pass as VueQueryPlugin's
 * `clientPersister`.
 */
export function persistCache(client: QueryClient): [() => void, Promise<void>] {
  const [unsubscribe, restored] = persistQueryClient({ queryClient: client, persister, maxAge: CACHE_MAX_AGE });
  // A failed restore has already discarded the persisted cache, so there is nothing left to wait for
  restoring = restored.catch(() => undefined);
  return [unsubscribe, restored];
}

/** Resolves once the persisted cache is restored, even when restoring fails, or right away when nothing restores */
export function cacheRestored(): Promise<void> {
  return restoring;
}
