<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { TagCatalog, TagCategoryKey, UserProfileSummary } from '../types/chat'

interface WorkspaceOnboardingPayload {
  name: string
  cookingPreferenceText: string
  tagSelections: TagCatalog
  allowAutoUpdate: boolean
  autoStartStepTimer: boolean
}

const props = defineProps<{
  isOpen: boolean
  tagCatalog: TagCatalog
  userProfile: UserProfileSummary
}>()

const emit = defineEmits<{
  complete: [payload: WorkspaceOnboardingPayload]
}>()

const steps = [
  '欢迎来到 ChefMate',
  '完善个人信息',
  '设置偏好档案',
  '调整记忆设置',
  '开始第一段对话',
] as const

const categoryMeta: Array<{ key: TagCategoryKey; label: string }> = [
  { key: 'flavor', label: '口味' },
  { key: 'method', label: '做法' },
  { key: 'scene', label: '场景' },
  { key: 'health', label: '健康' },
  { key: 'time', label: '时间' },
  { key: 'tool', label: '工具' },
]

const currentStep = ref(0)
const displayName = ref('')
const cookingPreferenceText = ref('')
const allowAutoUpdate = ref(true)
const autoStartStepTimer = ref(false)
const selectedTags = ref<TagCatalog>({
  flavor: [],
  method: [],
  scene: [],
  health: [],
  time: [],
  tool: [],
})

const selectedTagCount = computed(() => Object.values(selectedTags.value).flat().length)
const canContinue = computed(() => {
  if (currentStep.value === 1) {
    return displayName.value.trim().length > 1
  }

  return true
})

function normalizeSelections(source: UserProfileSummary['tagSelections']): TagCatalog {
  return {
    flavor: source.flavor.filter((tag) => props.tagCatalog.flavor.includes(tag)),
    method: source.method.filter((tag) => props.tagCatalog.method.includes(tag)),
    scene: source.scene.filter((tag) => props.tagCatalog.scene.includes(tag)),
    health: source.health.filter((tag) => props.tagCatalog.health.includes(tag)),
    time: source.time.filter((tag) => props.tagCatalog.time.includes(tag)),
    tool: source.tool.filter((tag) => props.tagCatalog.tool.includes(tag)),
  }
}

function toggleTag(category: TagCategoryKey, tag: string) {
  const currentTags = selectedTags.value[category]
  if (currentTags.includes(tag)) {
    selectedTags.value[category] = currentTags.filter((item) => item !== tag)
    return
  }

  selectedTags.value[category] = [...currentTags, tag]
}

function availableTags(category: TagCategoryKey) {
  return props.tagCatalog[category].filter((tag) => !selectedTags.value[category].includes(tag))
}

function goNext() {
  if (!canContinue.value || currentStep.value >= steps.length - 1) {
    return
  }

  currentStep.value += 1
}

function goBack() {
  if (currentStep.value === 0) {
    return
  }

  currentStep.value -= 1
}

function skipPreferences() {
  currentStep.value = 3
}

function completeOnboarding() {
  emit('complete', {
    name: displayName.value.trim(),
    cookingPreferenceText: cookingPreferenceText.value.trim(),
    tagSelections: selectedTags.value,
    allowAutoUpdate: allowAutoUpdate.value,
    autoStartStepTimer: autoStartStepTimer.value,
  })
}

