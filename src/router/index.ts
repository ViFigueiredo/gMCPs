import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/mcps', name: 'mcps', component: () => import('@/views/McpsView.vue') },
    { path: '/market', name: 'market', component: () => import('@/views/MarketView.vue') },
    { path: '/integrations', name: 'integrations', component: () => import('@/views/IntegrationsView.vue') },
  ],
})

export default router
