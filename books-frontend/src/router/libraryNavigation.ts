import { nextTick } from "vue";
import type { RouteLocationNormalized, Router, RouterScrollBehavior } from "vue-router";

/**
 * Returns an identifier for the library tab, such as "/shelves/finished".
 *
 * We use that identifier in App.vue to preserve the tab's view with KeepAlive and here to remember the tab's scroll position.
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

export function createLibraryNavigation() {
  const positions = new Map<string, { left: number; top: number }>();

  const scrollBehavior: RouterScrollBehavior = async (to, _from, savedPosition) => {
    // We use KeepAlive in App.vue to preserve library views, including all the pages the user has loaded.
    // We wait for Vue to put the returning view back in the document before restoring its scroll position.
    await nextTick();

    const key = libraryPageKey(to);

    // Use the browser's saved position for Back/Forward, or the tab's last position for other visits.
    return savedPosition ?? (key ? positions.get(key) : undefined) ?? { left: 0, top: 0 };
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
        // Clear saved positions so the next session starts at the top of each tab.
        positions.clear();
        return;
      }

      const key = libraryPageKey(from);

      if (key) {
        // Save the departing tab's position before Vue replaces its view.
        positions.set(key, { left: window.scrollX, top: window.scrollY });
      }
    });
  }

  return { scrollBehavior, install };
}
