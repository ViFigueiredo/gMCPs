import type { Server, CatalogItem, GatewayState, Stats, RestartResult, LogsResult } from '@/types'

const BASE = 'http://localhost:8000/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${msg}`)
  }
  return res.json()
}

export const api = {
  servers: {
    list: () => request<Server[]>('/servers'),
    detail: (name: string) => request<Server>(`/servers/${encodeURIComponent(name)}`),
    install: (name: string) => request<Server>(`/servers/${encodeURIComponent(name)}/install`, { method: 'POST' }),
    uninstall: (name: string) => request<Server>(`/servers/${encodeURIComponent(name)}/uninstall`, { method: 'POST' }),
    toggle: (name: string) => request<Server>(`/servers/${encodeURIComponent(name)}/toggle`, { method: 'POST' }),
    installMany: (names: string[]) =>
      Promise.all(names.map(n => api.servers.install(n))),
  },
  catalog: {
    list: () => request<CatalogItem[]>('/catalog'),
  },
  state: {
    get: () => request<GatewayState>('/state'),
  },
  stats: {
    get: () => request<Stats>('/stats'),
  },
  gateway: {
    restart: () => request<RestartResult>('/gateway/restart', { method: 'POST' }),
    logs: (n = 5) => request<LogsResult>(`/gateway/logs?n=${n}`),
  },
}
