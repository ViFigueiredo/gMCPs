import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { Server, Stats, ResourcesStats } from '@/types'

export const useGatewayStore = defineStore('gateway', () => {
  const servers = ref<Server[]>([])
  const resources = ref<ResourcesStats>({ ram_used_mb: 0, cpu_percent: 0, storage_used_gb: 0, active_servers: 0, gateway_online: false })
  const sharedServers = ref<Record<string, number>>({})
  const sharedRelays = ref<any[]>([])
  const error = ref<string | null>(null)
  const connected = ref(false)
  const statusKey = ref<string | null>(null)
  const statusArg = ref<string | null>(null)
  let _healthTimer: ReturnType<typeof setInterval> | null = null

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

  async function _silentFetch() {
    try {
      servers.value = await api.servers.list()
      connected.value = true
      error.value = null
    } catch {
      connected.value = false
    }
  }

  async function fetchServers() {
    return withStatus('status.loading_servers', null, async () => {
      servers.value = await api.servers.list()
      connected.value = true
    })
  }

  function startHealthCheck(ms = 15000) {
    _silentFetch()
    _healthTimer = setInterval(_silentFetch, ms)
  }

  function stopHealthCheck() {
    if (_healthTimer) {
      clearInterval(_healthTimer)
      _healthTimer = null
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

  async function fetchResources() {
    try {
      resources.value = await api.resources.get()
    } catch { /* ignore */ }
  }

  // ── Shared mode ──

  async function fetchShared() {
    try {
      const res = await api.shared.list()
      sharedServers.value = res.shared
      const statusRes = await api.shared.status()
      sharedRelays.value = statusRes.relays
    } catch { /* ignore */ }
  }

  async function enableShared(name: string) {
    return withStatus('status.sharing', name, async () => {
      await api.shared.enable(name)
      await fetchShared()
    })
  }

  async function disableShared(name: string) {
    return withStatus('status.unsharing', name, async () => {
      await api.shared.disable(name)
      await fetchShared()
    })
  }

  function isShared(name: string): boolean {
    return name in sharedServers.value
  }

  function sharedPort(name: string): number | null {
    return sharedServers.value[name] ?? null
  }

  return {
    servers,
    resources,
    sharedServers,
    sharedRelays,
    loading,
    error,
    connected,
    statusKey,
    statusArg,
    stats,
    installedServers,
    availableServers,
    fetchServers,
    fetchResources,
    fetchShared,
    enableShared,
    disableShared,
    isShared,
    sharedPort,
    install,
    uninstall,
    toggle,
    restartGateway,
    fetchLogs,
    startHealthCheck,
    stopHealthCheck,
  }
})
