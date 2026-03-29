<script setup lang="ts">
import type { UserProfileSummary } from '../types/chat'

defineProps<{
  userProfile: UserProfileSummary
}>()
</script>

<template>
  <section class="settings-panel">
    <header class="panel-header">
      <p>个人设置</p>
      <h2>你的智能烹饪伙伴档案</h2>
      <span>这张大卡片后续可以复用到更多设置、确认和管理场景。</span>
    </header>

    <div class="settings-grid">
      <section class="settings-block">
        <h3>基础信息</h3>
        <label>
          <span>昵称</span>
          <input :value="userProfile.name" readonly />
        </label>
        <label>
          <span>邮箱</span>
          <input :value="userProfile.email" readonly />
        </label>
        <label>
          <span>下厨熟练度</span>
          <input :value="userProfile.level" readonly />
        </label>
      </section>

      <section class="settings-block">
        <h3>做饭偏好</h3>
        <label>
          <span>做饭节奏</span>
          <textarea readonly rows="3">{{ userProfile.availableTime }}</textarea>
        </label>
        <label>
          <span>厨房模式</span>
          <textarea readonly rows="3">{{ userProfile.kitchenMode }}</textarea>
        </label>
      </section>

      <section class="settings-block">
        <h3>长期记忆标签</h3>
        <div class="chip-row">
          <span v-for="preference in userProfile.preferences" :key="preference">{{ preference }}</span>
        </div>
      </section>

      <section class="settings-block">
        <h3>常用厨具</h3>
        <div class="chip-row">
          <span v-for="tool in userProfile.tools" :key="tool">{{ tool }}</span>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.settings-panel {
  display: grid;
  gap: 1.4rem;
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

.panel-header span {
  display: block;
  margin-top: 0.55rem;
  color: var(--color-text-soft);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.settings-block {
  padding: 1.15rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 1.2rem;
  background: rgba(255, 255, 255, 0.62);
}

.settings-block h3 {
  margin: 0 0 0.95rem;
  font-size: 1rem;
}

.settings-block label {
  display: grid;
  gap: 0.45rem;
  margin-bottom: 0.85rem;
}

.settings-block label:last-child {
  margin-bottom: 0;
}

.settings-block span {
  color: var(--color-text-soft);
  font-size: 0.84rem;
}

.settings-block input,
.settings-block textarea {
  width: 100%;
  padding: 0.8rem 0.9rem;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 0.95rem;
  color: var(--color-text);
  background: rgba(255, 252, 247, 0.92);
  resize: none;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.chip-row span {
  padding: 0.42rem 0.72rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
  color: var(--color-accent);
}

@media (max-width: 760px) {
  .panel-header h2 {
    font-size: 1.45rem;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
