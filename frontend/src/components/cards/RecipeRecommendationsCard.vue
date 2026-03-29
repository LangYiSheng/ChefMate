<script setup lang="ts">
import type { RecipeRecommendationsCard as RecipeRecommendationsCardType } from '../../types/chat'

defineProps<{
  card: RecipeRecommendationsCardType
}>()
</script>

<template>
  <section class="card-shell">
    <div class="card-head">
      <div>
        <p>推荐结果卡</p>
        <h3>{{ card.title }}</h3>
      </div>
      <span>Mock Data</span>
    </div>

    <p class="summary">{{ card.summary }}</p>

    <div class="recipe-grid">
      <article v-for="recipe in card.recipes" :key="recipe.id" class="recipe-item">
        <div class="recipe-top">
          <div>
            <strong>{{ recipe.name }}</strong>
            <small>{{ recipe.fitReason }}</small>
          </div>
          <span>{{ recipe.duration }}</span>
        </div>

        <div class="recipe-meta">
          <span>{{ recipe.difficulty }}</span>
          <span>{{ recipe.calories }}</span>
        </div>

        <div class="tag-row">
          <em v-for="highlight in recipe.highlights" :key="highlight">{{ highlight }}</em>
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
  background:
    linear-gradient(145deg, rgba(255, 254, 251, 0.98), rgba(250, 246, 239, 0.94)),
    var(--color-surface-strong);
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.card-head p,
.summary,
.recipe-item small,
.recipe-meta {
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
  padding: 0.32rem 0.6rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-size: 0.76rem;
}

.summary {
  margin: 0.7rem 0 0;
}

.recipe-grid {
  display: grid;
  gap: 0.8rem;
  margin-top: 1rem;
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
  margin-bottom: 0.7rem;
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
  margin-bottom: 0.8rem;
  font-size: 0.82rem;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.tag-row em {
  padding: 0.28rem 0.56rem;
  border-radius: 999px;
  background: rgba(229, 143, 91, 0.14);
  color: #a05522;
  font-style: normal;
  font-size: 0.76rem;
}
</style>
