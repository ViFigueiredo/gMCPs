<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
        <label class="text-xs text-neutral-400">Inicio:</label>
        <input
          type="date"
          v-model="dateStart"
          @change="fetchConnections"
          class="bg-neutral-800 border border-neutral-700 rounded px-2 py-1 text-white text-xs outline-none focus:border-primary"
        />
      </div>
      <div class="flex items-center gap-2">
        <label class="text-xs text-neutral-400">Fim:</label>
        <input
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
</template>
