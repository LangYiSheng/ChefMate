<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchRecipes } from '../lib/api'
import { getAuthToken } from '../state/auth'
import type { RecipeRecord, RecipeSearchField } from '../types/chat'

const props = defineProps<{
  recipes: RecipeRecord[]
  selectedRecipe?: RecipeRecord | null
  selectedRecipeId?: number | null
  recommendationSeed?: string
}>()

const emit = defineEmits<{
  selectRecipe: [recipeId: number]
  showLibrary: []
  startConversation: [recipe: RecipeRecord]
  toggleSidebar: []
}>()

const searchFieldOptions: Array<{ value: RecipeSearchField; label: string }> = [
  { value: 'name', label: '菜名' },
  { value: 'ingredient', label: '食材' },
  { value: 'method', label: '做法' },
  { value: 'flavor', label: '口味' },
]

const searchQuery = ref('')
const submittedSearchQuery = ref('')
const selectedSearchFields = ref<RecipeSearchField[]>(['name', 'ingredient', 'method', 'flavor'])
const submittedSearchFields = ref<RecipeSearchField[]>(['name', 'ingredient', 'method', 'flavor'])
const libraryRecipes = ref<RecipeRecord[]>([])
const recentRecipes = ref<RecipeRecord[]>([])
const libraryLoading = ref(false)
const libraryError = ref('')

const normalizedSearch = computed(() => searchQuery.value.trim())
const isSearching = computed(() => submittedSearchQuery.value.length > 0)
const activeSearchFieldLabels = computed(() =>
  searchFieldOptions
    .filter((option) => submittedSearchFields.value.includes(option.value))
    .map((option) => option.label)
    .join('、'),
)

const recommendedRecipes = computed(() => libraryRecipes.value)

const selectedRecipe = computed(
  () => props.selectedRecipe ?? props.recipes.find((recipe) => recipe.id === props.selectedRecipeId) ?? null,
)

async function loadLibraryRecipes() {
  const token = getAuthToken()
  if (!token) {
    return
  }

  libraryLoading.value = true
  libraryError.value = ''

  try {
    const response = await fetchRecipes(token, {
      keyword: isSearching.value ? submittedSearchQuery.value : undefined,
      searchFields: isSearching.value ? submittedSearchFields.value : undefined,
      limit: isSearching.value ? 24 : 6,
      offset: 0,
    })
    libraryRecipes.value = response.items
    recentRecipes.value = response.recentItems
  } catch (error) {
    libraryError.value = error instanceof Error ? error.message : '菜谱加载失败，请稍后再试。'
    libraryRecipes.value = []
    recentRecipes.value = []
  } finally {
    libraryLoading.value = false
  }
}

function submitSearch() {
  submittedSearchQuery.value = normalizedSearch.value
  submittedSearchFields.value = [...selectedSearchFields.value]
  void loadLibraryRecipes()
}

function resetSearch() {
  searchQuery.value = ''
  submittedSearchQuery.value = ''
  submittedSearchFields.value = [...selectedSearchFields.value]
  void loadLibraryRecipes()
}

function toggleSearchField(field: RecipeSearchField) {
  if (selectedSearchFields.value.includes(field)) {
    if (selectedSearchFields.value.length === 1) {
      return
    }
    selectedSearchFields.value = selectedSearchFields.value.filter((item) => item !== field)
    return
  }

  selectedSearchFields.value = [...selectedSearchFields.value, field]
}

function openRecipe(recipeId: number) {
  emit('selectRecipe', recipeId)
}

function goBackToLibrary() {
  emit('showLibrary')
}

function startSelectedRecipeConversation() {
  if (!selectedRecipe.value) {
    return
  }

  emit('startConversation', selectedRecipe.value)
}

function formatTimer(seconds?: number | null) {
  if (!seconds) {
    return null
  }

  if (seconds < 60) {
    return `${seconds} 秒`
  }

  return `${Math.round(seconds / 60)} 分钟`
}

watch(
  () => props.recommendationSeed,
  () => {
    if (!isSearching.value) {
      void loadLibraryRecipes()
    }
  },
)

onMounted(() => {
  void loadLibraryRecipes()
})
</script>

