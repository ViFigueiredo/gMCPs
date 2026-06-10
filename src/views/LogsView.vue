<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api'

const { t } = useI18n()

interface Connection {
  agent: string
  mcp_name: string
  container_id: string
  container_name: string
  started_at: string
  ended_at: string | null
  status: string
}

interface Tag {
  mcp_name: string
  active: number
  total: number
}

const connections = ref<Connection[]>([])
const tags = ref<Tag[]>([])
const selectedMcps = ref<Set<string>>(new Set())
const dateStart = ref('')
const dateEnd = ref('')
const loading = ref(false)

const BASE = 'http://localhost:8000/api'

async function fetchConnections() {
  loading.value = true
  try {
    const mcpParam = Array.from(selectedMcps.value).join(',')
    const params = new URLSearchParams()
    if (mcpParam) params.set('mcp', mcpParam)
    if (dateStart.value) params.set('date_start', dateStart.value)
    if (dateEnd.value) params.set('date_end', dateEnd.value)
    const qs = params.toString()
    const res = await fetch(`${BASE}/connections${qs ? '?' + qs : ''}`)
    if (res.ok) {
      const data = await res.json()
      connections.value = data.connections
    }
  } finally {
    loading.value = false
  }
}

async function fetchTags() {
  try {
    const res = await fetch(`${BASE}/connections/tags`)
    if (res.ok) {
      const data = await res.json()
      tags.value = data.tags
    }
  } catch { /* ignore */ }
}

function toggleMcp(name: string) {
  if (selectedMcps.value.has(name)) {
    selectedMcps.value.delete(name)
  } else {
    selectedMcps.value.add(name)
  }
  fetchConnections()
}

function clearFilters() {
  selectedMcps.value.clear()
  dateStart.value = ''
  dateEnd.value = ''
  fetchConnections()
}

const stopping = ref<Record<string, boolean>>({})

async function stopContainer(mcpName: string) {
  stopping.value[mcpName] = true
  try {
    await api.stopContainer(mcpName)
    await fetchConnections()
    await fetchTags()
  } catch { /* ignore */ }
  finally {
    stopping.value[mcpName] = false
  }
}

// ── Clear modal ──
const showClearModal = ref(false)
const clearForm = ref({
  mcps: [] as string[],
  selectAllMcps: true,
  dateStart: '',
  dateEnd: '',
  lastAmount: 0,
  lastUnit: 'minutes' as 'minutes' | 'hours' | 'days',
})
const clearing = ref(false)
const clearResult = ref<number | null>(null)

function openClear() {
  clearForm.value = {
    mcps: [],
    selectAllMcps: true,
    dateStart: dateStart.value,
    dateEnd: dateEnd.value,
    lastAmount: 0,
    lastUnit: 'minutes',
  }
  clearResult.value = null
  showClearModal.value = true
}

function toggleClearMcp(name: string) {
  const idx = clearForm.value.mcps.indexOf(name)
  if (idx >= 0) {
    clearForm.value.mcps.splice(idx, 1)
  } else {
    clearForm.value.mcps.push(name)
  }
}

