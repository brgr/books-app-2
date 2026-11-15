import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { type IDBPDatabase, openDB } from "idb";

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
