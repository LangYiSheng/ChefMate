<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { TagCatalog, TagCategoryKey, UserProfileSummary } from '../types/chat'

const props = defineProps<{
  tagCatalog: TagCatalog
  userProfile: UserProfileSummary
}>()

const emit = defineEmits<{
  updateAllowAutoUpdate: [value: boolean]
  updateAutoStartStepTimer: [value: boolean]
  saveProfile: [payload: {
    allowAutoUpdate: boolean
    autoStartStepTimer: boolean
    voiceWakeWordEnabled: boolean
    cookingPreferenceText: string
    tagSelections: TagCatalog
    displayName: string
    email: string
  }]
  logout: []
}>()

const tabs = [
  { id: 'profile', label: '档案' },
  { id: 'settings', label: '设置' },
  { id: 'account', label: '账户' },
  { id: 'about', label: '关于' },
] as const

const categoryMeta: Array<{ key: TagCategoryKey; label: string }> = [
  { key: 'flavor', label: '口味' },
  { key: 'method', label: '做法' },
  { key: 'scene', label: '场景' },
  { key: 'health', label: '健康' },
  { key: 'time', label: '时间' },
  { key: 'tool', label: '工具' },
]

const activeTab = ref<(typeof tabs)[number]['id']>('profile')
const selectedTags = ref<TagCatalog>({
  flavor: [],
  method: [],
  scene: [],
  health: [],
  time: [],
  tool: [],
})
const cookingPreferenceText = ref('')
const allowAutoUpdate = ref(true)
const autoStartStepTimer = ref(false)
const voiceWakeWordEnabled = ref(false)
const displayName = ref('')
const accountEmail = ref('')
const logoutConfirmOpen = ref(false)

const selectedTagCount = computed(() => Object.values(selectedTags.value).flat().length)

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

function toggleAllowAutoUpdate() {
  allowAutoUpdate.value = !allowAutoUpdate.value
  emit('updateAllowAutoUpdate', allowAutoUpdate.value)
}

function toggleAutoStartStepTimer() {
  autoStartStepTimer.value = !autoStartStepTimer.value
  emit('updateAutoStartStepTimer', autoStartStepTimer.value)
}

function toggleVoiceWakeWord() {
  voiceWakeWordEnabled.value = !voiceWakeWordEnabled.value
}

function openLogoutConfirm() {
  logoutConfirmOpen.value = true
}

function closeLogoutConfirm() {
  logoutConfirmOpen.value = false
}

function confirmLogout() {
  logoutConfirmOpen.value = false
  emit('logout')
}

function saveProfile() {
  emit('saveProfile', {
    allowAutoUpdate: allowAutoUpdate.value,
    autoStartStepTimer: autoStartStepTimer.value,
    voiceWakeWordEnabled: voiceWakeWordEnabled.value,
    cookingPreferenceText: cookingPreferenceText.value.trim(),
    tagSelections: selectedTags.value,
    displayName: displayName.value.trim(),
    email: accountEmail.value.trim(),
  })
}

