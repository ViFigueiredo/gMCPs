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

    <main class="max-w-5xl mx-auto px-4 py-6 pb-14">
      <RouterView />
    </main>

    <footer class="fixed bottom-0 left-0 right-0 bg-neutral-900 border-t border-neutral-800">
      <div class="max-w-5xl mx-auto px-4 py-2 text-xs flex items-center gap-4">
        <span class="text-neutral-500">
          {{ store.stats.installed }} {{ t('stats.installed').toLowerCase() }}
        </span>
        <span class="text-neutral-500">
          {{ store.stats.enabled }} {{ t('stats.active').toLowerCase() }}
        </span>
        <span class="text-neutral-500">
          {{ store.stats.catalog }} {{ t('stats.catalog').toLowerCase() }}
        </span>

        <span class="ml-auto flex items-center gap-2">
          <span v-if="store.loading" class="flex items-center gap-1.5 text-blue-400">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
            </span>
            <span>{{ t(store.statusKey!, { arg: store.statusArg }) }}</span>
          </span>
          <span v-else-if="store.error" class="text-red-400">
            {{ t('error.prefix') }}: {{ store.error }}
          </span>
          <span v-else class="text-green-500 flex items-center gap-1.5">
            <span class="inline-flex rounded-full h-1.5 w-1.5 bg-green-500" />
            {{ store.stats.catalog > 0 ? t('status.connected') : t('status.disconnected') }}
          </span>
        </span>
      </div>
    </footer>
  </div>
</template>
