<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  PASSWORD_RULE,
  USERNAME_RULE,
  validateOptionalEmail,
  validatePassword,
  validateUsername,
} from '../constants/auth'
import { saveAuthSession } from '../state/auth'

const props = defineProps<{
  mode: 'login' | 'register'
}>()

const router = useRouter()

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const attemptedSubmit = ref(false)

const isLogin = computed(() => props.mode === 'login')
const pageTitle = computed(() => (isLogin.value ? '欢迎回来' : '欢迎加入 ChefMate'))
const pageDescription = computed(() =>
  isLogin.value
    ? '回到你的厨房工作台，继续当前的做饭任务和聊天记录。'
    : '创建一个新账号，让 ChefMate 记住你的偏好、菜谱和厨房节奏。',
)

const welcomeHighlights = computed(() =>
  isLogin.value
    ? ['继续未完成的烹饪步骤', '保留你的菜谱偏好和建议', '在一个工作台里完成推荐到开火']
    : ['建立你的长期烹饪偏好档案', '记录菜谱、备料与烹饪过程', '让 ChefMate 更快熟悉你的厨房节奏'],
)

const loginErrors = computed(() => ({
  username:
    attemptedSubmit.value && !validateUsername(loginForm.username)
      ? '用户名格式不符合要求'
      : '',
  password:
    attemptedSubmit.value && !validatePassword(loginForm.password)
      ? '密码格式不符合要求'
      : '',
}))

const registerErrors = computed(() => ({
  username:
    attemptedSubmit.value && !validateUsername(registerForm.username)
      ? '用户名格式不符合要求'
      : '',
  email:
    attemptedSubmit.value && !validateOptionalEmail(registerForm.email)
      ? '邮箱格式不正确'
      : '',
  password:
    attemptedSubmit.value && !validatePassword(registerForm.password)
      ? '密码格式不符合要求'
      : '',
  confirmPassword:
    attemptedSubmit.value && registerForm.confirmPassword !== registerForm.password
      ? '两次输入的密码不一致'
      : '',
}))

const registerUsernameState = computed(() => {
  const username = registerForm.username.trim()
  if (!username) {
    return {
      tone: 'neutral',
      message: USERNAME_RULE.hint,
    }
  }

  return validateUsername(username)
    ? {
        tone: 'success',
        message: '用户名符合规范',
      }
    : {
        tone: 'error',
        message: USERNAME_RULE.hint,
      }
})

