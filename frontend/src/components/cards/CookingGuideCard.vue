<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  CookingGuideCard as CookingGuideCardType,
  TimerRequest,
} from '../../types/chat'

const props = defineProps<{
  card: CookingGuideCardType
  autoStartTimer: boolean
}>()

const emit = defineEmits<{
  startTimer: [payload: TimerRequest]
}>()

const flashMode = ref(false)
const safeSteps = computed(() => props.card.steps ?? [])
const activeIndex = ref(Math.max(props.card.currentStep - 1, 0))
const activeStep = computed(() => safeSteps.value[activeIndex.value] ?? null)

function moveStep(offset: number) {
  const nextIndex = activeIndex.value + offset

  if (nextIndex < 0 || nextIndex >= safeSteps.value.length) {
    return
  }

  activeIndex.value = nextIndex
}

function requestTimer() {
  if (!activeStep.value?.timerSeconds) {
    return
  }

  emit('startTimer', {
    stepId: activeStep.value.id,
    label: activeStep.value.title,
    seconds: activeStep.value.timerSeconds,
  })
}

watch(
  [() => props.autoStartTimer, () => activeStep.value?.id],
  ([autoStartTimer, activeStepId], previousValue) => {
    if (!autoStartTimer || !activeStepId || !activeStep.value?.timerSeconds) {
      return
    }

    const [previousAutoStartTimer, previousStepId] = previousValue ?? []
    if (autoStartTimer === previousAutoStartTimer && activeStepId === previousStepId) {
      return
    }

    requestTimer()
  },
  { immediate: true },
)
</script>

<template>
  <section class="card-shell cooking-guide-card">
    <div class="card-head">
      <h3>{{ card.title }}</h3>
      <span>步骤 {{ activeIndex + 1 }}/{{ card.totalSteps }}</span>
    </div>
    <div class="mode-switch">
      <button type="button" :class="{ active: !flashMode }" @click="flashMode = false">列表</button>
      <button type="button" :class="{ active: flashMode }" @click="flashMode = true">闪卡</button>
    </div>

    <div v-if="!flashMode" class="step-list">
      <article
        v-for="(step, index) in safeSteps"
        :key="step.id"
        class="step-item"
        :class="{ active: index === activeIndex, done: step.status === 'done' }"
        @click="activeIndex = index"
      >
        <div class="step-index">{{ index + 1 }}</div>
        <div class="step-content">
          <div class="step-head">
            <strong>{{ step.title }}</strong>
            <span>{{ step.duration }}</span>
          </div>
          <p>{{ step.detail }}</p>
          <small v-if="step.notes">{{ step.notes }}</small>
        </div>
      </article>
    </div>

    <div v-else-if="activeStep" class="flash-shell">
      <article class="flash-card">
        <div class="flash-top">
          <strong>{{ activeStep.title }}</strong>
          <button
            v-if="activeStep.timerSeconds"
            type="button"
            class="timer-inline-button"
            @click="requestTimer"
          >
            <span>⏱</span>
            <span>{{ activeStep.duration }}</span>
          </button>
          <span v-else class="flash-duration">{{ activeStep.duration }}</span>
        </div>
        <p>{{ activeStep.detail }}</p>
        <small v-if="activeStep.notes">{{ activeStep.notes }}</small>
      </article>
    </div>

    <div class="nav-row">
      <button type="button" :disabled="activeIndex === 0" @click="moveStep(-1)">上一步</button>
      <button
        type="button"
        :disabled="activeIndex === safeSteps.length - 1"
        @click="moveStep(1)"
      >
        下一步
      </button>
    </div>
  </section>
</template>

<style scoped>
.card-shell {
  min-width: min(100%, 34rem);
  padding: 1rem;
  border: 1px solid rgba(47, 93, 80, 0.16);
  border-radius: 1.35rem;
  background: rgba(255, 253, 249, 0.98);
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

.card-head span,
.flash-duration {
  flex: 0 0 auto;
  padding: 0.34rem 0.65rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 0.78rem;
}

.step-item p,
.step-item small,
.flash-card p,
.flash-card small {
  color: var(--color-text-soft);
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

.step-list {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.step-item,
.flash-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
  padding: 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.72);
}

.step-item {
  cursor: pointer;
}

.step-item.active,
.flash-card {
  border-color: rgba(229, 143, 91, 0.28);
  background: linear-gradient(135deg, rgba(255, 247, 238, 0.98), rgba(255, 252, 246, 0.96));
}

.step-item.done {
  opacity: 0.76;
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.1);
  color: var(--color-accent);
  font-size: 0.82rem;
  font-weight: 700;
}

.step-content {
  min-width: 0;
}

.step-head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.step-head span {
  flex: 0 0 auto;
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.step-item p,
.step-item small,
.flash-card p,
.flash-card small {
  margin: 0.4rem 0 0;
  line-height: 1.65;
}

.flash-shell {
  margin-top: 1rem;
}

.flash-card {
  grid-template-columns: 1fr;
}

.flash-card strong {
  font-size: 1.14rem;
}

.flash-top {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: flex-start;
}

.timer-inline-button {
  display: inline-flex;
  gap: 0.3rem;
  align-items: center;
  min-height: 2rem;
  padding: 0 0.7rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--color-accent);
  font-size: 0.8rem;
  cursor: pointer;
}

.nav-row {
  display: flex;
  gap: 0.65rem;
  margin-top: 0.95rem;
}

.nav-row button {
  flex: 1;
  min-height: 2.75rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 0.95rem;
  background: rgba(255, 255, 255, 0.74);
  color: var(--color-accent);
  cursor: pointer;
}

.nav-row button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 640px) {
  .nav-row {
    flex-direction: column;
  }
}
</style>
