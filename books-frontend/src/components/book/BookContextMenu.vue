<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { MenuAnchor } from "../../composables/useContextMenu";
import { swallowNextClick } from "../../utils/click";

const props = defineProps<{
  x: number;
  y: number;
  /**
   * The book a long press picked up. The page then dims, the `preview` slot shows the book lifted in place, and the
   * menu pops up below the book, or above it when there's no room below, instead of at `x`/`y`, where the finger would
   * cover it.
   */
  anchor?: MenuAnchor | null;
  canRemoveFromShelf?: boolean;
  canReorder?: boolean;
}>();

type MoveEdge = "top" | "bottom";

const emit = defineEmits<{
  view: [];
  move: [edge: MoveEdge];
  removeFromShelf: [];
  close: [];
}>();

const menuEl = ref<HTMLElement | null>(null);
const pos = ref({ top: props.y, left: props.x });
const placement = ref<"below" | "above">("below");

/** Space between the menu and the viewport's edges. */
const margin = 8;
/** Space between the menu and the book it belongs to, which is shown slightly enlarged. */
const anchorGap = 12;
/** How far past the screen's top and bottom edges the dimming reaches, to cover the page under Safari's bars. */
const dimOverhang = 200;

const dim = ref({ top: 0, height: 0 });

/** Measures the part of the page to dim: what is on screen, plus what Safari shows under its bars. */
function measureDim() {
  const top = Math.max(0, window.scrollY - dimOverhang);
  const bottom = Math.min(document.documentElement.scrollHeight, window.scrollY + window.innerHeight + dimOverhang);
  dim.value = { top, height: bottom - top };
}

function place() {
  const el = menuEl.value;
  if (!el) {
    return;
  }

  const { width, height } = el.getBoundingClientRect();
  const maxLeft = window.innerWidth - width - margin;
  const maxTop = window.innerHeight - height - margin;
  let left = props.x;
  let top = props.y;

  if (props.anchor) {
    const below = props.anchor.top + props.anchor.height + anchorGap;
    const above = props.anchor.top - anchorGap - height;
    // Below the book, unless there is room only above it
    placement.value = below <= maxTop || above < margin ? "below" : "above";
    left = props.anchor.left;
    top = placement.value === "below" ? below : above;
  }

  pos.value = { top: Math.max(margin, Math.min(top, maxTop)), left: Math.max(margin, Math.min(left, maxLeft)) };
}

function onBackdropPointerDown(e: PointerEvent) {
  // A right-click closes the menu through `contextmenu`
  if (e.button !== 0) {
    return;
  }

  emit("close");
  swallowNextClick();
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") {
    emit("close");
  }
}

watch(
  () => [props.x, props.y, props.anchor],
  () => {
    measureDim();
    void nextTick(place);
  },
);

onMounted(() => {
  measureDim();
  nextTick(place);
  document.addEventListener("keydown", onKey);
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKey);
});
</script>

<template>
  <teleport to="body">
    <div v-if="anchor" class="ctx-dim" :style="{ top: dim.top + 'px', height: dim.height + 'px' }" />
    <div class="ctx-backdrop" @pointerdown.self="onBackdropPointerDown" @contextmenu.prevent="emit('close')">
      <div
        v-if="anchor"
        class="ctx-preview"
        :style="{
          top: anchor.top + 'px',
          left: anchor.left + 'px',
          width: anchor.width + 'px',
          height: anchor.height + 'px',
        }"
        aria-hidden="true"
        inert
      >
        <slot name="preview" />
      </div>
      <div
        ref="menuEl"
        class="ctx-menu"
        :class="{ 'ctx-menu-popped': anchor, 'ctx-menu-above': placement === 'above' }"
        role="menu"
        :style="{ top: pos.top + 'px', left: pos.left + 'px' }"
      >
        <button type="button" class="ctx-item" role="menuitem" @click="emit('view')">View Book</button>
        <button type="button" class="ctx-item" role="menuitem" :disabled="!canReorder" @click="emit('move', 'top')">
          Move to Top
        </button>
        <button type="button" class="ctx-item" role="menuitem" :disabled="!canReorder" @click="emit('move', 'bottom')">
          Move to Bottom
        </button>
        <button
          v-if="canRemoveFromShelf"
          type="button"
          class="ctx-item ctx-item-danger"
          role="menuitem"
          @click="emit('removeFromShelf')"
        >
          Remove from this shelf
        </button>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  /* A touch outside the menu only closes it: no scrolling or zooming the page behind, and no waiting for a double-tap */
  touch-action: none;
  /* The long press that opened the menu would otherwise go on to select its text */
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

/* Dims the page behind a book picked up by a long press. It is laid over the page rather than fixed to the screen:
   Safari draws the page under its status bar and toolbar, but cuts fixed elements off at their edges */
.ctx-dim {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.25);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  animation: ctx-fade 0.18s ease;
}

/* A copy of that book, lifted above the dimmed page where the book itself sits */
.ctx-preview {
  position: fixed;
  pointer-events: none;
  transform: scale(1.06);
  filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.35));
  animation: ctx-lift 0.18s ease;
}

.ctx-menu {
  position: fixed;
  min-width: 168px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
  padding: 6px 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Grow the menu out of the book's corner */
.ctx-menu-popped {
  transform-origin: top left;
  animation: ctx-pop 0.22s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}

.ctx-menu-popped.ctx-menu-above {
  transform-origin: bottom left;
}

@keyframes ctx-fade {
  from {
    opacity: 0;
  }
}

@keyframes ctx-lift {
  from {
    transform: scale(1);
    filter: none;
  }
}

@keyframes ctx-pop {
  from {
    transform: scale(0.6);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ctx-dim,
  .ctx-preview,
  .ctx-menu-popped {
    animation: none;
  }
}

.ctx-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 10px 12px;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.12s ease;
}

.ctx-item:hover,
.ctx-item:focus-visible {
  background: color-mix(in srgb, var(--color-primary) 16%, var(--color-bg-card));
  outline: none;
}

.ctx-item-danger {
  color: var(--color-danger, #c0392b);
}

.ctx-item:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