const registerPasswordState = computed(() => {
  const password = registerForm.password
  if (!password) {
    return {
      tone: 'neutral',
      message: PASSWORD_RULE.hint,
    }
  }

  const hasLetter = /[A-Za-z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[~!@#$%^&*_\-+=.?]/.test(password)
  const isLengthValid =
    password.length >= PASSWORD_RULE.minLength && password.length <= PASSWORD_RULE.maxLength

  if (!isLengthValid || !hasLetter || !hasNumber) {
    return {
      tone: 'error',
      message: '强度较弱，请至少满足长度、字母和数字要求',
    }
  }

  if (password.length >= 12 && hasSpecial) {
    return {
      tone: 'success',
      message: '密码强度较高',
    }
  }

  return {
    tone: 'warning',
    message: '密码强度中等，可以增加长度或符号进一步提升',
  }
})

const registerConfirmState = computed(() => {
  if (!registerForm.confirmPassword) {
    return {
      tone: 'neutral',
      message: '需要与上面的密码保持一致',
    }
  }

  return registerForm.confirmPassword === registerForm.password
    ? {
        tone: 'success',
        message: '两次输入的密码一致',
      }
    : {
        tone: 'error',
        message: '两次输入的密码不一致',
      }
})

function switchMode(mode: 'login' | 'register') {
  attemptedSubmit.value = false
  void router.push({ name: mode === 'login' ? 'auth-login' : 'auth-register' })
}

function submitLogin() {
  attemptedSubmit.value = true
  if (loginErrors.value.username || loginErrors.value.password) {
    return
  }

  saveAuthSession({
    username: loginForm.username.trim(),
    loggedInAt: new Date().toISOString(),
    hasCompletedWorkspaceOnboarding: false,
    profileCompletedAt: null,
  })
  void router.push({ name: 'chat' })
}

function submitRegister() {
  attemptedSubmit.value = true
  if (
    registerErrors.value.username ||
    registerErrors.value.email ||
    registerErrors.value.password ||
    registerErrors.value.confirmPassword
  ) {
    return
  }

  saveAuthSession({
    username: registerForm.username.trim(),
    email: registerForm.email.trim() || null,
    loggedInAt: new Date().toISOString(),
    hasCompletedWorkspaceOnboarding: false,
    profileCompletedAt: null,
  })
  void router.push({ name: 'chat' })
}
</script>

<template>
  <section class="auth-shell">
    <div class="auth-grid">
      <aside class="welcome-panel">
        <div class="welcome-layer"></div>
        <Transition name="auth-copy-fade" mode="out-in">
          <div :key="mode" class="welcome-content">
            <p class="brand-tag">ChefMate</p>
            <h1>{{ pageTitle }}</h1>
            <p class="welcome-copy">{{ pageDescription }}</p>

            <div class="welcome-lines">
              <span>推荐</span>
              <span>备料</span>
              <span>烹饪</span>
              <span>记录</span>
            </div>

            <ul class="welcome-list">
              <li v-for="highlight in welcomeHighlights" :key="highlight">{{ highlight }}</li>
            </ul>
          </div>
        </Transition>
      </aside>

      <section class="form-panel">
        <div class="form-panel-inner">
          <div class="form-head">
            <p class="eyebrow">账号入口</p>
            <h2>{{ isLogin ? '登录 ChefMate' : '注册新账号' }}</h2>
          </div>

          <div class="mode-tabs">
            <button
              type="button"
              class="mode-tab"
              :class="{ active: isLogin }"
              @click="switchMode('login')"
            >
              登录
            </button>
            <button
              type="button"
              class="mode-tab"
              :class="{ active: !isLogin }"
              @click="switchMode('register')"
            >
              注册
            </button>
          </div>

          <Transition name="auth-form-fade" mode="out-in">
            <form v-if="isLogin" key="login" class="auth-form" @submit.prevent="submitLogin">
              <label class="field-block">
                <span>用户名</span>
                <input v-model="loginForm.username" autocomplete="username" placeholder="输入用户名" />
                <small class="field-note neutral">{{ USERNAME_RULE.hint }}</small>
                <em v-if="loginErrors.username">{{ loginErrors.username }}</em>
              </label>

              <label class="field-block">
                <span>密码</span>
                <input
                  v-model="loginForm.password"
                  type="password"
                  autocomplete="current-password"
                  placeholder="输入密码"
                />
                <small class="field-note neutral">{{ PASSWORD_RULE.hint }}</small>
                <em v-if="loginErrors.password">{{ loginErrors.password }}</em>
              </label>

              <button type="submit" class="submit-button">登录</button>
            </form>

            <form v-else key="register" class="auth-form" @submit.prevent="submitRegister">
              <label class="field-block">
                <span>用户名</span>
                <input v-model="registerForm.username" autocomplete="username" placeholder="创建用户名" />
                <small class="field-note" :class="registerUsernameState.tone">{{ registerUsernameState.message }}</small>
                <em v-if="registerErrors.username">{{ registerErrors.username }}</em>
              </label>

              <label class="field-block">
                <span>邮箱（可选）</span>
                <input v-model="registerForm.email" autocomplete="email" placeholder="输入邮箱" />
                <small class="field-note neutral">可留空；如果填写，需要符合标准邮箱格式</small>
                <em v-if="registerErrors.email">{{ registerErrors.email }}</em>
              </label>

              <label class="field-block">
                <span>密码</span>
                <input
                  v-model="registerForm.password"
                  type="password"
                  autocomplete="new-password"
                  placeholder="创建密码"
                />
                <small class="field-note" :class="registerPasswordState.tone">{{ registerPasswordState.message }}</small>
                <em v-if="registerErrors.password">{{ registerErrors.password }}</em>
              </label>

              <label class="field-block">
                <span>确认密码</span>
                <input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  autocomplete="new-password"
                  placeholder="再次输入密码"
                />
                <small class="field-note" :class="registerConfirmState.tone">{{ registerConfirmState.message }}</small>
                <em v-if="registerErrors.confirmPassword">{{ registerErrors.confirmPassword }}</em>
              </label>

              <button type="submit" class="submit-button">注册</button>
            </form>
          </Transition>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  padding: 0;
  background:
    radial-gradient(circle at top left, rgba(229, 143, 91, 0.2), transparent 22rem),
    radial-gradient(circle at bottom right, rgba(47, 93, 80, 0.14), transparent 26rem),
    linear-gradient(180deg, rgba(255, 248, 239, 0.96), rgba(244, 238, 228, 0.94));
}

.auth-grid {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1.12fr) minmax(22rem, 28rem);
  overflow: hidden;
  background: rgba(255, 252, 247, 0.82);
}

