<script setup lang="ts">
import type { PantryStatusCard as PantryStatusCardType } from '../../types/chat'

defineProps<{
  card: PantryStatusCardType
}>()

function statusLabel(status: PantryStatusCardType['checklist'][number]['status']) {
  if (status === 'ready') {
    return '已齐'
  }

  if (status === 'low') {
    return '不足'
  }

  return '缺失'
}
</script>

<template>
  <section class="card-shell">
    <div class="card-head">
      <div>
        <p>备料检查卡</p>
        <h3>{{ card.title }}</h3>
      </div>
      <strong>{{ Math.round(card.completion * 100) }}%</strong>
    </div>

    <p class="summary">{{ card.summary }}</p>

    <div class="progress-track">
      <div class="progress-bar" :style="{ width: `${Math.round(card.completion * 100)}%` }"></div>
    </div>

    <div class="checklist">
      <article v-for="item in card.checklist" :key="item.ingredient" class="check-item">
        <div class="check-main">
          <div>
            <strong>{{ item.ingredient }}</strong>
            <small>{{ item.amount }}</small>
          </div>
          <span :class="item.status">{{ statusLabel(item.status) }}</span>
        </div>
        <p>{{ item.note }}</p>
      </article>
    </div>

    <div class="action-row">
      <button v-for="action in card.actions" :key="action" type="button">{{ action }}</button>
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
.check-item p,
.check-main small {
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

.card-head strong {
  color: var(--color-accent);
  font-size: 1.1rem;
}

.summary {
  margin: 0.7rem 0 0;
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

.checklist {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.check-item {
  padding: 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.62);
}

.check-main {
  display: flex;
  justify-content: space-between;
  gap: 0.7rem;
  align-items: center;
}

.check-main span {
  flex: 0 0 auto;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  font-size: 0.76rem;
}

.check-main span.ready {
  background: rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
}

.check-main span.low {
  background: rgba(229, 143, 91, 0.12);
  color: #a05522;
}

.check-main span.missing {
  background: rgba(150, 72, 58, 0.12);
  color: #8b4436;
}

.check-item p {
  margin: 0.5rem 0 0;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.95rem;
}

.action-row button {
  padding: 0.52rem 0.8rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-accent);
  cursor: pointer;
}
</style>
