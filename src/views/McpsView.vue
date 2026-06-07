<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const store = useGatewayStore()
const { t } = useI18n()
const search = ref('')
const filter = ref<'all' | 'active' | 'inactive'>('all')
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

async function handleDialog() {
  const a = dialog.value.action
  dialog.value.show = false
  await a()
}
</script>

<template>
  <div>
    <div class="sticky top-0 z-10 bg-neutral-950 -mx-4 px-4 pb-2">
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

      <div class="grid grid-cols-[6rem_minmax(0,1fr)_auto] gap-4 py-2 text-sm text-neutral-500 font-semibold border-b border-neutral-700">
        <span>Status</span>
        <span>Servidor</span>
        <span>Ações</span>
      </div>
    </div>

    <div v-if="store.loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

    <div v-if="filtered.length" class="divide-y divide-neutral-800">
      <div
        v-for="s in filtered"
        :key="s.name"
        class="grid grid-cols-[6rem_minmax(0,1fr)_auto] gap-4 px-4 py-3 items-center hover:bg-neutral-800/50 transition-colors"
      >
        <span :class="s.enabled ? 'text-success font-medium' : 'text-neutral-500'">
          {{ s.enabled ? t('mcps.active') : t('mcps.inactive') }}
        </span>
        <div class="min-w-0">
          <span :class="['font-medium', s.enabled ? 'text-white' : 'text-neutral-400']">
            {{ s.name }}
          </span>
          <span v-if="s.secrets" class="ml-2 text-warning text-xs" :title="t('mcps.needs_key')">*</span>
          <p class="text-xs text-neutral-500 truncate">{{ s.desc }}</p>
        </div>
        <div class="flex gap-2">
          <button
            class="px-3 py-1 text-xs rounded-md font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
            @click="confirmToggle(s)"
          >
            {{ s.enabled ? t('mcps.deactivate') : t('mcps.activate') }}
          </button>
          <button
            class="px-3 py-1 text-xs rounded-md font-medium bg-danger/20 text-red-300 hover:bg-red-800/50 transition-colors"
            @click="confirmUninstall(s.name)"
          >
            {{ t('mcps.remove') }}
          </button>
        </div>
      </div>
    </div>
    <p v-else class="text-neutral-500 py-8 text-center">{{ t('mcps.empty') }}</p>

    <ConfirmDialog
      :show="dialog.show"
      :title="dialog.title"
      :message="dialog.message"
      @confirm="handleDialog"
      @cancel="dialog.show = false"
    />
  </div>
</template>