.welcome-panel {
  position: relative;
  display: grid;
  overflow: hidden;
  padding: 3.4rem;
  align-items: end;
  background:
    linear-gradient(145deg, rgba(41, 80, 69, 0.96), rgba(28, 53, 46, 0.96)),
    var(--color-accent);
  color: #fff8ef;
}

.welcome-layer {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.14), transparent 18rem),
    radial-gradient(circle at 80% 18%, rgba(229, 143, 91, 0.22), transparent 16rem),
    linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.04) 48%, transparent 100%);
}

.welcome-content {
  position: relative;
  z-index: 1;
  max-width: 30rem;
}

.brand-tag,
.eyebrow {
  margin: 0 0 0.65rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.76rem;
}

.welcome-content h1,
.form-head h2 {
  margin: 0;
  line-height: 1.05;
}

.welcome-content h1 {
  font-size: clamp(2.6rem, 4vw, 4.4rem);
}

.welcome-copy {
  max-width: 24rem;
  margin: 1rem 0 0;
  color: rgba(255, 248, 239, 0.78);
  font-size: 1rem;
  line-height: 1.75;
}

.welcome-lines {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1.4rem;
}

.welcome-lines span {
  padding: 0.38rem 0.72rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 0.8rem;
}

.welcome-list {
  display: grid;
  gap: 0.7rem;
  margin: 2rem 0 0;
  padding: 0;
  list-style: none;
}

.welcome-list li {
  position: relative;
  padding-left: 1rem;
  color: rgba(255, 248, 239, 0.88);
}

.welcome-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.72rem;
  width: 0.34rem;
  height: 0.34rem;
  border-radius: 999px;
  background: rgba(229, 143, 91, 0.88);
}

.form-panel {
  display: grid;
  place-items: center;
  padding: 2rem;
  background: rgba(255, 252, 247, 0.92);
}

.form-panel-inner {
  width: min(100%, 25rem);
}

.form-head h2 {
  font-size: 2rem;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
  margin-top: 1.5rem;
  padding: 0.32rem;
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.08);
}

.mode-tab {
  min-height: 2.9rem;
  border-radius: 999px;
  color: var(--color-text-soft);
  cursor: pointer;
}

.mode-tab.active {
  background: rgba(255, 255, 255, 0.96);
  color: var(--color-accent);
  box-shadow: 0 10px 22px rgba(26, 39, 35, 0.08);
}

.auth-form {
  display: grid;
  gap: 1rem;
  margin-top: 1.4rem;
}

.field-block {
  display: grid;
  gap: 0.45rem;
}

.field-block span {
  font-size: 0.9rem;
  font-weight: 600;
}

.field-block input {
  min-height: 3.2rem;
  padding: 0 1rem;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.86);
  color: var(--color-text);
}

.field-block input:focus {
  outline: none;
  border-color: rgba(47, 93, 80, 0.3);
  box-shadow: 0 0 0 4px rgba(47, 93, 80, 0.08);
}

.field-block small {
  font-size: 0.78rem;
  line-height: 1.5;
}

.field-note.neutral {
  color: var(--color-text-soft);
}

.field-note.success {
  color: var(--color-accent);
}

.field-note.warning {
  color: #9c6228;
}

.field-note.error {
  color: #b34e2b;
}

.field-block em {
  color: #b34e2b;
  font-size: 0.8rem;
  font-style: normal;
}

.submit-button {
  min-height: 3.2rem;
  margin-top: 0.3rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, rgba(47, 93, 80, 0.98), rgba(31, 57, 49, 0.98));
  color: #fff9f1;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 16px 34px rgba(27, 50, 44, 0.16);
}

.auth-copy-fade-enter-active,
.auth-copy-fade-leave-active,
.auth-form-fade-enter-active,
.auth-form-fade-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.auth-copy-fade-enter-from,
.auth-copy-fade-leave-to,
.auth-form-fade-enter-from,
.auth-form-fade-leave-to {
  opacity: 0;
  transform: translateY(0.6rem);
}

@media (max-width: 920px) {
  .auth-grid {
    min-height: 100vh;
    grid-template-columns: 1fr;
  }

  .welcome-panel {
    display: none;
  }

  .form-panel {
    min-height: 100vh;
    padding: 1.35rem;
  }

  .form-panel-inner {
    width: min(100%, 28rem);
  }

  .form-head h2 {
    font-size: 1.7rem;
  }
}
</style>
