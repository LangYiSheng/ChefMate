<script setup lang="ts">
import type { CookingGuideCard as CookingGuideCardType } from '../../types/chat'

defineProps<{
  card: CookingGuideCardType
}>()
</script>

<template>
  <section class="card-shell">
    <div class="card-head">
      <div>
        <p>烹饪指导卡</p>
        <h3>{{ card.title }}</h3>
      </div>
      <span>步骤 {{ card.currentStep }}/{{ card.totalSteps }}</span>
    </div>

    <p class="summary">{{ card.summary }}</p>

    <div class="timer-row">
      <article v-for="timer in card.timers" :key="timer.label" class="timer-item">
        <strong>{{ timer.duration }}</strong>
        <small>{{ timer.label }}</small>
      </article>
    </div>

    <div class="step-list">
      <article
        v-for="(step, index) in card.steps"
        :key="step.title"
        class="step-item"
        :class="step.status"
      >
        <div class="step-index">{{ index + 1 }}</div>
        <div class="step-content">
          <div class="step-head">
            <strong>{{ step.title }}</strong>
            <span>{{ step.duration }}</span>
          </div>
          <p>{{ step.detail }}</p>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.card-shell {
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

.card-head p,
.summary,
.timer-item small,
.step-item p {
  color: var(--color-text-soft);
}

.card-head p {
  margin: 0 0 0.25rem;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.card-head h3 {
  margin: 0;
  font-size: 1.1rem;
}

.card-head span {
  flex: 0 0 auto;
  padding: 0.34rem 0.65rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 0.78rem;
}

.summary {
  margin: 0.7rem 0 0;
}

.timer-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.timer-item {
  padding: 0.85rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.94), rgba(34, 61, 53, 0.94));
  color: #fef7ef;
}

.timer-item strong,
.timer-item small {
  display: block;
  color: inherit;
}

.step-list {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.step-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
  padding: 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.7);
}

.step-item.current {
  border-color: rgba(229, 143, 91, 0.34);
  background: linear-gradient(135deg, rgba(255, 246, 236, 0.96), rgba(255, 251, 245, 0.96));
}

.step-item.done {
  opacity: 0.72;
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

.step-item p {
  margin: 0.35rem 0 0;
}

@media (max-width: 640px) {
  .timer-row {
    grid-template-columns: 1fr;
  }
}
</style>
