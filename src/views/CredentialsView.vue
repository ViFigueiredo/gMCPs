<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useCredentialsStore } from '@/stores/credentials'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const store = useCredentialsStore()

const CREDENTIAL_SCHEMA: Record<string, string[]> = {
  neon: ['NEON_API_KEY'],
  exa: ['EXA_API_KEY'],
  sentry: ['SENTRY_AUTH_TOKEN'],
  github: ['GITHUB_PERSONAL_ACCESS_TOKEN'],
  dockerhub: ['HUB_PAT_TOKEN', 'dockerhub.username'],
  filesystem: ['filesystem.paths'],
}

const selectedServer = ref('')
const selectedKey = ref('')
const inputValue = ref('')
const showValue = ref(false)
const editing = ref(false)

const servers = computed(() => Object.keys(CREDENTIAL_SCHEMA))

function selectServer(server: string) {
  selectedServer.value = server
  selectedKey.value = CREDENTIAL_SCHEMA[server][0]
  inputValue.value = ''
  showValue.value = false
  editing.value = false
}

function selectKey(key: string) {
  selectedKey.value = key
  inputValue.value = ''
  showValue.value = false
  editing.value = false
}

async function save() {
  if (!selectedServer.value || !selectedKey.value || !inputValue.value.trim()) return
  try {
    await store.setCredential(selectedServer.value, selectedKey.value, inputValue.value)
    inputValue.value = ''
    editing.value = false
  } catch { /* message handled by store */ }
}

async function remove() {
  if (!selectedServer.value || !selectedKey.value) return
  try {
    await store.deleteCredential(selectedServer.value, selectedKey.value)
    inputValue.value = ''
  } catch { /* message handled by store */ }
}

function hasValue(server: string, key: string): boolean {
  return store.credentials[server]?.[key] ?? false
}

onMounted(() => {
  store.fetchCredentials()
})
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold mb-2">{{ t('credentials.title') }}</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">{{ t('credentials.hint') }}</p>

    <!-- Message toast -->
    <div v-if="store.message"
      class="mb-4 px-4 py-2 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 flex justify-between items-center">
      <span>{{ store.message }}</span>
      <button @click="store.clearMessage()" class="ml-2 font-bold">&times;</button>
    </div>

    <!-- Loading -->
    <div v-if="store.saving" class="text-sm text-gray-400 mb-4">{{ t('loading') }}</div>

    <!-- Server cards grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
      <button v-for="server in servers" :key="server" @click="selectServer(server)"
        :class="[
          'border rounded-lg p-4 text-center transition-all cursor-pointer text-neutral-700 dark:text-neutral-300',
          selectedServer === server
            ? 'border-blue-500 ring-2 ring-blue-300 dark:ring-blue-700'
            : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
        ]">
        <div class="font-medium text-sm mb-1">{{ server }}</div>
        <div class="flex justify-center gap-1 text-sm">
          <span v-for="key in CREDENTIAL_SCHEMA[server]" :key="key">
            {{ hasValue(server, key) ? '🔒' : '🔓' }}
          </span>
        </div>
      </button>
    </div>

    <!-- Detail form -->
    <div v-if="selectedServer" class="border border-gray-200 dark:border-gray-700 rounded-lg p-6 text-neutral-900 dark:text-neutral-100">
      <h3 class="text-lg font-semibold mb-2">{{ selectedServer }}</h3>

      <!-- Key selector -->
      <div class="flex gap-2 mb-4 flex-wrap">
        <button v-for="key in CREDENTIAL_SCHEMA[selectedServer]" :key="key"
          @click="selectKey(key)"
          :class="[
            'px-3 py-1 rounded text-sm border transition-colors',
            selectedKey === key
              ? 'bg-blue-500 text-white border-blue-500'
              : 'bg-gray-100 dark:bg-gray-800 text-neutral-700 dark:text-neutral-300 border-gray-300 dark:border-gray-600'
          ]">
          {{ key }}
          <span class="ml-1">{{ hasValue(selectedServer, key) ? '🔒' : '🔓' }}</span>
        </button>
      </div>

      <!-- Input field -->
      <div class="flex items-center gap-2 mb-4">
        <input :type="showValue ? 'text' : 'password'"
          v-model="inputValue"
          :placeholder="t('credentials.value_placeholder')"
          @focus="editing = true"
          class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 text-sm" />
        <button @click="showValue = !showValue"
          class="px-2 py-1 text-sm border rounded text-neutral-700 dark:text-neutral-300 hover:bg-gray-100 dark:hover:bg-gray-700 border-gray-300 dark:border-gray-600">
          {{ showValue ? '🙈' : '👁️' }}
        </button>
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2">
        <button @click="save" :disabled="!inputValue.trim() || store.saving"
          class="px-4 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ t('credentials.save') }}
        </button>
        <button @click="remove" :disabled="!hasValue(selectedServer, selectedKey) || store.saving"
          class="px-4 py-2 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ t('credentials.clear') }}
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-12 text-gray-400">
      {{ t('credentials.select_hint') }}
    </div>
  </div>
</template>