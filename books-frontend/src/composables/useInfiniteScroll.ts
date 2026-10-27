import { watch, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, type Ref } from "vue";

/**
 * Wires an IntersectionObserver to `sentinelEl` so `onIntersect` fires as that
 * element scrolls into view. Bind the same ref to the sentinel's `ref` in the
 * template; the observer is (re)attached whenever the element changes and torn
 * down on unmount. Call `reobserve()` after new content renders to keep the
 * sentinel observed (e.g. once a fresh page has been appended).
 */
export function useInfiniteScroll(
  sentinelEl: Ref<HTMLElement | null>,
  onIntersect: () => void,
  rootMargin = "400px 0px",
) {
  let observer: IntersectionObserver | null = null;
  let isViewCurrentlyShown = true;

  function setup() {
    if (!isViewCurrentlyShown || observer || !sentinelEl.value) {
      return;
    }

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (isViewCurrentlyShown && entry.isIntersecting) {
            onIntersect();
          }
        }
      },
      { rootMargin },
    );

    observer.observe(sentinelEl.value);
  }

  function reobserve() {
    if (observer && sentinelEl.value) {
      observer.unobserve(sentinelEl.value);
      observer.observe(sentinelEl.value);
    }
  }

  watch(sentinelEl, () => {
    observer?.disconnect();
    observer = null;
    void nextTick(setup);
  });

  onMounted(() => void nextTick(setup));
  onActivated(() => {
    isViewCurrentlyShown = true;
    void nextTick(setup);
  });

  function stop() {
    isViewCurrentlyShown = false;
    observer?.disconnect();
    observer = null;
  }

  onDeactivated(stop);
  onBeforeUnmount(stop);

  return { reobserve };
}
