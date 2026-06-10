<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { api } from '@/api'
import type { Server } from '@/types'

const store = useGatewayStore()
const { t } = useI18n()
const search = ref('')
const categoryFilter = ref('')
const filter = ref<'all' | 'installed' | 'available'>('all')
const page = ref(1)
const pageSize = ref(30)
const selected = ref(new Set<string>())
const detailServer = ref<Server | null>(null)
const dialog = ref<{ show: boolean; title: string; message: string; action: () => Promise<void> }>({
  show: false,
  title: '',
  message: '',
  action: async () => {},
})

// ── Custom MCP form ──
const showAddForm = ref(false)
const addName = ref('')
const addType = ref<'local' | 'remote'>('local')
const addCommand = ref('')
const addEnv = ref('')
const addError = ref('')

// ── Categories ──
const allCategories = computed(() => {
  const cats = new Set<string>()
  for (const s of store.servers) {
    if (s.category) cats.add(s.category)
  }
  return Array.from(cats).sort()
})

const catalogServers = computed(() => {
  let list = store.servers
  if (filter.value === 'installed') list = list.filter(s => s.installed)
  if (filter.value === 'available') list = list.filter(s => !s.installed)
  if (categoryFilter.value) {
    list = list.filter(s => s.category === categoryFilter.value)
  }
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(
      s => s.name.includes(q) || s.title.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q),
    )
  }
  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(catalogServers.value.length / pageSize.value)))

const paginatedServers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return catalogServers.value.slice(start, start + pageSize.value)
})

function goToPage(p: number) {
  page.value = Math.max(1, Math.min(p, totalPages.value))
}

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

// ── Custom MCP ──
function openAddForm() {
  addName.value = ''
  addType.value = 'local'
  addCommand.value = ''
  addEnv.value = ''
  addError.value = ''
  showAddForm.value = true
}

async function submitAddForm() {
  addError.value = ''
  if (!addName.value.trim()) {
    addError.value = 'Nome é obrigatório'
    return
  }
  if (!addCommand.value.trim()) {
    addError.value = 'Comando/URL é obrigatório'
    return
  }
  try {
    const env: Record<string, string> = {}
    if (addEnv.value.trim()) {
      addEnv.value.split(',').forEach(pair => {
        const [k, ...v] = pair.split('=')
        if (k && v.length) env[k.trim()] = v.join('=').trim()
      })
    }
    // Install first, then add to gateway
    await store.install(addName.value.trim())
    showAddForm.value = false
  } catch (e: unknown) {
    addError.value = e instanceof Error ? e.message : String(e)
  }
}
</script>

