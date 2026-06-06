import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { Server, Stats } from '@/types'

export const useGatewayStore = defineStore('gateway', () => {
  const servers = ref<Server[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchServers() {
    loading.value = true
    error.value = null
    try {
      servers.value = await api.servers.list()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch servers'
    } finally {
      loading.value = false
    }
  }

  const stats = computed<Stats>(() => {
    const total = servers.value.length
    const installed = servers.value.filter(s => s.installed).length
    const enabled = servers.value.filter(s => s.enabled).length
    return { catalog: total, installed, enabled }
  })

  const installedServers = computed(() => servers.value.filter(s => s.installed))
  const availableServers = computed(() => servers.value.filter(s => !s.installed))

  async function install(name: string) {
    await api.servers.install(name)
    await fetchServers()
  }

  async function uninstall(name: string) {
    await api.servers.uninstall(name)
    await fetchServers()
  }

  async function toggle(name: string) {
    await api.servers.toggle(name)
    await fetchServers()
  }

  async function restartGateway() {
    const result = await api.gateway.restart()
    return result.status === 'ok'
  }

  async function fetchLogs(n = 5) {
    const result = await api.gateway.logs(n)
    return result.logs
  }

  return {
    servers,
    loading,
    error,
    stats,
    installedServers,
    availableServers,
    fetchServers,
    install,
    uninstall,
    toggle,
    restartGateway,
    fetchLogs,
  }
})
