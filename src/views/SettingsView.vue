<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api'
import type { AppConfig } from '@/types'

const { t, locale } = useI18n()
const config = ref<AppConfig>({ theme: 'dark', language: 'pt-BR', share_default: false })
const loading = ref(true)
const saving = ref(false)
const saved = ref(false)

async function fetchConfig() {
  loading.value = true
  try {
    config.value = await api.config.get()
  } catch { /* use default */ }
  loading.value = false
}

async function saveConfig() {
  saving.value = true
  saved.value = false
  try {
    config.value = await api.config.update({
      theme: config.value.theme,
      language: config.value.language,
      share_default: config.value.share_default,
    })
    locale.value = config.value.language
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch { /* ignore */ }
  saving.value = false
}

onMounted(fetchConfig)
</script>

<template>
  <div class="max-w-2xl">
    <h2 class="text-xl font-bold text-white mb-6">{{ t('config.title') }}</h2>

    <div v-if="loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

    <div v-else class="space-y-6">
      <!-- Language -->
      <div class="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
        <label class="block text-sm font-medium text-white mb-2">{{ t('config.language') }}</label>
        <select
          v-model="config.language"
          class="w-full max-w-xs bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white outline-none focus:border-primary transition-colors"
        >
          <option value="pt-BR">Português (BR)</option>
          <option value="en-US">English (US)</option>
        </select>
      </div>

      <!-- Theme -->
      <div class="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
        <label class="block text-sm font-medium text-white mb-2">{{ t('config.theme') }}</label>
        <div class="flex gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="radio" v-model="config.theme" value="dark" class="accent-primary" />
            <span class="text-neutral-300">{{ t('config.theme_dark') }}</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="radio" v-model="config.theme" value="light" class="accent-primary" />
            <span class="text-neutral-300">{{ t('config.theme_light') }}</span>
          </label>
        </div>
      </div>

      <!-- Share default -->
      <div class="bg-neutral-900 rounded-lg border border-neutral-800 p-4">
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" v-model="config.share_default" class="w-4 h-4 accent-primary" />
          <span class="text-sm text-white">{{ t('config.share_default') }}</span>
        </label>
      </div>

      <!-- Save -->
      <div class="flex items-center gap-3">
        <button
          class="px-6 py-2 rounded-lg text-sm font-bold bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
          :disabled="saving"
          @click="saveConfig"
        >
          {{ saving ? '...' : t('config.save') }}
        </button>
        <span v-if="saved" class="text-success text-sm">{{ t('config.saved') }}</span>
      </div>
    </div>
  </div>
</template>
