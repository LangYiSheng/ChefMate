<script setup lang="ts">
import type {
  CardActionEvent,
  RecipeRecommendationsCard as RecipeRecommendationsCardType,
} from '../../types/chat'

defineProps<{
  card: RecipeRecommendationsCardType
  disabled: boolean
}>()

const emit = defineEmits<{
  action: [action: CardActionEvent]
}>()
</script>

<template>
  <section class="card-shell" :class="{ 'is-disabled': disabled }" :aria-disabled="disabled">
    <div class="card-head">
      <h3>{{ card.title }}</h3>
      <span>{{ card.recipes.length }} 道候选</span>
    </div>

    <div class="recipe-grid">
      <article v-for="recipe in card.recipes" :key="recipe.recipeId" class="recipe-item">
        <div class="recipe-top">
          <div>
            <strong>{{ recipe.name }}</strong>
            <small>{{ recipe.description }}</small>
          </div>
          <span>{{ recipe.estimatedMinutes }} 分钟</span>
        </div>

        <div class="recipe-meta">
          <span>{{ recipe.difficulty }}</span>
          <span>{{ recipe.servings }} 人份</span>
        </div>

        <div class="tag-row">
          <em v-for="tag in recipe.tags" :key="tag">{{ tag }}</em>
        </div>

        <div class="action-row">
          <button
            v-for="action in recipe.actions"
            :key="action.id"
            type="button"
            :class="action.actionType === 'try_recipe' ? 'primary-button' : 'ghost-button'"
            @click="emit('action', { actionType: action.actionType, payload: action.payload })"
          >
            {{ action.label }}
          </button>
        </div>
      </article>
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

.recipe-item small,
.recipe-meta {
  color: var(--color-text-soft);
}

.card-head h3 {
  margin: 0;
  font-size: 1.1rem;
}

.card-head span {
  flex: 0 0 auto;
  padding: 0.32rem 0.6rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 0.76rem;
}

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 0.9rem;
}

.recipe-item {
  padding: 0.95rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.62);
}

.recipe-top {
  display: flex;
  justify-content: space-between;
  gap: 0.85rem;
}

.recipe-top strong,
.recipe-top small,
.recipe-meta span {
  display: block;
}

.recipe-top span {
  flex: 0 0 auto;
  color: var(--color-accent);
  font-size: 0.82rem;
}

.recipe-meta {
  display: flex;
  gap: 0.8rem;
  margin-top: 0.75rem;
  font-size: 0.82rem;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.8rem;
}

.tag-row em {
  padding: 0.28rem 0.56rem;
  border-radius: 999px;
  background: rgba(229, 143, 91, 0.14);
  color: #a05522;
  font-style: normal;
  font-size: 0.76rem;
}

.action-row {
  display: flex;
  gap: 0.65rem;
  margin-top: 1rem;
}

.action-row button {
  flex: 1;
  min-height: 2.7rem;
  padding: 0.65rem 0.9rem;
  border-radius: 0.95rem;
  cursor: pointer;
}

.ghost-button {
  border: 1px solid rgba(47, 93, 80, 0.14);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-accent);
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
}

@media (max-width: 640px) {
  .recipe-grid {
    grid-template-columns: 1fr;
  }

  .action-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}

@media (min-width: 641px) and (max-width: 980px) {
  .recipe-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
