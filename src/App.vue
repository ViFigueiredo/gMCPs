<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useGatewayStore } from '@/stores/gateway'
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()
const route = useRoute()
const store = useGatewayStore()

onMounted(() => {
  store.fetchServers()
  const saved = localStorage.getItem('theme')
  if (saved === 'light') document.documentElement.classList.add('light')
})

const isLight = ref(document.documentElement.classList.contains('light'))
const locales = ['pt-BR', 'en-US']
const langOpen = ref(false)

function toggleTheme() {
  document.documentElement.classList.toggle('light')
  isLight.value = document.documentElement.classList.contains('light')
  localStorage.setItem('theme', isLight.value ? 'light' : 'dark')
}

function setLocale(l: string) {
  locale.value = l
  localStorage.setItem('locale', l)
  langOpen.value = false
}

watch(langOpen, (v) => { if (!v) return; const close = (e: MouseEvent) => { langOpen.value = false; document.removeEventListener('click', close) }; setTimeout(() => document.addEventListener('click', close), 0) })

const tabs = [
  { name: 'home', label: 'Home', path: '/' },
  { name: 'mcps', label: 'MCPs', path: '/mcps' },
  { name: 'market', label: 'Market', path: '/market' },
  { name: 'integrations', label: 'Integrations', path: '/integrations' },
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

        <div class="ml-auto flex items-center gap-2">
          <!-- Language switcher -->
          <div class="relative">
            <button
              class="px-2 py-1.5 rounded text-xs font-medium text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
              @click="langOpen = !langOpen"
            >
              {{ locale }}
            </button>
            <div
              v-if="langOpen"
              class="absolute right-0 top-full mt-1 bg-neutral-900 border border-neutral-700 rounded-lg py-1 min-w-24 shadow-xl z-50"
            >
              <button
                v-for="l in locales"
                :key="l"
                class="block w-full text-left px-3 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800 transition-colors"
                :class="{ 'font-semibold text-white': locale === l }"
                @click="setLocale(l)"
              >
                {{ l }}
              </button>
            </div>
          </div>

          <!-- Theme toggle -->
          <button
            class="px-2 py-1.5 rounded text-xs font-medium text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
            @click="toggleTheme"
            :title="isLight ? 'Dark mode' : 'Light mode'"
          >
            {{ isLight ? '\u263E' : '\u2600' }}
          </button>
        </div>
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
