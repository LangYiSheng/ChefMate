<script setup lang="ts">
import type { CardActionEvent, RecipeDetailCard as RecipeDetailCardType } from '../../types/chat'

defineProps<{
  card: RecipeDetailCardType
}>()

const emit = defineEmits<{
  action: [action: CardActionEvent]
}>()
</script>

<template>
  <section class="card-shell">
    <section class="hero-block">
      <div>
        <h4>{{ card.recipe.name }}</h4>
        <p>{{ card.recipe.description }}</p>
      </div>
      <div class="meta-row">
        <span>{{ card.recipe.difficulty }}</span>
        <span>{{ card.recipe.estimatedMinutes }} 分钟</span>
        <span>{{ card.recipe.servings }} 人份</span>
      </div>
      <div class="tag-row">
        <em v-for="tag in card.recipe.tags" :key="tag">{{ tag }}</em>
      </div>
    </section>

    <div class="detail-grid">
      <section class="detail-block">
        <h5>所需材料</h5>
        <div class="detail-scroll hover-scroll">
          <article
            v-for="ingredient in card.recipe.ingredients"
            :key="ingredient.id ?? ingredient.ingredientName"
            class="ingredient-item"
          >
            <div class="ingredient-top">
              <strong>{{ ingredient.ingredientName }}</strong>
              <span>{{ ingredient.amountText }}</span>
            </div>
            <p v-if="ingredient.purpose">{{ ingredient.purpose }}</p>
          </article>
        </div>
      </section>

      <section class="detail-block">
        <h5>步骤</h5>
        <div class="detail-scroll hover-scroll">
          <article
            v-for="step in card.recipe.steps"
            :key="step.id ?? step.stepNo"
            class="step-item"
          >
            <div class="step-top">
              <strong>{{ step.title || `步骤 ${step.stepNo}` }}</strong>
              <span>{{ step.timerSeconds ? `${Math.round(step.timerSeconds / 60)} 分钟` : '跟着感觉推进' }}</span>
            </div>
            <p>{{ step.instruction }}</p>
            <small v-if="step.notes">{{ step.notes }}</small>
          </article>
        </div>
      </section>
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
  min-width: min(100%, 34rem);
  padding: 1rem;
  border: 1px solid rgba(47, 93, 80, 0.16);
  border-radius: 1.35rem;
  background:
    linear-gradient(145deg, rgba(255, 254, 251, 0.98), rgba(250, 246, 239, 0.94)),
    var(--color-surface-strong);
}

.hero-block p,
.ingredient-item p,
.step-item p,
.step-item small {
  color: var(--color-text-soft);
}

.hero-block h4,
.detail-block h5 {
  margin: 0;
}

.hero-block {
  display: grid;
  gap: 0.8rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.64);
}

.hero-block h4 {
  font-size: 1.18rem;
}

.hero-block p {
  margin: 0.55rem 0 0;
  line-height: 1.7;
}

.meta-row,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.meta-row span,
.tag-row em {
  padding: 0.28rem 0.56rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-style: normal;
  font-size: 0.76rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
  margin-top: 0.95rem;
}

.detail-block {
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.64);
}

.detail-scroll {
  max-height: 14rem;
  margin-top: 0.85rem;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.35rem;
}

.ingredient-item,
.step-item {
  padding-top: 0.8rem;
  border-top: 1px solid rgba(47, 93, 80, 0.08);
}

.ingredient-item:first-child,
.step-item:first-child {
  padding-top: 0;
  border-top: 0;
}

.ingredient-top,
.step-top {
  display: flex;
  justify-content: space-between;
  gap: 0.7rem;
}

.ingredient-top span,
.step-top span {
  color: var(--color-text-soft);
  font-size: 0.8rem;
}

.ingredient-item p,
.step-item p,
.step-item small {
  margin: 0.4rem 0 0;
}

.action-row {
  display: flex;
  gap: 0.65rem;
  margin-top: 1rem;
}

.action-row button {
  flex: 1;
  min-height: 2.75rem;
  padding: 0.65rem 0.95rem;
  border-radius: 0.95rem;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
}

@media (max-width: 720px) {
  .detail-grid,
  .action-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
