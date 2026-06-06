<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { api } from '@/api'
import type { Server } from '@/types'

const store = useGatewayStore()
const { t } = useI18n()
const search = ref('')
const selected = ref(new Set<string>())
const detailServer = ref<Server | null>(null)
const dialog = ref<{ show: boolean; title: string; message: string; action: () => Promise<void> }>({
  show: false,
  title: '',
  message: '',
  action: async () => {},
})

onMounted(() => store.fetchServers())

const catalogServers = computed(() => {
  let list = store.servers
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(
      s => s.name.includes(q) || s.title.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q),
    )
  }
  return list
})

const hasSelection = computed(() => selected.value.size > 0)

function toggleSelect(name: string) {
  const s = new Set(selected.value)
  if (s.has(name)) s.delete(name)
  else s.add(name)
  selected.value = s
}

function selectAll() {
  if (selected.value.size === catalogServers.value.length) {
    selected.value.clear()
  } else {
    selected.value = new Set(catalogServers.value.map(s => s.name))
  }
}

function pendingNames(): string[] {
  return Array.from(selected.value)
    .filter(n => !store.servers.find(s => s.name === n)?.installed)
}

async function installSelected() {
  if (!hasSelection.value) return
  const names = pendingNames()
  if (!names.length) return
  selected.value.clear()
  for (const name of names) {
    try { await store.install(name) }
    catch { /* handled by store.error */ }
  }
}

async function showDetail(name: string) {
  try {
    detailServer.value = await api.servers.detail(name)
  } catch {
    const s = store.servers.find(x => x.name === name)
    detailServer.value = s || null
  }
}

function closeDetail() {
  detailServer.value = null
}

function confirmAction(s: { name: string; installed: boolean }) {
  if (s.installed) {
    dialog.value = {
      show: true,
      title: t('market.detail_remove'),
      message: `${t('market.detail_remove')} '${s.name}'?`,
      action: async () => { await store.uninstall(s.name) },
    }
  }
}

async function handleDialog() {
  const a = dialog.value.action
  dialog.value.show = false
  await a()
  closeDetail()
}
</script>