async function submitClear() {
  clearing.value = true
  clearResult.value = null
  try {
    const body: Record<string, any> = {}
    if (!clearForm.value.selectAllMcps && clearForm.value.mcps.length > 0) {
      body.mcps = clearForm.value.mcps
    }
    if (clearForm.value.dateStart) body.date_start = clearForm.value.dateStart
    if (clearForm.value.dateEnd) body.date_end = clearForm.value.dateEnd
    if (clearForm.value.lastAmount > 0) {
      const mult = clearForm.value.lastUnit === 'minutes' ? 60 : clearForm.value.lastUnit === 'hours' ? 3600 : 86400
      body.last_seconds = clearForm.value.lastAmount * mult
    }
    const res = await fetch(`${BASE}/connections/clear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (res.ok) {
      const data = await res.json()
      clearResult.value = data.stopped
      await fetchConnections()
      await fetchTags()
    } else {
      const err = await res.text().catch(() => '')
      clearResult.value = -1
      console.error('Clear error:', res.status, err)
    }
  } catch (e) {
    clearResult.value = -1
    console.error('Clear fetch error:', e)
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchConnections()
  fetchTags()
})
</script>

<template>
  <div>
    <!-- Filter tags -->
    <div class="flex flex-wrap gap-2 mb-3 items-center">
      <button
        class="px-3 py-1 rounded-full text-xs font-medium transition-colors"
        :class="selectedMcps.size === 0
          ? 'bg-primary text-white'
          : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'"
        @click="clearFilters"
      >
        All
      </button>
      <button
        v-for="tag in tags"
        :key="tag.mcp_name"
        class="px-3 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1"
        :class="selectedMcps.has(tag.mcp_name)
          ? 'bg-primary text-white'
          : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'"
        @click="toggleMcp(tag.mcp_name)"
      >
        {{ tag.mcp_name }}
        <span
          class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full text-[10px] font-bold"
          :class="tag.active > 0 ? 'bg-success text-white' : 'bg-neutral-600 text-neutral-300'"
        >
          {{ tag.active }}
        </span>
      </button>
    </div>

    <!-- Date filters -->
    <div class="flex gap-4 mb-3 items-center">
      <div class="flex items-center gap-2">
        <label for="dateStart" class="text-xs text-neutral-400">Inicio:</label>
        <input
          id="dateStart"
          type="date"
          v-model="dateStart"
          @change="fetchConnections"
          class="bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary"
        />
      </div>
      <div class="flex items-center gap-2">
        <label for="dateEnd" class="text-xs text-neutral-400">Fim:</label>
        <input
          id="dateEnd"
          type="date"
          v-model="dateEnd"
          @change="fetchConnections"
          class="bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary"
        />
      </div>
      <button
        class="px-2 py-1 rounded text-xs font-medium bg-neutral-800 text-neutral-400 hover:bg-neutral-700 transition-colors"
        @click="fetchConnections"
      >
        Refresh
      </button>
      <button
        class="px-2 py-1 rounded text-xs font-medium bg-danger/20 text-danger hover:bg-red-800/50 hover:text-red-300 transition-colors"
        @click="openClear"
      >
        Clear
      </button>
    </div>

    <!-- Table -->
    <div class="bg-neutral-900 border border-neutral-800 rounded-lg overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-neutral-500 border-b border-neutral-800">
              <th class="text-left p-3 font-semibold text-xs">AGENTE</th>
              <th class="text-left p-3 font-semibold text-xs">MCP</th>
              <th class="text-left p-3 font-semibold text-xs">CONTAINER</th>
              <th class="text-left p-3 font-semibold text-xs">INICIO</th>
              <th class="text-left p-3 font-semibold text-xs">FIM</th>
              <th class="text-left p-3 font-semibold text-xs">STATUS</th>
              <th class="text-left p-3 font-semibold text-xs"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="border-b border-neutral-800">
              <td colspan="7" class="p-4 text-center text-neutral-500">
                {{ t('loading') }}
              </td>
            </tr>
            <tr
              v-for="c in connections"
              :key="c.container_id + c.started_at"
              class="border-b border-neutral-800 hover:bg-neutral-800 transition-colors"
            >
              <td class="p-3 text-neutral-200 font-mono text-xs">{{ c.agent }}</td>
              <td class="p-3">
                <span class="font-medium text-white text-xs">{{ c.mcp_name }}</span>
              </td>
              <td class="p-3 font-mono text-neutral-300 text-xs">{{ c.container_id }}</td>
              <td class="p-3 font-mono text-neutral-400 text-xs">{{ c.started_at }}</td>
              <td class="p-3 font-mono text-neutral-400 text-xs">{{ c.ended_at || '-' }}</td>
              <td class="p-3">
                <span
                  class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold"
                  :class="c.status === 'active'
                    ? 'bg-success/20 text-success'
                    : 'bg-neutral-800 text-neutral-500'"
                >
                  <span
                    class="inline-flex rounded-full h-1.5 w-1.5"
                    :class="c.status === 'active' ? 'bg-success' : 'bg-neutral-500'"
                  />
                  {{ c.status }}
                </span>
              </td>
              <td v-if="c.status === 'active'" class="p-3">
                <button
                  class="px-2 py-1 rounded text-[10px] font-medium bg-danger/20 text-danger hover:bg-red-800/50 hover:text-red-300 transition-colors disabled:opacity-50"
                  :disabled="stopping[c.mcp_name]"
                  @click="stopContainer(c.mcp_name)"
                >
                  {{ stopping[c.mcp_name] ? '...' : 'stop' }}
                </button>
              </td>
              <td v-else class="p-3" />
            </tr>
            <tr v-if="!loading && connections.length === 0">
              <td colspan="7" class="p-4 text-center text-neutral-500">
                Nenhuma conexao encontrada
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Clear Modal -->
  <div v-if="showClearModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="showClearModal = false">
    <div class="bg-neutral-900 rounded-xl border border-neutral-700 p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
      <h3 class="text-lg font-semibold text-white mb-4">Parar containers em massa</h3>

      <div class="space-y-4">
        <!-- MCP filter -->
        <div>
          <label class="block text-sm text-neutral-400 mb-2">MCPs</label>
          <div class="flex items-center gap-2 mb-2">
            <label class="flex items-center gap-2 text-sm text-white">
              <input type="checkbox" v-model="clearForm.selectAllMcps" class="accent-blue-500" />
              Todos
            </label>
          </div>
          <div v-if="!clearForm.selectAllMcps" class="flex flex-wrap gap-2">
            <label v-for="tag in tags" :key="tag.mcp_name" class="flex items-center gap-2 text-sm text-neutral-300 cursor-pointer">
              <input type="checkbox" :checked="clearForm.mcps.includes(tag.mcp_name)" @change="toggleClearMcp(tag.mcp_name)" class="accent-blue-500" />
              {{ tag.mcp_name }} ({{ tag.active }})
            </label>
          </div>
        </div>

        <!-- Period filter -->
        <div>
          <label class="block text-sm text-neutral-400 mb-2">Periodo</label>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs text-neutral-500">Inicio</label>
              <input type="datetime-local" v-model="clearForm.dateStart" class="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary" />
            </div>
            <div>
              <label class="text-xs text-neutral-500">Fim</label>
              <input type="datetime-local" v-model="clearForm.dateEnd" class="w-full bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary" />
            </div>
          </div>
        </div>

        <!-- Last N minutes/hours/days -->
        <div>
          <label class="block text-sm text-neutral-400 mb-2">Ultimos</label>
          <div class="flex gap-2">
            <input type="number" v-model.number="clearForm.lastAmount" min="0" class="w-20 bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary" placeholder="0" />
            <select v-model="clearForm.lastUnit" class="bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary">
              <option value="minutes">minutos</option>
              <option value="hours">horas</option>
              <option value="days">dias</option>
            </select>
          </div>
        </div>

        <!-- Result -->
        <div v-if="clearResult !== null" :class="clearResult >= 0 ? 'text-green-400' : 'text-red-400'" class="text-sm font-medium">
          {{ clearResult >= 0 ? `${clearResult} container(s) parado(s)` : 'Erro ao parar containers' }}
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button class="px-4 py-2 text-sm rounded-lg bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors cursor-pointer" @click="showClearModal = false">
          Cancelar
        </button>
        <button
          class="px-4 py-2 text-sm rounded-lg bg-danger text-white hover:bg-red-600 transition-colors cursor-pointer disabled:opacity-50"
          :disabled="clearing"
          @click="submitClear"
        >
          {{ clearing ? 'Parando...' : 'Parar containers' }}
        </button>
      </div>
    </div>
  </div>
</template>
