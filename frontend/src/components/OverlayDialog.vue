<script setup lang="ts">
defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) {
    emit('close')
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="isOpen"
        class="overlay-shell"
        role="dialog"
        aria-modal="true"
        @click="onBackdropClick"
      >
        <div class="overlay-card">
          <button class="overlay-close" type="button" aria-label="关闭弹层" @click="emit('close')">
            ×
          </button>
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay-shell {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(18, 26, 24, 0.38);
  backdrop-filter: blur(10px);
}

.overlay-card {
  position: relative;
  width: min(100%, 52rem);
  max-height: min(88vh, 56rem);
  overflow-y: auto;
  padding: 1.5rem;
  border: 1px solid rgba(47, 93, 80, 0.16);
  border-radius: 1.6rem;
  background:
    linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(248, 242, 232, 0.98)),
    var(--color-surface-strong);
  box-shadow: 0 28px 72px rgba(20, 28, 26, 0.24);
}

.overlay-close {
  position: sticky;
  top: 0;
  float: right;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 1.2rem;
  cursor: pointer;
}

.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 180ms ease;
}

.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .overlay-shell {
    padding: 1rem;
  }

  .overlay-card {
    width: 100%;
    padding: 1.1rem;
    border-radius: 1.3rem;
  }
}
</style>
