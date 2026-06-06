<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useGatewayStore } from '@/stores/gateway'
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()
const store = useGatewayStore()

onMounted(() => store.fetchServers())

const tabs = [
  { name: 'home', label: 'Home', path: '/' },
  { name: 'mcps', label: 'MCPs', path: '/mcps' },
  { name: 'market', label: 'Market', path: '/market' },
]
</script>

<template>
  <div class="min-h-screen bg-neutral-950 text-white">
    <!-- Tab bar -->
    <header class="border-b border-neutral-800">
      <nav class="max-w-5xl mx-auto flex items-center gap-1 px-4 pt-2">
        <RouterLink
          v-for="tab in tabs"
          :key="tab.name"
          :to="tab.path"
          :class="[
            'px-4 py-2 rounded-t-lg text-sm font-medium transition-colors',
            route.name === tab.name
              ? 'bg-neutral-900 text-white border border-neutral-800 border-b-transparent'
              : 'text-neutral-400 hover:text-white hover:bg-neutral-900/50',
          ]"
        >
          {{ t('tab.' + tab.name) }}
        </RouterLink>
      </nav>
    </header>

    <!-- Content -->
    <main class="max-w-5xl mx-auto px-4 py-6">
      <RouterView />
    </main>

    <!-- Status bar -->
    <footer class="fixed bottom-0 left-0 right-0 bg-neutral-900 border-t border-neutral-800">
      <div class="max-w-5xl mx-auto px-4 py-2 text-xs text-neutral-500 flex items-center gap-4">
        <span>{{ store.stats.installed }} {{ t('stats.installed').toLowerCase() }}</span>
        <span>{{ store.stats.enabled }} {{ t('stats.active').toLowerCase() }}</span>
        <span>{{ store.stats.catalog }} {{ t('stats.catalog').toLowerCase() }}</span>
      </div>
    </footer>
  </div>
</template>
