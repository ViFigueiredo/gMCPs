<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import type { AgentInfo } from '@/types'
import { api } from '@/api'

const store = useGatewayStore()
const { t } = useI18n()
const agents = ref<AgentInfo[]>([])
const loading = ref(true)
const expanded = ref<Record<string, boolean>>({})
const adding = ref<Record<string, boolean>>({})
const statusMsg = ref('')
const statusError = ref(false)

const gatewayMcps = computed(() =>
  store.servers.filter(s => s.installed && s.enabled).map(s => s.name)
)

function missingMcps(agent: AgentInfo): string[] {
  const configured = new Set(agent.servers.map(s => s.name.toLowerCase().replace(/-/g, '')))
  return gatewayMcps.value.filter(
    name => !configured.has(name.toLowerCase().replace(/-/g, ''))
  )
}

async function fetchAgents() {
  loading.value = true
  try {
    agents.value = await api.integrations.list()
    agents.value.forEach(a => { expanded.value[a.id] = false })
  } catch (e: unknown) {
    statusMsg.value = t('integrations.error', { 0: (e instanceof Error ? e.message : String(e)) })
    statusError.value = true
  } finally {
    loading.value = false
  }
}

function toggleExpanded(id: string) {
  expanded.value[id] = !expanded.value[id]
}

async function autoAdd(agentId: string, mcpName: string) {
  const key = `${agentId}:${mcpName}`
  adding.value[key] = true
  try {
    await api.integrations.autoAdd(agentId, mcpName)
    statusMsg.value = t('integrations.server_added')
    statusError.value = false
    await fetchAgents()
  } catch (e: unknown) {
    statusMsg.value = t('integrations.error', { 0: (e instanceof Error ? e.message : String(e)) })
    statusError.value = true
  } finally {
    adding.value[key] = false
  }
  setTimeout(() => { statusMsg.value = '' }, 4000)
}

async function removeServer(agentId: string, serverName: string) {
  const key = `${agentId}:remove:${serverName}`
  adding.value[key] = true
  try {
    await api.integrations.removeServer(agentId, serverName)
    statusMsg.value = 'Servidor removido!'
    statusError.value = false
    await fetchAgents()
  } catch (e: unknown) {
    statusMsg.value = t('integrations.error', { 0: (e instanceof Error ? e.message : String(e)) })
    statusError.value = true
  } finally {
    adding.value[key] = false
  }
  setTimeout(() => { statusMsg.value = '' }, 4000)
}

onMounted(fetchAgents)
</script>

<template>
  <div>
    <div v-if="statusMsg" :class="['mb-4 px-4 py-2 rounded-lg text-sm', statusError ? 'bg-danger/20 text-red-300' : 'bg-success/20 text-green-300']">
      {{ statusMsg }}
    </div>

    <div v-if="loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

    <div v-for="agent in agents" :key="agent.id" class="mb-3 bg-neutral-900 rounded-lg border border-neutral-800 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-neutral-800/50 transition-colors" @click="toggleExpanded(agent.id)">
        <div class="flex items-center gap-2">
          <span class="text-neutral-400 text-xs transition-transform" :class="expanded[agent.id] ? 'rotate-90' : ''">&#9654;</span>
          <span class="font-semibold text-white">{{ agent.name }}</span>
          <span v-if="!agent.installed" class="text-warning text-sm">{{ t('integrations.not_installed') }}</span>
          <span class="text-neutral-500 text-xs">({{ agent.servers.length }})</span>
        </div>
        <div class="flex items-center gap-3 text-xs text-neutral-400">
          <span v-if="agent.config_path">
            {{ t('integrations.config_file') }}: <code class="text-neutral-300">{{ agent.config_path }}</code>
          </span>
        </div>
      </div>

      <div v-if="expanded[agent.id]">
        <!-- Already configured servers -->
        <div class="border-t border-neutral-800 p-4">
          <template v-if="agent.servers.length">
            <div class="text-xs text-neutral-500 font-semibold mb-2 uppercase tracking-wider">Configurados</div>
            <div class="divide-y divide-neutral-800">
              <div v-for="s in agent.servers" :key="s.name" class="flex items-center gap-3 py-2 text-sm">
                <span class="font-medium text-white min-w-0 flex-1 truncate">{{ s.name }}</span>
                <span class="text-neutral-400 text-xs px-2 py-0.5 rounded bg-neutral-800">{{ s.type }}</span>
                <span v-if="s.enabled !== undefined" :class="s.enabled ? 'text-success' : 'text-neutral-500'" class="text-xs">
                  {{ s.enabled ? 'On' : 'Off' }}
                </span>
                <button
                  class="px-2 py-0.5 rounded text-xs font-medium text-danger hover:bg-danger/20 hover:text-red-300 transition-colors"
                  :disabled="adding[`${agent.id}:remove:${s.name}`]"
                  @click="removeServer(agent.id, s.name)"
                >
                  {{ adding[`${agent.id}:remove:${s.name}`] ? '...' : 'remover' }}
                </button>
              </div>
            </div>
          </template>
          <p v-else class="text-neutral-500 text-sm mb-3">{{ t('integrations.no_servers') }}</p>
        </div>

        <!-- Available MCPs to add -->
        <div v-if="agent.installed && agent.config_path && missingMcps(agent).length" class="border-t border-neutral-800 px-4 pb-4">
          <div class="text-xs text-neutral-500 font-semibold mb-2 uppercase tracking-wider">Disponiveis para adicionar</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="mcp in missingMcps(agent)"
              :key="mcp"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              :class="adding[`${agent.id}:${mcp}`]
                ? 'bg-blue-800 text-blue-200 cursor-wait'
                : 'bg-blue-600 text-white hover:bg-blue-500 cursor-pointer'"
              :disabled="adding[`${agent.id}:${mcp}`]"
              @click="autoAdd(agent.id, mcp)"
            >
              <span v-if="adding[`${agent.id}:${mcp}`]" class="inline-block h-3 w-3 rounded-full border-2 border-blue-200 border-t-transparent animate-spin" />
              {{ mcp }}
            </button>
          </div>
        </div>

        <div v-if="agent.error" class="border-t border-neutral-800 px-4 pb-4 pt-2">
          <div class="text-danger text-sm mt-2">
            {{ t('integrations.error', { 0: agent.error }) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
