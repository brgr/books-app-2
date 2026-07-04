<script setup lang="ts">
import {computed, ref, toRef} from 'vue'
import {useClampToggle} from '../../composables/useClampToggle'

const props = withDefaults(
  defineProps<{
    text: string
    lines?: number
    moreLabel?: string
    lessLabel?: string
  }>(),
  {
    lines: 3,
    moreLabel: 'Read more...',
    lessLabel: 'Read less',
  },
)

const textRef = ref<HTMLElement | null>(null)
const {expanded, showToggle, maxHeight, toggle} = useClampToggle(textRef, {
  lines: props.lines,
  source: toRef(props, 'text'),
})

const clamped = computed(() => showToggle.value && !expanded.value)
</script>

<template>
  <div class="collapsible-text">
    <p
      ref="textRef"
      class="collapsible-text__body"
      :class="{clamped}"
      :style="{maxHeight}"
    >
      {{ text }}
    </p>
    <button
      v-if="showToggle"
      type="button"
      class="collapsible-text__toggle"
      @click="toggle"
    >
      {{ expanded ? lessLabel : moreLabel }}
    </button>
  </div>
</template>

<style scoped>
.collapsible-text {
  position: relative;
}

.collapsible-text__body {
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow: hidden;
  position: relative;
  max-height: none;
  transition: max-height 240ms ease;
  will-change: max-height;
}

.collapsible-text__body.clamped {
  opacity: 1;
}

.collapsible-text__body.clamped::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1.8rem;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0),
    var(--color-bg)
  );
}

@supports (mask-image: linear-gradient(#000, transparent)) {
  .collapsible-text__body.clamped {
    mask-image: linear-gradient(180deg, #000 0%, #000 70%, transparent 100%);
    -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 70%, transparent 100%);
    mask-size: 100% 100%;
    -webkit-mask-size: 100% 100%;
    mask-repeat: no-repeat;
    -webkit-mask-repeat: no-repeat;
  }

  .collapsible-text__body.clamped::after {
    content: none;
  }
}

.collapsible-text__toggle {
  margin-top: var(--spacing-xs);
  padding: 0;
  border: none;
  background: none;
  color: var(--color-primary);
  font-size: 0.95rem;
  cursor: pointer;
}

.collapsible-text__toggle:hover {
  text-decoration: underline;
}
</style>