watch(
  () => [props.userProfile, props.tagCatalog] as const,
  ([profile]) => {
    selectedTags.value = normalizeSelections(profile.tagSelections)
    cookingPreferenceText.value = profile.cookingPreferenceText
    allowAutoUpdate.value = profile.allowAutoUpdate
    autoStartStepTimer.value = profile.autoStartStepTimer
    voiceWakeWordEnabled.value = profile.voiceWakeWordEnabled
    displayName.value = profile.name
    accountEmail.value = profile.email
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <section class="settings-panel">
    <header class="panel-header">
      <p>个人设置</p>
      <h2>你的智能烹饪伙伴档案</h2>
    </header>

    <div class="settings-layout">
      <nav class="tab-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="tab-button"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div class="tab-content">
        <div v-if="activeTab === 'profile'" class="content-scroll hover-scroll">
          <section class="settings-stack">
            <details class="fold-card">
              <summary class="fold-summary">
                <div class="fold-summary-main">
                  <strong>长期记忆标签</strong>
                  <p>ChefMate 会通过标签来向你推荐菜谱，已选 {{ selectedTagCount }} 个长期记忆标签</p>
                </div>
                <span class="fold-arrow" aria-hidden="true"></span>
              </summary>

              <div class="fold-content">
                <div v-for="category in categoryMeta" :key="category.key" class="tag-group">
                  <div class="tag-group-head">
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
                </div>
              </div>
            </details>

            <section class="plain-card">
              <div class="section-head">
                <strong>做饭偏好文本</strong>
                <p>写下你的口味、节奏和厨房习惯，方便 ChefMate 给出更贴合的建议</p>
              </div>

              <label class="field-block">
                <span>偏好描述</span>
                <textarea v-model="cookingPreferenceText" rows="6"></textarea>
              </label>

              <div class="action-row">
                <button type="button" class="primary-button" @click="saveProfile">保存偏好档案</button>
              </div>
            </section>
          </section>
        </div>

        <div v-else-if="activeTab === 'settings'" class="content-scroll hover-scroll">
          <section class="settings-stack">
            <section class="plain-card">
              <div class="toggle-row">
                <div>
                  <strong>允许 ChefMate 更新偏好档案</strong>
                  <p>关闭后ChefMate将没有权限修改你的偏好信息</p>
                </div>

                <button
                  type="button"
                  class="toggle-button"
                  :class="{ active: allowAutoUpdate }"
                  @click="toggleAllowAutoUpdate"
                >
                  <span></span>
                </button>
              </div>

              <div class="toggle-row">
                <div>
                  <strong>到步骤时自动开启计时器</strong>
                  <p>进入带计时的步骤后，会自动在右上角启动对应计时器。</p>
                </div>

                <button
                  type="button"
                  class="toggle-button"
                  :class="{ active: autoStartStepTimer }"
                  @click="toggleAutoStartStepTimer"
                >
                  <span></span>
                </button>
              </div>

              <div class="toggle-row">
                <div>
                  <strong>开启“小厨小厨”唤醒</strong>
                  <p>需要你手动进入待命后，才能通过命令词唤醒正式录音。</p>
                </div>

                <button
                  type="button"
                  class="toggle-button"
                  :class="{ active: voiceWakeWordEnabled }"
                  @click="toggleVoiceWakeWord"
                >
                  <span></span>
                </button>
              </div>

              <div class="action-row">
                <button type="button" class="primary-button" @click="saveProfile">保存设置</button>
              </div>
            </section>
          </section>
        </div>

        <div v-else-if="activeTab === 'account'" class="content-scroll hover-scroll">
          <section class="settings-stack">
            <section class="account-card">
              <div class="account-avatar">{{ displayName.slice(0, 1) }}</div>
              <div>
                <strong>{{ displayName }}</strong>
                <p>@{{ userProfile.account }}</p>
              </div>
            </section>

            <section class="plain-card">
              <div class="section-head">
                <strong>账户信息</strong>
                <p>查看个人信息，或更新显示名称、邮箱与密码</p>
              </div>

              <label class="field-block">
                <span>账户显示名称</span>
                <input v-model="displayName" />
              </label>

              <div class="static-field">
                <span>账号</span>
                <strong>@{{ userProfile.account }}</strong>
              </div>

              <label class="field-block">
                <span>邮箱（可选）</span>
                <input v-model="accountEmail" />
              </label>

              <div class="action-row">
                <button type="button" class="primary-button" @click="saveProfile">保存账户信息</button>
                <button type="button" class="secondary-button">重设密码</button>
                <button type="button" class="danger-button" @click="openLogoutConfirm">退出登录</button>
              </div>
            </section>
          </section>
        </div>

        <div v-else class="about-wrap">
          <section class="about-card">
            <h3>ChefMate</h3>
            <p>一款智能烹饪助手</p>
            <a class="github-link" href="https://github.com/LangYiSheng/ChefMate" target="_blank" rel="noreferrer">
              Github 仓库
            </a>
          </section>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="confirm-fade">
        <div v-if="logoutConfirmOpen" class="confirm-shell" @click="closeLogoutConfirm">
          <div class="confirm-card" @click.stop>
            <h3>确认退出登录？</h3>
            <p>退出后将返回未登录状态，你可以稍后重新登录继续使用 ChefMate。</p>
            <div class="confirm-actions">
              <button type="button" class="secondary-button" @click="closeLogoutConfirm">取消</button>
              <button type="button" class="danger-button" @click="confirmLogout">确认退出</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.settings-panel {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 1.25rem;
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
  font-size: 1.9rem;
  line-height: 1.1;
}

.settings-layout {
  display: grid;
  min-height: 0;
  grid-template-columns: 12rem minmax(0, 1fr);
  gap: 1rem;
}

.tab-nav {
  display: grid;
  gap: 0.55rem;
  align-self: start;
}

.tab-button {
  padding: 0.9rem 0.95rem;
  border: 1px solid rgba(47, 93, 80, 0.1);
  border-radius: 1rem;
  color: var(--color-text-soft);
  text-align: left;
  background: rgba(255, 255, 255, 0.52);
  cursor: pointer;
}

.tab-button.active {
  border-color: rgba(47, 93, 80, 0.22);
  color: var(--color-accent);
  background: rgba(247, 252, 249, 0.95);
  box-shadow: 0 14px 28px rgba(29, 43, 39, 0.06);
}

.tab-content {
  min-height: 0;
  overflow: hidden;
}

.content-scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.35rem;
}

.settings-stack {
  display: grid;
  gap: 0.95rem;
}

.fold-card,
.plain-card,
.account-card,
.about-card {
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1.25rem;
  background: rgba(255, 255, 255, 0.62);
}

.fold-card {
  overflow: hidden;
}

.fold-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  list-style: none;
  padding: 1.15rem 1.2rem;
  cursor: pointer;
}

.fold-summary::-webkit-details-marker {
  display: none;
}

.fold-summary-main {
  min-width: 0;
}

.fold-summary strong {
  display: block;
  font-size: 1rem;
}

