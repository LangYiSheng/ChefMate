<script setup lang="ts">
import CookingGuideCard from './CookingGuideCard.vue'
import PantryStatusCard from './PantryStatusCard.vue'
import RecipeRecommendationsCard from './RecipeRecommendationsCard.vue'
import type {
  CookingGuideCard as CookingGuideCardType,
  MessageCard,
  PantryStatusCard as PantryStatusCardType,
  RecipeRecommendationsCard as RecipeRecommendationsCardType,
} from '../../types/chat'

const props = defineProps<{
  card: MessageCard
}>()

function asRecipeCard(card: MessageCard) {
  return card as RecipeRecommendationsCardType
}

function asPantryCard(card: MessageCard) {
  return card as PantryStatusCardType
}

function asCookingCard(card: MessageCard) {
  return card as CookingGuideCardType
}
</script>

<template>
  <RecipeRecommendationsCard
    v-if="props.card.type === 'recipe-recommendations'"
    :card="asRecipeCard(props.card)"
  />
  <PantryStatusCard
    v-else-if="props.card.type === 'pantry-status'"
    :card="asPantryCard(props.card)"
  />
  <CookingGuideCard v-else :card="asCookingCard(props.card)" />
</template>