<template>
  <section class="recipe-panel">
    <header class="panel-header">
      <div class="panel-title">
        <button class="menu-button" type="button" aria-label="打开侧边栏" @click="emit('toggleSidebar')">
          <span></span>
          <span></span>
          <span></span>
        </button>

        <button
          v-if="selectedRecipe"
          type="button"
          class="back-button"
          aria-label="返回菜谱列表"
          @click="goBackToLibrary"
        >
          <span></span>
        </button>

        <div>
          <p>菜谱</p>
          <h2>{{ selectedRecipe ? selectedRecipe.name : '菜谱浏览' }}</h2>
        </div>
      </div>
    </header>

    <Transition name="recipe-view-fade" mode="out-in">
      <div v-if="!selectedRecipe" key="library" class="library-view">
        <div class="search-shell">
          <input
            v-model="searchQuery"
            class="search-input"
            type="search"
            placeholder="输入关键词，从全部菜谱中搜索"
            @keydown.enter.prevent="submitSearch"
          />

          <div class="search-field-row">
            <button
              v-for="option in searchFieldOptions"
              :key="option.value"
              type="button"
              class="field-chip"
              :class="{ active: selectedSearchFields.includes(option.value) }"
              @click="toggleSearchField(option.value)"
            >
              {{ option.label }}
            </button>
          </div>

          <div class="search-action-row">
            <button type="button" class="search-button" @click="submitSearch">搜索菜谱</button>
            <button
              v-if="isSearching"
              type="button"
              class="search-button search-button-ghost"
              @click="resetSearch"
            >
              恢复推荐
            </button>
          </div>
        </div>

        <div class="library-scroll hover-scroll">
          <section v-if="recentRecipes.length" class="section-block">
            <div class="section-head">
              <h3>最近尝试过的菜谱</h3>
              <p>快速回到最近浏览或做过的菜谱。</p>
            </div>

            <div class="recipe-grid recent-grid">
              <button
                v-for="recipe in recentRecipes"
                :key="recipe.id"
                type="button"
                class="recipe-card"
                @click="openRecipe(recipe.id)"
              >
                <strong>{{ recipe.name }}</strong>
                <small>{{ recipe.recentActivity }}</small>
                <p>{{ recipe.description }}</p>
              </button>
            </div>
          </section>

          <section class="section-block">
            <div class="section-head">
              <h3>{{ isSearching ? '搜索结果' : '推荐菜谱' }}</h3>
              <p>
                {{
                  isSearching
                    ? `共找到 ${recommendedRecipes.length} 道菜谱，搜索范围：${activeSearchFieldLabels}`
                    : '这 6 道推荐会优先参考你的长期记忆标签和常见偏好。'
                }}
              </p>
            </div>

            <div v-if="libraryLoading" class="state-card">正在加载菜谱...</div>
            <div v-else-if="libraryError" class="state-card state-card-error">{{ libraryError }}</div>
            <div v-else-if="!recommendedRecipes.length" class="state-card">
              {{ isSearching ? '没有找到符合条件的菜谱，换个关键词或搜索范围试试。' : '暂时还没有可推荐的菜谱。' }}
            </div>

            <div v-else class="recipe-grid">
              <button
                v-for="recipe in recommendedRecipes"
                :key="recipe.id"
                type="button"
                class="recipe-card"
                @click="openRecipe(recipe.id)"
              >
                <div class="recipe-card-top">
                  <strong>{{ recipe.name }}</strong>
                  <span>{{ recipe.estimatedMinutes }} 分钟</span>
                </div>
                <p>{{ recipe.description }}</p>
                <div class="meta-row">
                  <em>{{ recipe.difficulty }}</em>
                  <em>{{ recipe.servings }} 人份</em>
                </div>
                <div class="tag-row">
                  <span v-for="tag in recipe.tags.slice(0, 4)" :key="tag">{{ tag }}</span>
                </div>
              </button>
            </div>
          </section>
        </div>
      </div>

      <div v-else key="detail" class="detail-view">
        <div class="detail-scroll hover-scroll">
          <section class="hero-card">
            <div class="hero-cover">
              <span>菜谱详情</span>
              <strong>{{ selectedRecipe.name }}</strong>
            </div>

            <div class="hero-copy">
              <p class="hero-description">{{ selectedRecipe.description }}</p>
              <div class="hero-meta">
                <span>{{ selectedRecipe.difficulty }}</span>
                <span>{{ selectedRecipe.estimatedMinutes }} 分钟</span>
                <span>{{ selectedRecipe.servings }} 人份</span>
              </div>
              <div class="tag-row">
                <span v-for="tag in selectedRecipe.tags" :key="tag">{{ tag }}</span>
              </div>

              <button type="button" class="open-chat-button" @click="startSelectedRecipeConversation">
                开启对话
              </button>
            </div>
          </section>

          <div class="detail-grid">
            <section class="detail-card">
              <h3>所需材料</h3>
              <div class="detail-card-body hover-scroll">
                <div class="ingredient-list">
                  <article
                    v-for="ingredient in selectedRecipe.ingredients"
                    :key="`${selectedRecipe.id}-${ingredient.ingredientName}`"
                    class="ingredient-item"
                  >
                    <div class="ingredient-main">
                      <strong>{{ ingredient.ingredientName }}</strong>
                      <span>{{ ingredient.amountText }}</span>
                    </div>
                    <p v-if="ingredient.purpose">{{ ingredient.purpose }}</p>
                    <small v-if="ingredient.isOptional">可选</small>
                  </article>
                </div>
              </div>
            </section>

            <section class="detail-card">
              <h3>补充说明</h3>
              <div class="detail-card-body hover-scroll">
                <p class="tips-text">{{ selectedRecipe.tips || '这道菜暂无额外补充说明。' }}</p>
              </div>
            </section>
          </div>

          <section class="detail-card">
            <h3>步骤</h3>
            <div class="step-list">
              <article
                v-for="step in selectedRecipe.steps"
                :key="`${selectedRecipe.id}-${step.stepNo}`"
                class="step-item"
              >
                <div class="step-index">{{ step.stepNo }}</div>
                <div class="step-content">
                  <div class="step-head">
                    <strong>{{ step.title || `步骤 ${step.stepNo}` }}</strong>
                    <span v-if="formatTimer(step.timerSeconds)">{{ formatTimer(step.timerSeconds) }}</span>
                  </div>
                  <p>{{ step.instruction }}</p>
                  <small v-if="step.notes">{{ step.notes }}</small>
                </div>
              </article>
            </div>
          </section>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.recipe-panel {
  display: grid;
  height: 100%;
  min-height: 0;
  width: min(100%, 58rem);
  margin: 0 auto;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1rem;
}

