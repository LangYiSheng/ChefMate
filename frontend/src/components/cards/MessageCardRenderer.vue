<script setup lang="ts">
import CookingGuideCard from './CookingGuideCard.vue'
import PantryStatusCard from './PantryStatusCard.vue'
import RecipeDetailCard from './RecipeDetailCard.vue'
import RecipeRecommendationsCard from './RecipeRecommendationsCard.vue'
import type {
  CardActionEvent,
  CookingGuideCard as CookingGuideCardType,
  MessageCard,
  PantryStatusCard as PantryStatusCardType,
  RecipeDetailCard as RecipeDetailCardType,
  RecipeRecommendationsCard as RecipeRecommendationsCardType,
  TimerRequest,
} from '../../types/chat'

const props = defineProps<{
  card: MessageCard
  autoStartStepTimer: boolean
}>()

const emit = defineEmits<{
  action: [action: CardActionEvent]
  startTimer: [payload: TimerRequest]
}>()

function asRecipeCard(card: MessageCard) {
  return card as RecipeRecommendationsCardType
}

function asPantryCard(card: MessageCard) {
  return card as PantryStatusCardType
}

function asRecipeDetailCard(card: MessageCard) {
  return card as RecipeDetailCardType
}

function asCookingCard(card: MessageCard) {
  return card as CookingGuideCardType
}
</script>

<template>
  <RecipeRecommendationsCard
    v-if="props.card.type === 'recipe-recommendations'"
    :card="asRecipeCard(props.card)"
    @action="emit('action', $event)"
  />
  <RecipeDetailCard
    v-else-if="props.card.type === 'recipe-detail'"
    :card="asRecipeDetailCard(props.card)"
    @action="emit('action', $event)"
  />
  <PantryStatusCard
    v-else-if="props.card.type === 'pantry-status'"
    :card="asPantryCard(props.card)"
    @action="emit('action', $event)"
  />
  <CookingGuideCard
    v-else
    :card="asCookingCard(props.card)"
    :auto-start-timer="props.autoStartStepTimer"
    @start-timer="emit('startTimer', $event)"
  />
</template>
