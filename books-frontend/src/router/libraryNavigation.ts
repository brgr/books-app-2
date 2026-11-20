import { nextTick } from "vue";
import type { RouteLocationNormalized, Router, RouterScrollBehavior } from "vue-router";
import { pageScroller } from "../utils/pageScroller";

/**
 * Returns an identifier for the library tab, such as "/shelves/finished".
 *
 * We use that identifier in App.vue as the view's key and here to remember the tab's scroll position.
 * We give / and /shelves/to-read the same key because both URLs show the To Read tab.
 */
export function libraryPageKey(
  route: Pick<RouteLocationNormalized, "params" | "path"> & { name?: string | symbol | null },
): string | null {
  if (route.name === "books" || (route.name === "shelf" && route.params.shelf === "to-read")) {
    return "/shelves/to-read";
  }
  if (route.name === "shelf" || route.name === "custom-shelf" || route.name === "custom-shelves") {
    return route.path;
  }

  return null;
}

/** Validate the shelf URL from the `from` query parameter, falling back to To Read if it is missing or invalid. */
export function libraryOrigin(router: Router, value: unknown): string {
  if (typeof value === "string" && value.startsWith("/") && !value.startsWith("//")) {
    const resolved = router.resolve(value);

    if (libraryPageKey(resolved)) {
      return resolved.fullPath;
    }
  }

  return "/";
}

/** Identifies the history entry the browser is on, so Back and Forward can return to its scroll position. */
function historyEntryKey(route: RouteLocationNormalized): string {
  return `${window.history.state?.position ?? ""}:${route.fullPath}`;
}

export function createLibraryNavigation() {
  const tabPositions = new Map<string, number>();
  const entryPositions = new Map<string, number>();
  let currentEntry: string | null = null;

  const scrollBehavior: RouterScrollBehavior = async (to, _from, savedPosition) => {
    // The returning view renders every page the user had loaded straight from the query cache.
    // We wait for Vue to put it in the document before restoring its scroll position.
    await nextTick();

    const key = libraryPageKey(to);
    // vue-router passes a saved position only for Back/Forward, but measures the window, which never scrolls.
    // So we use the position we saved for the history entry, or the tab's last position for other visits.
    const top =
      (savedPosition ? entryPositions.get(historyEntryKey(to)) : undefined) ??
      (key ? tabPositions.get(key) : undefined) ??
      0;

    pageScroller()?.scrollTo({ top });
  };

  function install(router: Router) {
    router.beforeResolve((to, from) => {
      // We store the shelf's URL in the `from` query parameter and carry it through the detail and edit pages.
      // Keep it in the URL so the back link still knows which shelf to open after a reload or when someone copies the link.
      if ((to.name === "book-detail" || to.name === "book-edit") && to.query.from === undefined) {
        const origin = libraryPageKey(from)
          ? from.fullPath
          : from.name === "book-detail" || from.name === "book-edit"
            ? from.query.from
            : undefined;

        if (typeof origin === "string") {
          return { ...to, query: { ...to.query, from: libraryOrigin(router, origin) } };
        }
      }
    });

    router.afterEach((to, from, failure) => {
      if (failure) {
        return;
      }

      if (to.name === "login") {
        // Clear saved positions so the next session starts at the top of each page.
        tabPositions.clear();
        entryPositions.clear();
      } else {
        // Save the departing page's position before Vue replaces its view.
        const top = pageScroller()?.scrollTop ?? 0;
        const key = libraryPageKey(from);

        if (currentEntry) {
          entryPositions.set(currentEntry, top);
        }
        if (key) {
          tabPositions.set(key, top);
        }
      }

      currentEntry = historyEntryKey(to);
    });
  }

  return { scrollBehavior, install };
}
