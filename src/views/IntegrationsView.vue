<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AgentInfo } from '@/types'
import { api } from '@/api'

const { t } = useI18n()
const agents = ref<AgentInfo[]>([])
const loading = ref(true)
const dialog = ref<{ show: boolean; agent: AgentInfo | null }>({ show: false, agent: null })
const form = ref({
  name: '',
  type: 'local' as 'local' | 'remote',
  command: '',
  args: '',
  url: '',
  env: '',
})
const statusMsg = ref('')
const statusError = ref(false)

async function fetchAgents() {
  loading.value = true
  try {
    agents.value = await api.integrations.list()
  } catch (e: any) {
    statusMsg.value = t('integrations.error', { 0: e.message || e })
    statusError.value = true
  } finally {
    loading.value = false
  }
}

function openAdd(agent: AgentInfo) {
  form.value = { name: '', type: 'local', command: '', args: '', url: '', env: '' }
  dialog.value = { show: true, agent }
}

async function addMcp() {
  const a = dialog.value.agent
  if (!a) return
  const argsList = form.value.args ? form.value.args.split(' ').filter(Boolean) : []
  const envObj: Record<string, string> = {}
  if (form.value.env) {
    form.value.env.split('\n').filter(Boolean).forEach(line => {
      const idx = line.indexOf('=')
      if (idx > 0) envObj[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
    })
  }
  try {
    await api.integrations.addServer({
      agent_id: a.id,
      name: form.value.name,
      type: form.value.type,
      command: form.value.command,
      args: argsList,
      url: form.value.url,
      env: envObj,
    })
    statusMsg.value = t('integrations.server_added')
    statusError.value = false
    dialog.value.show = false
    await fetchAgents()
  } catch (e: any) {
    statusMsg.value = t('integrations.error', { 0: e.message || e })
    statusError.value = true
  }
  setTimeout(() => { statusMsg.value = '' }, 4000)
}

onMounted(fetchAgents)
</script>

<template>
  <div>
    <div v-if="statusMsg" :class="['mb-4 px-4 py-2 rounded-lg text-sm', statusError ? 'bg-red-900/50 text-red-300' : 'bg-green-900/50 text-green-300']">
      {{ statusMsg }}
    </div>

    <div v-if="loading" class="text-neutral-400 py-8 text-center">{{ t('loading') }}</div>

    <div v-for="agent in agents" :key="agent.id" class="mb-6 bg-neutral-900 rounded-lg border border-neutral-800 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
        <div>
          <span class="font-semibold text-white">{{ agent.name }}</span>
          <span v-if="!agent.installed" class="ml-2 text-yellow-400 text-sm">{{ t('integrations.not_installed') }}</span>
        </div>
        <div class="flex items-center gap-3 text-xs text-neutral-400">
          <span v-if="agent.config_path">
            {{ t('integrations.config_file') }}: <code class="text-neutral-300">{{ agent.config_path }}</code>
          </span>
        </div>
      </div>

      <div class="p-4">
        <div v-if="agent.error" class="text-red-400 text-sm mb-2">
          {{ t('integrations.error', { 0: agent.error }) }}
        </div>

        <div v-if="agent.servers.length" class="divide-y divide-neutral-800">
          <div v-for="s in agent.servers" :key="s.name" class="flex items-center gap-3 py-2 text-sm">
            <span class="font-medium text-white min-w-0 flex-1 truncate">{{ s.name }}</span>
            <span class="text-neutral-400 text-xs px-2 py-0.5 rounded bg-neutral-800">{{ s.type }}</span>
            <span v-if="s.enabled !== undefined" :class="s.enabled ? 'text-green-400' : 'text-neutral-500'" class="text-xs">
              {{ s.enabled ? 'On' : 'Off' }}
            </span>
          </div>
        </div>
        <p v-else class="text-neutral-500 text-sm">{{ t('integrations.no_servers') }}</p>
      </div>

      <div v-if="agent.installed && agent.config_path" class="px-4 pb-4">
        <button class="text-xs px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-500 transition-colors cursor-pointer" @click="openAdd(agent)">
          {{ t('integrations.add_btn') }}
        </button>
      </div>
    </div>

    <div v-if="dialog.show && dialog.agent" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="dialog.show = false">
      <div class="bg-neutral-900 rounded-xl border border-neutral-700 p-6 max-w-lg w-full mx-4">
        <h3 class="text-lg font-semibold text-white mb-4">
          {{ t('integrations.add_title', { 0: dialog.agent.name }) }}
        </h3>

        <div class="space-y-3">
          <div>
            <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.name') }}</label>
            <input v-model="form.name" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.type') }}</label>
            <select v-model="form.type" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500">
              <option value="local">local</option>
              <option value="remote">remote</option>
            </select>
          </div>
          <template v-if="form.type === 'local'">
            <div>
              <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.command') }}</label>
              <input v-model="form.command" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" placeholder="npx -y @modelcontextprotocol/server-filesystem" />
            </div>
            <div>
              <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.command') }} args</label>
              <input v-model="form.args" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" placeholder="/path/to/dir" />
            </div>
          </template>
          <template v-else>
            <div>
              <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.url') }}</label>
              <input v-model="form.url" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" placeholder="https://mcp.example.com/mcp" />
            </div>
          </template>
          <div>
            <label class="block text-sm text-neutral-400 mb-1">{{ t('integrations.env') }}</label>
            <textarea v-model="form.env" rows="3" class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" placeholder="API_KEY=xxx&#10;TOKEN=yyy" />
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button class="px-4 py-2 text-sm rounded-lg bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors cursor-pointer" @click="dialog.show = false">
            {{ t('dialog.cancel') }}
          </button>
          <button class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors cursor-pointer" @click="addMcp">
            {{ t('integrations.add_btn') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