<template>
  <div>
    <!-- Search + Install button -->
    <div class="flex items-center gap-3 mb-4">
      <input
        v-model="search"
        type="text"
        :placeholder="t('market.search')"
        class="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2 text-white placeholder-neutral-500 outline-none focus:border-blue-500 transition-colors"
      />
      <button
        :disabled="!hasSelection"
        class="px-5 py-2 rounded-lg text-sm font-bold transition-colors"
        :class="hasSelection ? 'bg-blue-600 text-white hover:bg-blue-500 cursor-pointer' : 'bg-neutral-800 text-neutral-600 cursor-not-allowed'"
        @click="installSelected"
      >
        {{ t('market.install_btn') }} {{ hasSelection ? `(${selected.size})` : '' }}
      </button>
    </div>

    <div v-if="store.loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

    <!-- Table header -->
    <div class="grid grid-cols-[2.5rem_6rem_minmax(0,1fr)_auto] gap-3 px-4 py-2 text-sm text-neutral-500 font-semibold border-b border-neutral-700 items-center">
      <input
        type="checkbox"
        :checked="catalogServers.length > 0 && selected.size === catalogServers.length"
        :indeterminate="selected.size > 0 && selected.size < catalogServers.length"
        class="w-4 h-4 accent-blue-500 cursor-pointer"
        @click="selectAll"
      />
      <span>Status</span>
      <span>Servidor</span>
      <span>Ações</span>
    </div>

    <!-- Server rows -->
    <div v-if="catalogServers.length" class="divide-y divide-neutral-800">
      <div
        v-for="s in catalogServers"
        :key="s.name"
        class="grid grid-cols-[2.5rem_6rem_minmax(0,1fr)_auto] gap-3 px-4 py-3 items-center hover:bg-neutral-800/50 transition-colors"
      >
        <input
          type="checkbox"
          :checked="selected.has(s.name)"
          class="w-4 h-4 accent-blue-500 cursor-pointer"
          @click="toggleSelect(s.name)"
        />
        <span :class="s.installed ? 'text-green-400' : 'text-neutral-500'">
          {{ s.installed ? t('market.status_installed') : t('market.status_available') }}
        </span>
        <div class="min-w-0">
          <span class="font-medium text-white">{{ s.name }}</span>
          <span v-if="s.secrets" class="ml-2 text-yellow-400 text-xs" title="Requer API key">*</span>
          <p class="text-xs text-neutral-500 truncate">{{ s.desc }}</p>
        </div>
        <button
          class="px-3 py-1 text-xs rounded-md font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors cursor-pointer"
          @click="showDetail(s.name)"
        >
          {{ t('market.details') }}
        </button>
      </div>
    </div>
    <p v-else class="text-neutral-500 py-8 text-center">
      {{ search ? t('market.no_results') : t('market.empty') }}
    </p>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="detailServer" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="closeDetail" />
        <div class="relative bg-neutral-800 border border-neutral-600 rounded-xl p-6 w-[32rem] max-h-[80vh] overflow-y-auto shadow-2xl">
          <div class="flex items-start justify-between mb-4">
            <div>
              <h3 class="text-xl font-bold text-white">{{ detailServer.name }}</h3>
              <p v-if="detailServer.title" class="text-sm text-neutral-400 mt-1">{{ detailServer.title }}</p>
            </div>
            <span
              :class="detailServer.installed ? 'text-green-400' : 'text-neutral-500'"
              class="text-sm font-medium"
            >
              {{ detailServer.installed ? t('market.status_installed') : t('market.status_available') }}
            </span>
          </div>

          <div class="space-y-4">
            <div>
              <h4 class="text-xs text-neutral-500 uppercase tracking-wide mb-1">{{ t('market.detail_desc') }}</h4>
              <p class="text-neutral-200 text-sm leading-relaxed whitespace-pre-wrap">{{ detailServer.desc || t('market.detail_no_desc') }}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <h4 class="text-xs text-neutral-500 uppercase tracking-wide mb-1">{{ t('market.detail_status') }}</h4>
                <p class="text-sm">
                  <span :class="detailServer.enabled ? 'text-green-400' : 'text-neutral-400'">
                    {{ detailServer.enabled ? 'Ativo' : 'Inativo' }}
                  </span>
                </p>
              </div>
              <div>
                <h4 class="text-xs text-neutral-500 uppercase tracking-wide mb-1">{{ t('market.detail_api_key') }}</h4>
                <p class="text-sm">
                  <span :class="detailServer.secrets ? 'text-yellow-400' : 'text-neutral-400'">
                    {{ detailServer.secrets ? t('market.detail_required') : t('market.detail_not_required') }}
                  </span>
                </p>
              </div>
            </div>

            <div v-if="detailServer.installed" class="flex gap-2 pt-2 border-t border-neutral-700">
              <button
                class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                :class="detailServer.enabled
                  ? 'bg-yellow-700/50 text-yellow-200 hover:bg-yellow-700'
                  : 'bg-green-700/50 text-green-200 hover:bg-green-700'"
                @click="async () => { await store.toggle(detailServer!.name); detailServer!.enabled = !detailServer!.enabled }"
              >
                {{ detailServer.enabled ? t('market.detail_deactivate') : t('market.detail_activate') }}
              </button>
              <button
                class="px-4 py-2 rounded-lg text-sm font-medium bg-red-900/50 text-red-300 hover:bg-red-800/50 transition-colors"
                @click="confirmAction(detailServer)"
              >
                {{ t('market.detail_remove') }}
              </button>
            </div>
          </div>

          <div class="flex justify-end mt-6">
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
              @click="closeDetail"
            >
              {{ t('market.close') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      :show="dialog.show"
      :title="dialog.title"
      :message="dialog.message"
      @confirm="handleDialog"
      @cancel="dialog.show = false"
    />
  </div>
</template>