watch(
  () => [props.userProfile, props.tagCatalog] as const,
  ([profile]) => {
    displayName.value = profile.name
    cookingPreferenceText.value = profile.cookingPreferenceText
    allowAutoUpdate.value = profile.allowAutoUpdate
    autoStartStepTimer.value = profile.autoStartStepTimer
    selectedTags.value = normalizeSelections(profile.tagSelections)
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="onboarding-fade">
      <section v-if="isOpen" class="onboarding-shell" role="dialog" aria-modal="true">
        <div class="onboarding-layout">
          <aside class="onboarding-aside">
            <p class="aside-eyebrow">首次使用引导</p>
            <h2>ChefMate 会先花一点时间认识你，再更好地陪你做饭。</h2>
            <ol class="step-list">
              <li
                v-for="(step, index) in steps"
                :key="step"
                :class="{ active: index === currentStep, done: index < currentStep }"
              >
                <span>{{ index + 1 }}</span>
                <strong>{{ step }}</strong>
              </li>
            </ol>
          </aside>

          <section class="onboarding-main">
            <Transition name="step-fade" mode="out-in">
              <div :key="currentStep" class="step-panel">
                <template v-if="currentStep === 0">
                  <p class="step-eyebrow">欢迎来到 ChefMate</p>
                  <h3>从推荐到备料，再到烹饪的每一步，ChefMate 会一直陪你推进。</h3>
                  <p class="step-copy">
                    在开始之前，我们先用几个小步骤帮你把个人信息、偏好档案和记忆设置准备好。
                  </p>
                </template>

                <template v-else-if="currentStep === 1">
                  <p class="step-eyebrow">完善个人信息</p>
                  <h3>先告诉我该怎么称呼你</h3>
                  <label class="field-block">
                    <span>账户显示名称</span>
                    <input v-model="displayName" placeholder="例如：小满" />
                    <small>这个名称会显示在你的工作台和个人设置中</small>
                  </label>
                </template>

                <template v-else-if="currentStep === 2">
                  <p class="step-eyebrow">偏好档案</p>
                  <h3>选择一些长期记忆标签，也可以简单写下你的做饭习惯</h3>
                  <p class="step-copy">这一步可以跳过，后面也能随时回来补充。</p>

                  <div class="tag-groups hover-scroll">
                    <section v-for="category in categoryMeta" :key="category.key" class="tag-group">
                      <div class="tag-head">
                        <strong>{{ category.label }}</strong>
                        <span>{{ selectedTags[category.key].length }} 已选</span>
                      </div>

                      <div class="chip-row">
                        <button
                          v-for="tag in selectedTags[category.key]"
                          :key="tag"
                          type="button"
                          class="chip chip-active"
                          @click="toggleTag(category.key, tag)"
                        >
                          {{ tag }}
                          <b>×</b>
                        </button>
                      </div>

                      <div class="chip-row chip-row-muted">
                        <button
                          v-for="tag in availableTags(category.key)"
                          :key="tag"
                          type="button"
                          class="chip"
                          @click="toggleTag(category.key, tag)"
                        >
                          {{ tag }}
                        </button>
                      </div>
                    </section>
                  </div>

                  <label class="field-block">
                    <span>偏好描述</span>
                    <textarea
                      v-model="cookingPreferenceText"
                      rows="4"
                      placeholder="例如：工作日晚饭希望快一点，偏家常、少油，尽量少洗锅。"
                    ></textarea>
                    <small>已选 {{ selectedTagCount }} 个长期记忆标签</small>
                  </label>
                </template>

                <template v-else-if="currentStep === 3">
                  <p class="step-eyebrow">记忆设置</p>
                  <h3>最后确认一下，ChefMate 是否可以根据聊天过程更新你的档案</h3>

                  <div class="toggle-card">
                    <div>
                      <strong>允许 ChefMate 更新偏好档案</strong>
                      <p>开启后，系统会结合你的对话和选择不断调整你的偏好信息。</p>
                    </div>

                    <button
                      type="button"
                      class="toggle-button"
                      :class="{ active: allowAutoUpdate }"
                      @click="allowAutoUpdate = !allowAutoUpdate"
                    >
                      <span></span>
                    </button>
                  </div>

                  <div class="toggle-card">
                    <div>
                      <strong>到步骤时自动开启计时器</strong>
                      <p>进入带计时的步骤后，会自动在右上角启动对应计时器。</p>
                    </div>

                    <button
                      type="button"
                      class="toggle-button"
                      :class="{ active: autoStartStepTimer }"
                      @click="autoStartStepTimer = !autoStartStepTimer"
                    >
                      <span></span>
                    </button>
                  </div>
                </template>

                <template v-else>
                  <p class="step-eyebrow">准备完成</p>
                  <h3>现在就开启一个新对话，开始探索 ChefMate 吧</h3>
                  <p class="step-copy">
                    你可以直接说“今晚想吃点热乎的”，或者告诉我冰箱里现在有什么食材。
                  </p>
                </template>
              </div>
            </Transition>

            <div class="step-actions">
              <button v-if="currentStep > 0" type="button" class="secondary-button" @click="goBack">上一步</button>
              <button
                v-if="currentStep === 2"
                type="button"
                class="ghost-button"
                @click="skipPreferences"
              >
                先跳过
              </button>
              <button
                v-if="currentStep < steps.length - 1"
                type="button"
                class="primary-button"
                :disabled="!canContinue"
                @click="goNext"
              >
                下一步
              </button>
              <button
                v-else
                type="button"
                class="primary-button"
                @click="completeOnboarding"
              >
                开启一个新对话
              </button>
            </div>
          </section>
        </div>
      </section>
    </Transition>
  </Teleport>
</template>

<style scoped>
.onboarding-shell {
  position: fixed;
  inset: 0;
  z-index: 80;
  background:
    radial-gradient(circle at top left, rgba(229, 143, 91, 0.18), transparent 24rem),
    radial-gradient(circle at right, rgba(54, 106, 94, 0.12), transparent 26rem),
    rgba(244, 239, 230, 0.98);
  backdrop-filter: blur(8px);
}

.onboarding-layout {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(18rem, 24rem) minmax(0, 1fr);
}

.onboarding-aside {
  padding: 3rem 2rem;
  background: linear-gradient(160deg, rgba(37, 73, 63, 0.98), rgba(27, 52, 45, 0.98));
  color: #fff8ef;
}

.aside-eyebrow,
.step-eyebrow {
  margin: 0 0 0.7rem;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.onboarding-aside h2,
.step-panel h3 {
  margin: 0;
  line-height: 1.08;
}

.onboarding-aside h2 {
  font-size: 2rem;
}

.step-list {
  display: grid;
  gap: 0.75rem;
  margin: 2rem 0 0;
  padding: 0;
  list-style: none;
}

.step-list li {
  display: flex;
  gap: 0.8rem;
  align-items: center;
  color: rgba(255, 248, 239, 0.58);
}

.step-list li span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 0.8rem;
}

.step-list li.active,
.step-list li.done {
  color: #fff8ef;
}

.step-list li.done span,
.step-list li.active span {
  background: rgba(229, 143, 91, 0.92);
  color: #fff8ef;
}

.onboarding-main {
  display: grid;
  min-height: 100vh;
  grid-template-rows: minmax(0, 1fr) auto;
  padding: 3rem;
}

.step-panel {
  width: min(100%, 48rem);
}

.step-panel h3 {
  font-size: clamp(2rem, 4vw, 3rem);
}

.step-copy {
  width: min(100%, 34rem);
  margin: 1rem 0 0;
  color: var(--color-text-soft);
  font-size: 1rem;
  line-height: 1.8;
}

.field-block {
  display: grid;
  gap: 0.45rem;
  margin-top: 1.6rem;
}

.field-block input,
.field-block textarea {
  width: min(100%, 32rem);
  min-height: 3.2rem;
  padding: 0.9rem 1rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.86);
}

.field-block textarea {
  resize: vertical;
}

.field-block small,
.toggle-card p,
.tag-head span {
  color: var(--color-text-soft);
}

.tag-groups {
  display: grid;
  gap: 0.9rem;
  max-height: 20rem;
  margin-top: 1.5rem;
  overflow-y: auto;
  padding-right: 0.4rem;
}

.tag-group {
  padding: 1rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.64);
}

