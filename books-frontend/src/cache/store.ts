import { openDB, type IDBPDatabase } from 'idb'

interface CacheEntry<T = unknown> {
  key: string
  data: T
  timestamp: number
}

const DB_NAME = 'books-cache'
const STORE_NAME = 'cache'
const DB_VERSION = 1

let dbPromise: Promise<IDBPDatabase> | null = null

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'key' })
        }
      },
    })
  }
  return dbPromise
}

export async function cacheGet<T>(key: string): Promise<CacheEntry<T> | undefined> {
  const db = await getDb()
  return db.get(STORE_NAME, key)
}

export async function cacheSet<T>(key: string, data: T): Promise<void> {
  const db = await getDb()
  const entry: CacheEntry<T> = { key, data, timestamp: Date.now() }
  await db.put(STORE_NAME, entry)
}

export async function cacheDel(key: string): Promise<void> {
  const db = await getDb()
  await db.delete(STORE_NAME, key)
}

export async function cacheInvalidateByPrefix(prefix: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  const store = tx.objectStore(STORE_NAME)
  let cursor = await store.openCursor()
  while (cursor) {
    if ((cursor.key as string).startsWith(prefix)) {
      await cursor.delete()
    }
    cursor = await cursor.continue()
  }
  await tx.done
}

export async function cacheClear(): Promise<void> {
  const db = await getDb()
  await db.clear(STORE_NAME)
}
