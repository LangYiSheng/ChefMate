<script setup lang="ts">
defineProps<{
  isOpen: boolean
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) {
    emit('cancel')
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="isOpen"
        class="modal-shell"
        role="dialog"
        aria-modal="true"
        @click="onBackdropClick"
      >
        <div class="modal-card">
          <div class="modal-copy">
            <h3>{{ title }}</h3>
            <p v-if="message">{{ message }}</p>
          </div>

          <div class="modal-actions">
            <button
              v-if="cancelLabel"
              type="button"
              class="secondary-button"
              @click="emit('cancel')"
            >
              {{ cancelLabel }}
            </button>
            <button type="button" class="primary-button" @click="emit('confirm')">
              {{ confirmLabel || '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-shell {
  position: fixed;
  inset: 0;
  z-index: 70;
  display: grid;
  place-items: center;
  padding: 1.25rem;
  background: rgba(18, 26, 24, 0.42);
  backdrop-filter: blur(10px);
}

.modal-card {
  width: min(100%, 25rem);
  padding: 1.2rem;
  border: 1px solid rgba(47, 93, 80, 0.16);
  border-radius: 1.35rem;
  background:
    linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(248, 242, 232, 0.98)),
    var(--color-surface-strong);
  box-shadow: 0 24px 56px rgba(20, 28, 26, 0.24);
}

.modal-copy h3 {
  margin: 0;
  font-size: 1.18rem;
}

.modal-copy p {
  margin: 0.55rem 0 0;
  color: var(--color-text-soft);
  line-height: 1.65;
}

.modal-actions {
  display: flex;
  gap: 0.65rem;
  margin-top: 1rem;
}

.modal-actions button {
  flex: 1;
  min-height: 2.75rem;
  border-radius: 0.95rem;
  cursor: pointer;
}

.secondary-button {
  border: 1px solid rgba(47, 93, 80, 0.14);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-accent);
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
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
  .modal-actions {
    flex-direction: column;
  }
}
</style>