.fold-summary p {
  margin: 0.35rem 0 0;
  color: var(--color-text-soft);
}

.fold-arrow {
  position: relative;
  flex: 0 0 auto;
  width: 0.8rem;
  height: 0.8rem;
  transition: transform 180ms ease;
}

.fold-arrow::before {
  content: '';
  position: absolute;
  inset: 0;
  border-right: 2px solid rgba(47, 93, 80, 0.62);
  border-bottom: 2px solid rgba(47, 93, 80, 0.62);
  transform: rotate(45deg) translate(-8%, -8%);
  transform-origin: center;
}

.fold-card[open] .fold-arrow {
  transform: rotate(180deg);
}

.fold-content {
  display: grid;
  gap: 1rem;
  padding: 0 1.2rem 1.2rem;
}

.plain-card {
  display: grid;
  gap: 1rem;
  padding: 1.15rem 1.2rem;
}

.section-head strong {
  display: block;
  font-size: 1rem;
}

.section-head p {
  margin: 0.35rem 0 0;
  color: var(--color-text-soft);
}

.tag-group {
  padding-top: 1.25rem;
  border-top: 1px solid rgba(47, 93, 80, 0.08);
}

.tag-group:first-of-type {
  padding-top: 0;
  border-top: 0;
}

.tag-group-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.7rem;
}

.tag-group-head span {
  color: var(--color-text-soft);
  font-size: 0.82rem;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.chip-row-muted {
  margin-top: 0.7rem;
}

.chip {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  padding: 0.42rem 0.72rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--color-accent);
  cursor: pointer;
}

.chip-active {
  background: rgba(47, 93, 80, 0.1);
}

.chip b {
  font-weight: 500;
}

.field-block {
  display: grid;
  gap: 0.5rem;
}

.field-block span,
.static-field span {
  color: var(--color-text-soft);
  font-size: 0.84rem;
}

.field-block input,
.field-block textarea {
  width: 100%;
  padding: 0.8rem 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 0.95rem;
  color: var(--color-text);
  background: rgba(255, 252, 247, 0.92);
  resize: none;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.toggle-row p {
  margin: 0.35rem 0 0;
  color: var(--color-text-soft);
}

.toggle-button {
  position: relative;
  flex: 0 0 auto;
  width: 3.4rem;
  height: 2rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.14);
  cursor: pointer;
}

.toggle-button span {
  position: absolute;
  top: 0.2rem;
  left: 0.2rem;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 999px;
  background: #fffdf8;
  box-shadow: 0 10px 22px rgba(29, 43, 39, 0.12);
  transition: transform 180ms ease;
}

.toggle-button.active {
  background: rgba(47, 93, 80, 0.94);
}

.toggle-button.active span {
  transform: translateX(1.4rem);
}

.account-card {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  padding: 1rem 1.15rem;
}

.account-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  background: rgba(47, 93, 80, 0.1);
  color: var(--color-accent);
  font-size: 1rem;
  font-weight: 700;
}

.account-card p {
  margin: 0.25rem 0 0;
  color: var(--color-text-soft);
}

.static-field {
  display: grid;
  gap: 0.35rem;
}

.static-field strong {
  font-size: 1rem;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.primary-button,
.secondary-button,
.danger-button,
.github-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.68rem 1rem;
  border-radius: 999px;
  text-decoration: none;
}

.primary-button {
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.96), rgba(32, 57, 49, 0.96));
  color: #fef7ef;
}

.secondary-button,
.github-link {
  border: 1px solid rgba(47, 93, 80, 0.12);
  background: rgba(255, 255, 255, 0.76);
  color: var(--color-accent);
}

.danger-button {
  border: 1px solid rgba(152, 70, 56, 0.16);
  background: rgba(152, 70, 56, 0.08);
  color: #8f4638;
}

.confirm-shell {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(18, 26, 24, 0.3);
  backdrop-filter: blur(8px);
}

.confirm-card {
  width: min(100%, 25rem);
  padding: 1.35rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1.3rem;
  background: rgba(255, 252, 247, 0.98);
  box-shadow: 0 22px 48px rgba(20, 28, 26, 0.18);
}

.confirm-card h3 {
  margin: 0;
  font-size: 1.15rem;
}

.confirm-card p {
  margin: 0.6rem 0 0;
  color: var(--color-text-soft);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
  margin-top: 1.2rem;
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 180ms ease;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.about-wrap {
  display: grid;
  height: 100%;
  place-items: center;
}

.about-card {
  display: grid;
  gap: 1.2rem;
  place-items: center;
  padding: 2.4rem;
  text-align: center;
}

.about-card h3 {
  margin: 0;
  font-size: 2rem;
}

.about-card p {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 1.1rem;
}

@media (max-width: 760px) {
  .panel-header h2 {
    font-size: 1.45rem;
  }

  .settings-layout {
    grid-template-columns: 1fr;
  }

  .tab-nav {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .tab-button {
    text-align: center;
  }

  .toggle-row {
    flex-direction: column;
    align-items: stretch;
  }

  .about-card {
    padding: 1.6rem 1rem;
  }
}
</style>
