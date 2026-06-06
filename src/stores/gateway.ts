import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { Server, Stats } from '@/types'

export const useGatewayStore = defineStore('gateway', () => {
  const servers = ref<Server[]>([])
  const error = ref<string | null>(null)
  const statusKey = ref<string | null>(null)
  const statusArg = ref<string | null>(null)

  const loading = computed(() => statusKey.value !== null)

  function withStatus<T>(key: string, arg: string | null, fn: () => Promise<T>): Promise<T> {
    statusKey.value = key
    statusArg.value = arg
    error.value = null
    return fn().finally(() => {
      statusKey.value = null
      statusArg.value = null
    }).catch((e: unknown) => {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    })
  }

  async function fetchServers() {
    return withStatus('status.loading_servers', null, async () => {
      servers.value = await api.servers.list()
    })
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
    return withStatus('status.installing', name, async () => {
      await api.servers.install(name)
      servers.value = await api.servers.list()
    })
  }

  async function uninstall(name: string) {
    return withStatus('status.uninstalling', name, async () => {
      await api.servers.uninstall(name)
      servers.value = await api.servers.list()
    })
  }

  async function toggle(name: string) {
    return withStatus('status.toggling', name, async () => {
      await api.servers.toggle(name)
      servers.value = await api.servers.list()
    })
  }

  async function restartGateway() {
    return withStatus('status.restarting', null, async () => {
      const result = await api.gateway.restart()
      return result.status === 'ok'
    })
  }

  async function fetchLogs(n = 5) {
    const result = await api.gateway.logs(n)
    return result.logs
  }

  return {
    servers,
    loading,
    error,
    statusKey,
    statusArg,
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
