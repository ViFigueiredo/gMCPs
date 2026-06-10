<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const store = useGatewayStore()
const { t } = useI18n()
const search = ref('')
const filter = ref<'all' | 'active' | 'inactive'>('all')
const page = ref(1)
const pageSize = ref(10)
const dialog = ref<{ show: boolean; title: string; message: string; action: () => Promise<void> }>({
  show: false,
  title: '',
  message: '',
  action: async () => {},
})

const filtered = computed(() => {
  let list = store.installedServers
  if (filter.value === 'active') list = list.filter(s => s.enabled)
  if (filter.value === 'inactive') list = list.filter(s => !s.enabled)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(s => s.name.includes(q) || s.desc.toLowerCase().includes(q))
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)))

const paginated = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

function goToPage(p: number) {
  page.value = Math.max(1, Math.min(p, totalPages.value))
}

function confirmToggle(server: { name: string; enabled: boolean }) {
  dialog.value = {
    show: true,
    title: server.enabled ? t('mcps.deactivate') : t('mcps.activate'),
    message: `${server.enabled ? t('mcps.deactivate') : t('mcps.activate')} '${server.name}'?`,
    action: async () => { await store.toggle(server.name) },
  }
}

function confirmUninstall(name: string) {
  dialog.value = {
    show: true,
    title: t('mcps.remove'),
    message: `${t('mcps.remove')} '${name}'?`,
    action: async () => { await store.uninstall(name) },
  }
}

async function handleShareToggle(name: string) {
  if (store.isShared(name)) {
    dialog.value = {
      show: true,
      title: 'Desativar compartilhamento',
      message: `Desativar modo compartilhado para '${name}'?`,
      action: async () => { await store.disableShared(name) },
    }
  } else {
    await store.enableShared(name)
  }
}

async function handleDialog() {
  const a = dialog.value.action
  dialog.value.show = false
  await a()
}

onMounted(() => { store.fetchShared() })
</script>

<template>
  <div class="overflow-x-auto">
    <div class="min-w-[48rem]">
      <div class="sticky top-0 z-10 bg-neutral-950 pb-2">
        <!-- Search + Filters -->
        <div class="flex items-center gap-4 mb-4">
          <input
            v-model="search"
            type="text"
            :placeholder="t('mcps.search')"
            class="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors"
          />
          <div class="flex gap-1 bg-neutral-800 rounded-lg p-1">
            <button
              v-for="f in (['all', 'active', 'inactive'] as const)"
              :key="f"
              :class="[
                'px-3 py-1 rounded-md text-sm transition-colors',
                filter === f ? 'bg-neutral-700 text-white' : 'text-neutral-400',
              ]"
              @click="filter = f"
            >
              {{ f === 'all' ? t('mcps.filter_all') : f === 'active' ? t('mcps.filter_active') : t('mcps.filter_inactive') }}
            </button>
          </div>
        </div>

        <!-- Table header -->
        <div class="grid grid-cols-[7rem_1fr_10rem] gap-3 py-2 text-sm text-neutral-500 font-semibold border-b border-neutral-700">
          <span class="pl-4">{{ t('mcps.status') }}</span>
          <span>{{ t('mcps.server') }}</span>
          <span>{{ t('mcps.actions') }}</span>
        </div>
      </div>

      <div v-if="store.loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

      <div v-if="filtered.length" class="divide-y divide-neutral-800">
        <div
          v-for="s in paginated"
          :key="s.name"
          class="grid grid-cols-[7rem_1fr_10rem] gap-3 px-0 py-3 items-center hover:bg-neutral-800/50 transition-colors"
        >
          <span :class="['pl-4', s.enabled ? 'text-success font-medium' : 'text-neutral-500']">
            {{ s.enabled ? t('mcps.active') : t('mcps.inactive') }}
          </span>
          <div class="flex items-center gap-3 min-w-0">
            <img v-if="s.icon" :src="s.icon" alt="" class="w-6 h-6 rounded-full flex-shrink-0 bg-neutral-700" />
            <span v-else class="w-6 h-6 rounded-full flex-shrink-0 bg-neutral-700 flex items-center justify-center text-xs text-neutral-400">
              {{ s.name.charAt(0).toUpperCase() }}
            </span>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span :class="['font-medium', s.enabled ? 'text-white' : 'text-neutral-400']">
                  {{ s.name }}
                </span>
                <span v-if="store.isShared(s.name)"
                      class="text-xs px-1.5 py-0.5 rounded bg-green-900/50 text-green-300 font-mono flex-shrink-0"
                      :title="`Servico compartilhado (porta ${store.sharedPort(s.name)})`">
                  S:{{ store.sharedPort(s.name) }}
                </span>
                <span v-if="s.secrets && !store.isShared(s.name)"
                      class="text-warning text-xs flex-shrink-0"
                      :title="t('mcps.needs_key')">*</span>
              </div>
              <p class="text-xs text-neutral-500 truncate">{{ s.desc }}</p>
            </div>
          </div>
          <div class="flex gap-1.5">
            <button
              class="px-2.5 py-1 text-xs rounded-md font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
              @click="confirmToggle(s)"
            >
              {{ s.enabled ? t('mcps.deactivate') : t('mcps.activate') }}
            </button>
            <button
              class="px-2.5 py-1 text-xs rounded-md font-medium bg-danger/20 text-red-300 hover:bg-red-800/50 transition-colors"
              @click="confirmUninstall(s.name)"
            >
              {{ t('mcps.remove') }}
            </button>
            <button
              class="px-2.5 py-1 text-xs rounded-md font-medium transition-colors"
              :class="store.isShared(s.name)
                ? 'bg-success/20 text-success hover:bg-green-800/50'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'"
              @click="handleShareToggle(s.name)"
              :title="store.isShared(s.name) ? `Compartilhado (porta ${store.sharedPort(s.name)})` : 'Ativar compartilhamento'"
            >
              {{ store.isShared(s.name) ? 'Shared' : 'Share' }}
            </button>
          </div>
        </div>
      </div>
      <p v-else class="text-neutral-500 py-8 text-center">{{ t('mcps.empty') }}</p>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-6 pb-4">
        <button
          class="px-3 py-1 rounded text-xs font-medium bg-neutral-800 text-neutral-300 hover:bg-neutral-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
        >&laquo;</button>
        <button
          v-for="p in totalPages"
          :key="p"
          class="px-3 py-1 rounded text-xs font-medium transition-colors"
          :class="p === page ? 'bg-primary text-white' : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'"
          @click="goToPage(p)"
        >{{ p }}</button>
        <button
          class="px-3 py-1 rounded text-xs font-medium bg-neutral-800 text-neutral-300 hover:bg-neutral-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
        >&raquo;</button>
        <span class="text-xs text-neutral-500 ml-2">{{ filtered.length }} total</span>
      </div>

      <ConfirmDialog
        :show="dialog.show"
        :title="dialog.title"
        :message="dialog.message"
        @confirm="handleDialog"
        @cancel="dialog.show = false"
      />
    </div>
  </div>
</template>