<template>
  <div class="flex gap-4">
    <!-- Category sidebar -->
    <div class="w-44 flex-shrink-0 hidden lg:block">
      <div class="sticky top-0 pt-0">
        <h3 class="text-xs text-neutral-500 font-semibold uppercase tracking-wider mb-3">{{ t('market.category_filter') }}</h3>
        <ul class="space-y-1">
          <li>
            <button
              class="w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors"
              :class="!categoryFilter ? 'bg-primary/20 text-primary font-medium' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'"
              @click="categoryFilter = ''"
            >
              {{ t('market.category_all') }} ({{ store.servers.length }})
            </button>
          </li>
          <li v-for="cat in allCategories" :key="cat">
            <button
              class="w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors"
              :class="categoryFilter === cat ? 'bg-primary/20 text-primary font-medium' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'"
              @click="categoryFilter = cat"
            >
              {{ cat }}
              <span class="text-neutral-600">({{ store.servers.filter(s => s.category === cat).length }})</span>
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- Main content -->
    <div class="flex-1 min-w-0">
      <div class="sticky top-0 z-10 bg-neutral-950 -mx-4 px-4 pb-2">
        <!-- Search + Filter + Install + Add buttons -->
        <div class="flex items-center gap-3 mb-4">
          <input
            v-model="search"
            type="text"
            :placeholder="t('market.search')"
            class="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors"
          />
          <div class="flex gap-1 bg-neutral-800 rounded-lg p-1">
            <button
              v-for="f in (['all', 'installed', 'available'] as const)"
              :key="f"
              :class="[
                'px-3 py-1 rounded-md text-sm transition-colors',
                filter === f ? 'bg-neutral-700 text-white' : 'text-neutral-400',
              ]"
              @click="filter = f"
            >
              {{ f === 'all' ? t('market.filter_all') : f === 'installed' ? t('market.filter_installed') : t('market.filter_available') }}
            </button>
          </div>
          <button
            :disabled="!hasSelection"
            class="px-5 py-2 rounded-lg text-sm font-bold transition-colors"
            :class="hasSelection ? 'bg-primary text-white hover:bg-primary-hover cursor-pointer' : 'bg-neutral-800 text-neutral-600 cursor-not-allowed'"
            @click="installSelected"
          >
            {{ t('market.install_btn') }} {{ hasSelection ? `(${selected.size})` : '' }}
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors cursor-pointer"
            @click="openAddForm"
          >
            {{ t('market.add_btn') }}
          </button>
        </div>

        <!-- Mobile category filter chips -->
        <div v-if="allCategories.length" class="flex flex-wrap gap-1.5 mb-2 lg:hidden">
          <button
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="!categoryFilter ? 'bg-primary/30 text-primary' : 'bg-neutral-800 text-neutral-400 hover:text-white'"
            @click="categoryFilter = ''"
          >
            {{ t('market.category_all') }}
          </button>
          <button
            v-for="cat in allCategories"
            :key="cat"
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="categoryFilter === cat ? 'bg-primary/30 text-primary' : 'bg-neutral-800 text-neutral-400 hover:text-white'"
            @click="categoryFilter = cat"
          >
            {{ cat }}
          </button>
        </div>

        <!-- Table header -->
        <div class="grid grid-cols-[2.5rem_6rem_minmax(0,1fr)_6rem] gap-3 py-2 text-sm text-neutral-500 font-semibold border-b border-neutral-700 items-center">
          <input
            type="checkbox"
            :checked="catalogServers.length > 0 && selected.size === catalogServers.length"
            :indeterminate="selected.size > 0 && selected.size < catalogServers.length"
            class="w-4 h-4 accent-blue-500 cursor-pointer"
            @click="selectAll"
          />
          <span>{{ t('mcps.status') }}</span>
          <span>{{ t('mcps.server') }}</span>
          <span class="text-center">{{ t('mcps.actions') }}</span>
        </div>
      </div>

      <div v-if="store.loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

      <!-- Server rows -->
      <div v-if="catalogServers.length" class="divide-y divide-neutral-800">
        <div
          v-for="s in paginatedServers"
          :key="s.name"
          class="grid grid-cols-[2.5rem_6rem_minmax(0,1fr)_6rem] gap-3 px-4 py-3 items-center hover:bg-neutral-800/50 transition-colors"
        >
          <input
            type="checkbox"
            :checked="selected.has(s.name)"
            class="w-4 h-4 accent-blue-500 cursor-pointer"
            @click="toggleSelect(s.name)"
          />
          <span :class="s.installed ? 'text-success' : 'text-neutral-500'">
            {{ s.installed ? t('market.status_installed') : t('market.status_available') }}
          </span>
          <div class="min-w-0 flex items-center gap-3">
            <img v-if="s.icon" :src="s.icon" alt="" class="w-6 h-6 rounded-full flex-shrink-0 bg-neutral-700" @error="(e: any) => e.target.style.display='none'" />
            <span v-else class="w-6 h-6 rounded-full flex-shrink-0 bg-neutral-700 flex items-center justify-center text-xs text-neutral-400">
              {{ s.name.charAt(0).toUpperCase() }}
            </span>
            <span class="font-medium text-white truncate">{{ s.name }}</span>
            <span v-if="s.secrets" class="text-warning text-xs" title="Requer API key">*</span>
          </div>
          <div class="flex justify-center">
            <button
              class="px-3 py-1 text-xs rounded-md font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors cursor-pointer"
              @click="showDetail(s.name)"
            >
              {{ t('market.details') }}
            </button>
          </div>
        </div>
      </div>
      <p v-else class="text-neutral-500 py-8 text-center">
        {{ search ? t('market.no_results') : t('market.empty') }}
      </p>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="detailServer" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="closeDetail" />
        <div class="relative bg-neutral-800 border border-neutral-600 rounded-xl p-6 w-[32rem] max-h-[80vh] overflow-y-auto shadow-2xl">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-3">
              <img v-if="detailServer.icon" :src="detailServer.icon" alt="" class="w-10 h-10 rounded-full bg-neutral-700" />
              <div>
                <h3 class="text-xl font-bold text-white">{{ detailServer.name }}</h3>
                <p v-if="detailServer.title" class="text-sm text-neutral-400 mt-1">{{ detailServer.title }}</p>
              </div>
            </div>
            <span
              :class="detailServer.installed ? 'text-success' : 'text-neutral-500'"
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

            <div v-if="detailServer.category" class="flex items-center gap-2">
              <span class="text-xs text-neutral-500 uppercase tracking-wide">{{ t('market.category_filter') }}:</span>
              <span class="text-xs px-2 py-0.5 rounded bg-neutral-700 text-neutral-300">{{ detailServer.category }}</span>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <h4 class="text-xs text-neutral-500 uppercase tracking-wide mb-1">{{ t('market.detail_status') }}</h4>
                <p class="text-sm">
                  <span :class="detailServer.enabled ? 'text-success' : 'text-neutral-400'">
                    {{ detailServer.enabled ? 'Ativo' : 'Inativo' }}
                  </span>
                </p>
              </div>
              <div>
                <h4 class="text-xs text-neutral-500 uppercase tracking-wide mb-1">{{ t('market.detail_api_key') }}</h4>
                <p class="text-sm">
                  <span :class="detailServer.secrets ? 'text-warning' : 'text-neutral-400'">
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
                class="px-4 py-2 rounded-lg text-sm font-medium bg-danger/20 text-red-300 hover:bg-red-800/50 transition-colors"
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

    <!-- Custom MCP Add Modal -->
    <Teleport to="body">
      <div v-if="showAddForm" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showAddForm = false" />
        <div class="relative bg-neutral-800 border border-neutral-600 rounded-xl p-6 w-[32rem] shadow-2xl">
          <div class="flex items-center gap-2 mb-6">
            <h3 class="text-lg font-bold text-white">{{ t('market.add_title') }}</h3>
            <div class="relative group">
              <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-neutral-600 text-neutral-300 text-xs cursor-help font-bold">i</span>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg bg-neutral-700 text-xs text-neutral-200 whitespace-nowrap shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-60 w-72">
                {{ t('market.add_info_icon') }}
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-xs text-neutral-400 block mb-1">{{ t('market.add_name') }}</label>
              <input v-model="addName" type="text" class="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors" />
            </div>
            <div>
              <label class="text-xs text-neutral-400 block mb-1">{{ t('market.add_type') }}</label>
              <select v-model="addType" class="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-white outline-none focus:border-primary transition-colors">
                <option value="local">Local (comando)</option>
                <option value="remote">Remoto (URL)</option>
              </select>
            </div>
            <div>
              <label class="text-xs text-neutral-400 block mb-1">{{ t('market.add_command') }}</label>
              <input v-model="addCommand" type="text" :placeholder="addType === 'local' ? 'npx -y @modelcontextprotocol/server-github' : 'http://localhost:3099/sse?server=...'" class="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors" />
            </div>
            <div>
              <label class="text-xs text-neutral-400 block mb-1">{{ t('market.add_env') }}</label>
              <input v-model="addEnv" type="text" placeholder="API_KEY=xxx, OTHER=yyy" class="w-full bg-neutral-700 border border-neutral-600 rounded-lg px-3 py-2 text-white placeholder-neutral-500 outline-none focus:border-primary transition-colors" />
            </div>
            <p v-if="addError" class="text-danger text-sm">{{ addError }}</p>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
              @click="showAddForm = false"
            >
              {{ t('market.close') }}
            </button>
            <button
              class="px-4 py-2 rounded-lg text-sm font-bold bg-primary text-white hover:bg-primary-hover transition-colors"
              @click="submitAddForm"
            >
              {{ t('market.add_btn') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

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
      <span class="text-xs text-neutral-500 ml-2">{{ catalogServers.length }} total</span>
    </div>

    <ConfirmDialog
      :show="dialog.show"
      :title="dialog.title"
      :message="dialog.message"
      @confirm="handleDialog"
      @cancel="dialog.show = false"
    />
  </div>
</template>