.recipe-view-fade-enter-active,
.recipe-view-fade-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.recipe-view-fade-enter-from,
.recipe-view-fade-leave-to {
  opacity: 0;
  transform: translateY(0.55rem);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.15rem 0 0.2rem;
}

.panel-title {
  display: flex;
  gap: 0.95rem;
  align-items: center;
}

.menu-button {
  display: none;
  flex-direction: column;
  gap: 0.24rem;
  align-items: center;
  justify-content: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 12px 22px rgba(29, 43, 39, 0.07);
  cursor: pointer;
}

.menu-button span {
  width: 1rem;
  height: 2px;
  border-radius: 999px;
  background: var(--color-accent);
}

.panel-header p {
  margin: 0 0 0.3rem;
  color: var(--color-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.85rem;
  line-height: 1.1;
}

.back-button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
}

.back-button span {
  width: 0.7rem;
  height: 0.7rem;
  border-bottom: 2px solid var(--color-accent);
  border-left: 2px solid var(--color-accent);
  transform: rotate(45deg);
}

.library-view,
.detail-view {
  display: grid;
  min-height: 0;
}

.library-view {
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1rem;
}

.search-shell {
  padding: 0.2rem 0;
}

.search-input {
  width: 100%;
  padding: 0.9rem 1rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1.1rem;
  background: rgba(255, 252, 247, 0.9);
}

.search-field-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.8rem;
}

.field-chip {
  padding: 0.42rem 0.78rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 999px;
  background: rgba(255, 252, 247, 0.82);
  color: var(--color-text-soft);
  cursor: pointer;
}

.field-chip.active {
  background: rgba(47, 93, 80, 0.1);
  color: var(--color-accent);
  border-color: rgba(47, 93, 80, 0.22);
}

.search-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.9rem;
}

.search-button {
  min-height: 2.6rem;
  padding: 0 1rem;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
  cursor: pointer;
}