.tag-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.85rem;
}

.chip {
  padding: 0.45rem 0.78rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  cursor: pointer;
}

.chip-active {
  background: rgba(47, 93, 80, 0.1);
  color: var(--color-accent);
}

.chip-row-muted .chip {
  color: var(--color-text-soft);
}

.toggle-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1.1rem;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1.1rem;
  background: rgba(255, 255, 255, 0.7);
}

.toggle-button {
  position: relative;
  width: 3.2rem;
  height: 1.9rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.14);
  cursor: pointer;
}

.toggle-button span {
  position: absolute;
  top: 0.22rem;
  left: 0.24rem;
  width: 1.46rem;
  height: 1.46rem;
  border-radius: 999px;
  background: #fffef9;
  transition: transform 180ms ease;
}

.toggle-button.active {
  background: rgba(47, 93, 80, 0.78);
}

.toggle-button.active span {
  transform: translateX(1.26rem);
}

.step-actions {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  justify-content: flex-end;
}

.step-actions button {
  min-height: 2.9rem;
  padding: 0 1.1rem;
  border-radius: 999px;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.98), rgba(31, 57, 49, 0.98));
  color: #fff8ef;
}

.primary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.secondary-button {
  border: 1px solid rgba(47, 93, 80, 0.14);
  background: rgba(255, 255, 255, 0.84);
  color: var(--color-accent);
}

