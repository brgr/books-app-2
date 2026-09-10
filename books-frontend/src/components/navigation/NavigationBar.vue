<script setup lang="ts">
import { computed, ref } from "vue";
import LibraryNavLink from "./LibraryNavLink.vue";
import BookIcon from "../icons/BookIcon.vue";
import OpenBookIcon from "../icons/OpenBookIcon.vue";
import BooksIcon from "../icons/BooksIcon.vue";
import StackedBooksIcon from "../icons/StackedBooksIcon.vue";
import { useRoute, useRouter } from "vue-router";
import { isAuthenticated, logout } from "../../api/auth";

const router = useRouter();
const route = useRoute();
const surface = computed(() => {
  if (route.name === "books") {
    return "to-read";
  }
  if (route.name === "custom-shelves" || route.name === "custom-shelf") {
    return "shelves";
  }
  if (route.name === "shelf") {
    return route.params.shelf === "abandoned" ? "shelves" : route.params.shelf;
  }
  return null;
});
const isLibraryPage = computed(() => Boolean(surface.value));
const showMenu = ref(isAuthenticated());
const isMenuOpen = ref(false);

async function handleLogout() {
  showMenu.value = false;
  isMenuOpen.value = false;
  await logout();
  router.push("/login");
}

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value;
}

function closeMenu() {
  isMenuOpen.value = false;
}
</script>

<template>
  <nav class="navbar">
    <div class="navbar-content">
      <div class="navbar-left">
        <router-link to="/" class="navbar-brand">
          <BookIcon class="navbar-icon" />
          BOOKS
        </router-link>

        <nav class="library-nav" :class="{ 'hide-on-mobile': !isLibraryPage }" aria-label="Library">
          <LibraryNavLink
            label="To Read"
            :active="surface === 'to-read'"
            :to="{ name: 'shelf', params: { shelf: 'to-read' } }"
          >
            <template #icon>
              <OpenBookIcon />
            </template>
          </LibraryNavLink>

          <LibraryNavLink
            label="Finished"
            :active="surface === 'finished'"
            :to="{ name: 'shelf', params: { shelf: 'finished' } }"
          >
            <template #icon>
              <BooksIcon />
            </template>
          </LibraryNavLink>

          <LibraryNavLink label="Shelves" :active="surface === 'shelves'" :to="{ name: 'custom-shelves' }">
            <template #icon>
              <StackedBooksIcon />
            </template>
          </LibraryNavLink>
        </nav>
      </div>

      <div class="navbar-right">
        <RouterLink :to="{ name: 'book-add' }" class="btn btn-primary btn-add">Add book</RouterLink>

        <div v-if="showMenu" class="navbar-user">
          <button
            class="menu-toggle"
            type="button"
            @click="toggleMenu"
            :aria-expanded="isMenuOpen"
            aria-label="Open user menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          <div v-if="isMenuOpen" class="menu-backdrop" @click="closeMenu"></div>
          <div v-if="isMenuOpen" class="menu-panel" role="menu">
            <router-link class="menu-item" role="menuitem" to="/settings" @click="closeMenu">Settings</router-link>
            <button class="menu-item" type="button" role="menuitem" @click="handleLogout">Logout</button>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<style scoped>
/* Mobile: a floating bottom bar within thumb reach. */
.library-nav {
  position: fixed;
  left: 50%;
  bottom: calc(14px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  width: min(92vw, 420px);
  display: flex;
  gap: 6px;
  padding: 6px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  box-shadow: var(--modal-shadow);
  z-index: 30;
}

.hide-on-mobile {
  display: none;
}

/* Desktop: the same links become inline tabs in the header. */
@media (min-width: 769px) {
  .library-nav {
    display: flex;
    position: static;
    transform: none;
    width: auto;
    justify-content: flex-start;
    gap: 4px;
    padding: 0;
    margin: 0;
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }
}

.navbar {
  background-color: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  overflow: visible;
  width: 100%;
  position: relative;
  z-index: 200;
}

.navbar-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  overflow: visible;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 1.125rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--color-text);
  text-decoration: none;
  text-transform: uppercase;
}

.navbar-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.navbar-user {
  display: flex;
  align-items: center;
  position: relative;
}

.btn-add {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-weight: 600;
}

.menu-toggle {
  background: none;
  border: none;
  width: 36px;
  height: 36px;
  padding: 6px;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  border-radius: var(--border-radius);
  transition: background-color 0.15s ease;
}

.menu-toggle:hover {
  background-color: var(--color-bg);
}

.menu-toggle span {
  display: block;
  width: 18px;
  height: 2px;
  background-color: var(--color-text);
  border-radius: 999px;
}

.menu-backdrop {
  position: fixed;
  inset: 0;
  background: transparent;
  z-index: 10;
}

.menu-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
  min-width: 160px;
  z-index: 11;
  padding: var(--spacing-xs);
}

.menu-item {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius);
  cursor: pointer;
  text-decoration: none;
  transition: background-color 0.15s ease;
}

.menu-item:hover {
  background-color: var(--color-bg);
}

@media (max-width: 768px) {
  .navbar-content {
    flex-wrap: nowrap;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }

  .navbar-left {
    flex: 0 1 auto;
    min-width: 0;
    gap: var(--spacing-sm);
  }

  .navbar-right {
    flex: 0 0 auto;
    gap: var(--spacing-sm);
  }

  .btn-add {
    font-size: 13px;
    padding: var(--spacing-xs) var(--spacing-sm);
    white-space: nowrap;
  }

  .menu-toggle {
    width: 32px;
    height: 32px;
    padding: 5px;
  }

  .menu-toggle span {
    width: 16px;
  }
}
</style>
