<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  CardActionEvent,
  PantryClientCardState,
  PantryStatusCard as PantryStatusCardType,
} from '../../types/chat'

const props = defineProps<{
  card: PantryStatusCardType
  disabled: boolean
}>()

const emit = defineEmits<{
  action: [action: CardActionEvent]
  stateChange: [state: PantryClientCardState]
}>()

const flashMode = ref(false)
const activeIndex = ref(0)
const checkedItems = ref<Record<string, boolean>>({})

function buildCheckedState() {
  return Object.fromEntries(
    props.card.checklist.map((item) => [item.id, item.status === 'ready']),
  ) as Record<string, boolean>
}

const completion = computed(() => {
  const total = props.card.checklist.length
  if (!total) {
    return 0
  }

  const checkedCount = Object.values(checkedItems.value).filter(Boolean).length
  return Math.round((checkedCount / total) * 100)
})

const activeFlashItem = computed(() => props.card.checklist[activeIndex.value] ?? null)
const readyIngredientIds = computed(() =>
  props.card.checklist.filter((item) => checkedItems.value[item.id]).map((item) => item.id),
)

function isReady(itemId: string) {
  return Boolean(checkedItems.value[itemId])
}

function toggleItem(itemId: string) {
  checkedItems.value[itemId] = !checkedItems.value[itemId]
}

function moveFlash(offset: number) {
  const nextIndex = activeIndex.value + offset

  if (nextIndex < 0 || nextIndex >= props.card.checklist.length) {
    return
  }

  activeIndex.value = nextIndex
}

watch(
  () => props.card.checklist.map((item) => `${item.id}:${item.status}`).join('|'),
  () => {
    checkedItems.value = buildCheckedState()
    activeIndex.value = 0
    flashMode.value = false
  },
  { immediate: true },
)

watch(
  [readyIngredientIds, flashMode, () => activeFlashItem.value?.id],
  () => {
    emit('stateChange', {
      readyIngredientIds: readyIngredientIds.value,
      focusedIngredientId: flashMode.value ? (activeFlashItem.value?.id ?? null) : null,
      flashMode: flashMode.value,
    })
  },
  { immediate: true },
)
</script>

<template>
  <section class="card-shell" :class="{ 'is-disabled': disabled }" :aria-disabled="disabled">
    <div class="card-head">
      <h3>{{ card.title }}</h3>
      <strong>{{ completion }}%</strong>
    </div>

    <div class="progress-track">
      <div class="progress-bar" :style="{ width: `${completion}%` }"></div>
    </div>

    <div class="mode-switch">
      <button type="button" :class="{ active: !flashMode }" @click="flashMode = false">列表</button>
      <button type="button" :class="{ active: flashMode }" @click="flashMode = true">闪卡</button>
    </div>

    <div v-if="!flashMode" class="checklist">
      <article v-for="item in card.checklist" :key="item.id" class="check-item">
        <label class="check-main">
          <div class="checkbox-wrap">
            <input :checked="isReady(item.id)" type="checkbox" @change="toggleItem(item.id)" />
            <div>
              <strong>{{ item.ingredient }}</strong>
              <small>{{ item.amount }}</small>
            </div>
          </div>
          <span :class="{ ready: isReady(item.id), pending: !isReady(item.id) }">
            {{ isReady(item.id) ? '已齐' : '未齐' }}
          </span>
        </label>
        <p>{{ item.note }}</p>
      </article>
    </div>

    <div v-else-if="activeFlashItem" class="flash-shell">
      <article class="flash-card">
        <span class="flash-status" :class="{ ready: isReady(activeFlashItem.id), pending: !isReady(activeFlashItem.id) }">
          {{ isReady(activeFlashItem.id) ? '已齐' : '未齐' }}
        </span>
        <strong>{{ activeFlashItem.ingredient }}</strong>
        <small>{{ activeFlashItem.amount }}</small>
        <p>{{ activeFlashItem.note }}</p>
      </article>

      <div class="flash-actions">
        <button type="button" :disabled="activeIndex === 0" @click="moveFlash(-1)">上一个</button>
        <button type="button" @click="toggleItem(activeFlashItem.id)">
          {{ isReady(activeFlashItem.id) ? '设为未齐' : '标记已齐' }}
        </button>
        <button
          type="button"
          :disabled="activeIndex === card.checklist.length - 1"
          @click="moveFlash(1)"
        >
          下一个
        </button>
      </div>
    </div>

    <div class="action-row">
      <button
        v-for="action in card.actions"
        :key="action.id"
        type="button"
        class="primary-button"
        @click="emit('action', { actionType: action.actionType, payload: action.payload })"
      >
        {{ action.label }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.card-shell {
  min-width: min(100%, 32rem);
  padding: 1rem;
  border: 1px solid rgba(47, 93, 80, 0.16);
  border-radius: 1.35rem;
  background: rgba(255, 253, 249, 0.98);
}

.card-shell.is-disabled {
  pointer-events: none;
  opacity: 0.6;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.card-head h3 {
  margin: 0;
  font-size: 1.1rem;
}

.card-head strong,
.check-main small,
.check-item p,
.flash-card small,
.flash-card p {
  color: var(--color-text-soft);
}

.progress-track {
  height: 0.5rem;
  margin-top: 0.95rem;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.1);
}

.progress-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-accent), rgba(47, 93, 80, 0.55));
}

.mode-switch {
  display: inline-flex;
  gap: 0.35rem;
  margin-top: 0.95rem;
  padding: 0.28rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
}

.mode-switch button {
  min-width: 4.3rem;
  padding: 0.45rem 0.78rem;
  border-radius: 999px;
  color: var(--color-text-soft);
  cursor: pointer;
}

.mode-switch button.active {
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-accent);
}

.checklist {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.check-item,
.flash-card {
  padding: 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.66);
}

.check-main {
  display: flex;
  justify-content: space-between;
  gap: 0.7rem;
  align-items: center;
  cursor: pointer;
}

.checkbox-wrap {
  display: flex;
  gap: 0.7rem;
  align-items: flex-start;
}

.checkbox-wrap input {
  margin-top: 0.15rem;
  accent-color: var(--color-accent);
}

.check-main span,
.flash-status {
  flex: 0 0 auto;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  font-size: 0.76rem;
}

.check-main span.ready,
.flash-status.ready {
  background: rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
}

.check-main span.pending,
.flash-status.pending {
  background: rgba(229, 143, 91, 0.12);
  color: #a05522;
}

.check-item p,
.flash-card p,
.flash-card small {
  margin: 0.45rem 0 0;
  line-height: 1.65;
}

.flash-shell {
  margin-top: 1rem;
}

.flash-card {
  display: grid;
  gap: 0.65rem;
}

.flash-card strong {
  font-size: 1.12rem;
}

.flash-actions,
.action-row {
  display: flex;
  gap: 0.65rem;
  margin-top: 0.85rem;
}

.flash-actions button,
.action-row button {
  flex: 1;
  min-height: 2.75rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 0.95rem;
  background: rgba(255, 255, 255, 0.74);
  color: var(--color-accent);
  cursor: pointer;
}

.flash-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
}

@media (max-width: 640px) {
  .flash-actions {
    flex-direction: column;
  }
}
</style>
