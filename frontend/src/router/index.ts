import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../state/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/auth/login',
    },
    {
      path: '/auth/login',
      name: 'auth-login',
      component: {
        template: '<div />',
      },
    },
    {
      path: '/auth/register',
      name: 'auth-register',
      component: {
        template: '<div />',
      },
    },
    {
      path: '/chat/:conversationId?',
      name: 'chat',
      component: {
        template: '<div />',
      },
    },
    {
      path: '/recipes',
      name: 'recipes',
      component: {
        template: '<div />',
      },
    },
    {
      path: '/recipes/:recipeId',
      name: 'recipe-detail',
      component: {
        template: '<div />',
      },
    },
  ],
})

router.beforeEach((to) => {
  const authenticated = isAuthenticated()
  const isAuthRoute = to.name === 'auth-login' || to.name === 'auth-register'

  if (!authenticated && !isAuthRoute) {
    return { name: 'auth-login' }
  }

  if (authenticated && isAuthRoute) {
    return { name: 'chat' }
  }

  return true
})

export default router
