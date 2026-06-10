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

const servers = computed(() => Object.keys(CREDENTIAL_SCHEMA))

// Detail view
const detailServer = ref('')
const detailKey = ref('')
const editValue = ref('')
const showValue = ref(false)
const editing = ref(false)

function hasValue(server: string, key: string): boolean {
  return store.credentials[server]?.[key] ?? false
}

function openDetail(server: string, key: string) {
  detailServer.value = server
  detailKey.value = key
  editValue.value = ''
  showValue.value = false
  editing.value = false
}

function closeDetail() {
  detailServer.value = ''
  detailKey.value = ''
  editValue.value = ''
}

async function saveDetail() {
  if (!detailServer.value || !detailKey.value || !editValue.value.trim()) return
  try {
    await store.setCredential(detailServer.value, detailKey.value, editValue.value)
    closeDetail()
  } catch { /* handled by store */ }
}

async function removeDetail() {
  if (!detailServer.value || !detailKey.value) return
  try {
    await store.deleteCredential(detailServer.value, detailKey.value)
    closeDetail()
  } catch { /* handled by store */ }
}

onMounted(() => { store.fetchCredentials() })
</script>

<template>
  <div class="overflow-x-auto">
    <div class="min-w-[48rem]">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-xl font-bold text-white">{{ t('credentials.title') }}</h1>
        <p class="text-sm text-neutral-400 mt-1">{{ t('credentials.hint') }}</p>
      </div>

      <!-- Toast -->
      <div v-if="store.message"
        class="mb-4 px-4 py-2 rounded-lg bg-blue-900/50 text-blue-200 border border-blue-700 flex justify-between items-center text-sm">
        <span>{{ store.message }}</span>
        <button @click="store.clearMessage()" class="ml-2 font-bold text-blue-300 hover:text-white">&times;</button>
      </div>

      <!-- Loading -->
      <div v-if="store.saving" class="text-sm text-neutral-400 mb-4">{{ t('loading') }}</div>

      <!-- Credentials list -->
      <div v-if="servers.length" class="divide-y divide-neutral-800 border border-neutral-800 rounded-lg overflow-hidden">
        <div
          v-for="server in servers"
          :key="server"
          class="bg-neutral-900/50"
        >
          <!-- Server header -->
          <div class="flex items-center justify-between px-4 py-3 bg-neutral-900">
            <span class="font-semibold text-white text-sm capitalize">{{ server }}</span>
            <span class="text-xs text-neutral-500">
              {{ CREDENTIAL_SCHEMA[server].length }} {{ CREDENTIAL_SCHEMA[server].length === 1 ? 'chave' : 'chaves' }}
            </span>
          </div>

          <!-- Keys list -->
          <div class="divide-y divide-neutral-800/50">
            <div
              v-for="key in CREDENTIAL_SCHEMA[server]"
              :key="key"
              class="flex items-center justify-between px-4 py-2.5 hover:bg-neutral-800/50 transition-colors"
            >
              <div class="flex items-center gap-3 min-w-0">
                <span class="text-sm font-mono text-neutral-300">{{ key }}</span>
                <span
                  class="text-xs px-1.5 py-0.5 rounded font-medium"
                  :class="hasValue(server, key)
                    ? 'bg-green-900/50 text-green-300'
                    : 'bg-neutral-800 text-neutral-500'"
                >
                  {{ hasValue(server, key) ? 'configurada' : 'pendente' }}
                </span>
              </div>
              <button
                class="px-3 py-1 text-xs rounded-md font-medium transition-colors"
                :class="hasValue(server, key)
                  ? 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'
                  : 'bg-primary/20 text-primary hover:bg-primary/30'"
                @click="openDetail(server, key)"
              >
                {{ hasValue(server, key) ? 'editar' : 'configurar' }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <p v-else class="text-neutral-500 py-8 text-center">{{ t('credentials.select_hint') }}</p>

      <!-- Edit/Detail Modal -->
      <Teleport to="body">
        <div v-if="detailServer" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/60" @click="closeDetail" />
          <div class="relative bg-neutral-800 border border-neutral-600 rounded-xl p-6 w-[32rem] shadow-2xl">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h3 class="text-lg font-bold text-white">{{ detailServer }}</h3>
                <p class="text-sm text-neutral-400 mt-1 font-mono">{{ detailKey }}</p>
              </div>
              <span
                class="text-xs px-2 py-1 rounded font-medium"
                :class="hasValue(detailServer, detailKey)
                  ? 'bg-green-900/50 text-green-300'
                  : 'bg-neutral-800 text-neutral-500'"
              >
                {{ hasValue(detailServer, detailKey) ? 'configurada' : 'pendente' }}
              </span>
            </div>

            <div class="space-y-4">
              <div>
                <label class="text-xs text-neutral-400 block mb-1">Valor</label>
                <div class="flex items-center gap-2">
                  <input
                    v-model="editValue"
                    :type="showValue ? 'text' : 'password'"
                    :placeholder="hasValue(detailServer, detailKey) ? 'Digite novo valor para substituir...' : t('credentials.value_placeholder')"
                    @focus="editing = true"
                    class="flex-1 bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors"
                  />
                  <button
                    class="px-3 py-2 rounded-lg text-sm bg-neutral-700 text-neutral-300 hover:bg-neutral-600 transition-colors"
                    @click="showValue = !showValue"
                  >
                    {{ showValue ? 'ocultar' : 'mostrar' }}
                  </button>
                </div>
              </div>
            </div>

            <div class="flex justify-between mt-6">
              <button
                v-if="hasValue(detailServer, detailKey)"
                class="px-4 py-2 rounded-lg text-sm font-medium bg-danger/20 text-red-300 hover:bg-red-800/50 transition-colors"
                :disabled="store.saving"
                @click="removeDetail"
              >
                {{ t('credentials.clear') }}
              </button>
              <div class="flex gap-3 ml-auto">
                <button
                  class="px-4 py-2 rounded-lg text-sm font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
                  @click="closeDetail"
                >
                  {{ t('market.close') }}
                </button>
                <button
                  class="px-4 py-2 rounded-lg text-sm font-bold bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
                  :disabled="!editValue.trim() || store.saving"
                  @click="saveDetail"
                >
                  {{ store.saving ? '...' : t('credentials.save') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </Teleport>
    </div>
  </div>
</template>
