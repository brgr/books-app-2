import { computed, inject, onBeforeUnmount, provide, ref, shallowRef, type InjectionKey, type Ref } from "vue";

/** What a shelf reports back to the page, so the page can tell when everything it shows is empty. */
export interface ShelfState {
  /** True once the shelf's first page has resolved at least once. */
  loaded: boolean;
  /** How many books the shelf actually renders (after the page's search filter). */
  count: number;
}

/** State a library page shares with every shelf it renders. */
export interface LibraryPageContext {
  /** The one search box driving all shelves on the page. */
  searchQuery: Ref<string>;
  /** Bumped when the page mutates the library (e.g. a book was added); shelves reload off it. */
  refreshToken: Ref<number>;
  registerShelf: (state: Ref<ShelfState>) => void;
}

const libraryPageKey = Symbol("library-page") as InjectionKey<LibraryPageContext>;

/**
 * Provides the page-level state that BookShelf components inject. Call from a library page
 * (a tab) that renders one or more `<BookShelf>`; it returns the page's own view of those
 * shelves collectively.
 */
export function provideLibraryPage(state: Pick<LibraryPageContext, "searchQuery">) {
  // Shelves come and go with the page's own v-ifs, so the registry is rebuilt by reassignment
  // rather than mutated: a shallowRef keeps the reported state refs intact instead of unwrapping them.
  const registered = shallowRef<Ref<ShelfState>[]>([]);
  const refreshToken = ref(0);

  function registerShelf(shelfState: Ref<ShelfState>) {
    registered.value = [...registered.value, shelfState];
    // Runs in the registering shelf's scope, so a shelf drops out of the registry as it unmounts
    onBeforeUnmount(() => {
      registered.value = registered.value.filter((candidate) => candidate !== shelfState);
    });
  }

  provide(libraryPageKey, { ...state, refreshToken, registerShelf });

  return {
    /** Every shelf on the page has loaded and come back with nothing to show. */
    allShelvesEmpty: computed(
      () =>
        registered.value.length > 0 && registered.value.every((shelf) => shelf.value.loaded && shelf.value.count === 0),
    ),
    /** Reloads every shelf on the page. */
    refreshShelves: () => {
      refreshToken.value += 1;
    },
  };
}

export function useLibraryPage(): LibraryPageContext {
  const context = inject(libraryPageKey);
  if (!context) throw new Error("useLibraryPage() requires an ancestor that calls provideLibraryPage()");
  return context;
}