.ghost-button {
  color: var(--color-text-soft);
}

.onboarding-fade-enter-active,
.onboarding-fade-leave-active,
.step-fade-enter-active,
.step-fade-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.onboarding-fade-enter-from,
.onboarding-fade-leave-to,
.step-fade-enter-from,
.step-fade-leave-to {
  opacity: 0;
  transform: translateY(0.6rem);
}

@media (max-width: 960px) {
  .onboarding-shell {
    overflow-y: auto;
  }

  .onboarding-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .onboarding-aside {
    padding: 1.35rem 1rem 0.95rem;
  }

  .onboarding-aside h2 {
    max-width: 14rem;
    font-size: 1.34rem;
    line-height: 1.22;
  }

  .onboarding-main {
    min-height: 0;
    padding: 1rem 1rem calc(8rem + env(safe-area-inset-bottom));
  }

  .step-list {
    display: flex;
    gap: 0.55rem;
    margin-top: 1.2rem;
    overflow-x: auto;
    padding-bottom: 0.2rem;
    scrollbar-width: none;
  }

  .step-list::-webkit-scrollbar {
    display: none;
  }

  .step-list li {
    flex: 0 0 auto;
    padding: 0.45rem;
    border: 1px solid rgba(255, 248, 239, 0.12);
    border-radius: 999px;
  }

  .step-list li strong {
    display: none;
  }

  .step-list li span {
    width: 1.75rem;
    height: 1.75rem;
  }

  .step-panel h3 {
    font-size: 1.72rem;
    line-height: 1.18;
  }

  .step-panel {
    width: 100%;
  }

  .step-copy {
    width: 100%;
    font-size: 0.94rem;
    line-height: 1.68;
  }

  .field-block input,
  .field-block textarea {
    width: 100%;
  }

  .tag-groups {
    max-height: 11.5rem;
  }

  .step-actions {
    position: fixed;
    right: 1rem;
    bottom: calc(1rem + env(safe-area-inset-bottom));
    left: 1rem;
    z-index: 3;
    flex-wrap: wrap;
    justify-content: stretch;
    padding: 0;
    background: transparent;
    box-shadow: none;
  }

  .step-actions button {
    flex: 1 1 100%;
  }

  .toggle-card {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.95rem 1rem;
  }
}

@media (max-width: 640px) {
  .aside-eyebrow,
  .step-eyebrow {
    margin-bottom: 0.45rem;
    font-size: 0.72rem;
  }

  .step-panel h3 {
    font-size: 1.5rem;
  }

  .tag-group {
    padding: 0.85rem;
  }

  .chip {
    padding: 0.4rem 0.7rem;
    font-size: 0.9rem;
  }
}
</style>
