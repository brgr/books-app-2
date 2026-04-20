import { ref, watch, toValue, isRef, type Ref } from 'vue'
import { cachedQuery } from '../cache/query'
import { cacheDel } from '../cache/store'

type MaybeRefOrGetter<T> = T | Ref<T> | (() => T)

export function useCachedQuery<T>(
  key: MaybeRefOrGetter<string>,
  fetcher: () => Promise<T>,
  options?: { enabled?: MaybeRefOrGetter<boolean> }
) {
  const data = ref<T | null>(null) as Ref<T | null>
  const isStale = ref(false)
  const error = ref<unknown>(null)

  let generation = 0
  let currentPromise: Promise<void> = Promise.resolve()

  function execute() {
    const currentKey = toValue(key)
    if (!currentKey) return

    const enabled = options?.enabled !== undefined ? toValue(options.enabled) : true
    if (!enabled) return

    const gen = ++generation
    error.value = null

    currentPromise = cachedQuery<T>({
      key: currentKey,
      fetcher,
      onData: (d, source) => {
        if (gen !== generation) return
        data.value = d
        isStale.value = source === 'cache'
      },
      onError: (err) => {
        if (gen !== generation) return
        error.value = err
      },
    })
  }

  async function refresh() {
    execute()
    await currentPromise
  }

  async function invalidate() {
    const currentKey = toValue(key)
    await cacheDel(currentKey)
    execute()
    await currentPromise
  }

  if (isRef(key) || typeof key === 'function') {
    watch(() => toValue(key), () => execute(), { immediate: true })
  } else {
    execute()
  }

  if (options?.enabled !== undefined && (isRef(options.enabled) || typeof options.enabled === 'function')) {
    watch(() => toValue(options.enabled!), (val) => {
      if (val) execute()
    })
  }

  return { data, isStale, error, refresh, invalidate }
}