.search-button-ghost {
  background: rgba(255, 252, 247, 0.88);
  border: 1px solid rgba(47, 93, 80, 0.12);
  color: var(--color-accent);
}

.library-scroll,
.detail-scroll {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.35rem;
}

.section-block,
.detail-card,
.hero-card {
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1.25rem;
  background: rgba(255, 255, 255, 0.62);
}

.section-block {
  padding: 1.15rem 1.2rem;
  margin-bottom: 1rem;
}

.section-head h3,
.detail-card h3 {
  margin: 0;
  font-size: 1rem;
}

.section-head p,
.tips-text,
.ingredient-item p,
.step-item p,
.step-item small {
  color: var(--color-text-soft);
}

.section-head p {
  margin: 0.35rem 0 0;
}

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 1rem;
}

.state-card {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px dashed rgba(47, 93, 80, 0.18);
  border-radius: 1rem;
  background: rgba(255, 252, 247, 0.7);
  color: var(--color-text-soft);
}

.state-card-error {
  border-style: solid;
  border-color: rgba(160, 85, 34, 0.16);
  color: #8f4a1e;
}

.recent-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.recipe-card {
  padding: 1rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1.05rem;
  text-align: left;
  background: rgba(255, 252, 247, 0.88);
  cursor: pointer;
}

.recipe-card strong,
.recipe-card small {
  display: block;
}

.recipe-card small,
.recipe-card p {
  color: var(--color-text-soft);
}

.recipe-card p {
  margin: 0.55rem 0;
}

.recipe-card-top {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.recipe-card-top span {
  color: var(--color-accent);
  font-size: 0.82rem;
}

.meta-row,
.tag-row,
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.meta-row em,
.tag-row span,
.hero-meta span {
  padding: 0.28rem 0.56rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
  font-style: normal;
  font-size: 0.76rem;
}

.hero-card {
  display: grid;
  grid-template-columns: 16rem minmax(0, 1fr);
  gap: 1rem;
  padding: 1.2rem;
}

.hero-cover {
  display: grid;
  align-content: end;
  min-height: 13rem;
  padding: 1rem;
  border-radius: 1rem;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.18), transparent 35%),
    linear-gradient(135deg, rgba(47, 93, 80, 0.94), rgba(32, 57, 49, 0.88));
  color: #fffaf3;
}

.hero-cover span {
  opacity: 0.78;
  font-size: 0.8rem;
}

.hero-cover strong {
  margin-top: 0.5rem;
  font-size: 1.5rem;
  line-height: 1.15;
}

.hero-description {
  margin: 0 0 0.8rem;
  color: var(--color-text);
}

.detail-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.detail-card {
  padding: 1.15rem 1.2rem;
  margin-top: 1rem;
}

.detail-card-body {
  max-height: 13.5rem;
  margin-top: 1rem;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.35rem;
}

.ingredient-list,
.step-list {
  display: grid;
  gap: 0.8rem;
  margin-top: 1rem;
}

.ingredient-item {
  padding-top: 0.8rem;
  border-top: 1px solid rgba(47, 93, 80, 0.08);
}

.ingredient-item:first-child {
  padding-top: 0;
  border-top: 0;
}

.ingredient-main,
.step-head {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.ingredient-main span,
.step-head span {
  color: var(--color-text-soft);
  font-size: 0.82rem;
}

.ingredient-item p,
.ingredient-item small {
  display: block;
  margin: 0.35rem 0 0;
}

.step-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.8rem;
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.1);
  color: var(--color-accent);
  font-weight: 700;
}

.open-chat-button {
  flex: 0 0 auto;
  width: 10rem;
  height: 2.9rem;
  margin-top: 1rem;
  padding: 0.8rem 1.25rem;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
  cursor: pointer;
}

@media (max-width: 860px) {
  .recipe-grid,
  .recent-grid,
  .hero-card,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .panel-header {
    flex-direction: column;
    align-items: stretch;
    padding-right: 0;
  }

  .panel-title {
    align-items: flex-start;
  }

  .menu-button {
    display: inline-flex;
  }
}

@media (max-width: 640px) {
  .panel-header h2 {
    font-size: 1.45rem;
  }

  .open-chat-button {
    width: 100%;
  }
}
</style>
