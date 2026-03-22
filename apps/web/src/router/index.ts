import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: () => import('../views/LandingPage.vue')
  },
  {
    path: '/worlds',
    name: 'worlds',
    component: () => import('../components/StoryList.vue')
  },
  {
    path: '/create',
    name: 'create',
    component: () => import('../components/StoryCreator.vue')
  },
  {
    path: '/discover',
    name: 'discover',
    component: () => import('../views/PublicDiscoveryPage.vue')
  },
  {
    path: '/share/:id',
    name: 'share',
    component: () => import('../views/PublicStoryPage.vue'),
    props: route => ({ storyId: route.params.id })
  },
  {
    path: '/world/:id',
    name: 'world',
    component: () => import('../components/StoryDetail.vue'),
    props: route => ({ originalStoryId: route.params.id })
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../components/Settings.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }

    if (to.name === 'world' || from.name === 'world') {
      return false
    }

    return { top: 0 }
  }
})

export default router
