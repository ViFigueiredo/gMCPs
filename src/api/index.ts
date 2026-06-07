import type { Server, CatalogItem, GatewayState, Stats, RestartResult, LogsResult, ResourcesStats, AgentInfo } from '@/types'

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
  resources: {
    get: () => request<ResourcesStats>('/resources'),
  },
  gateway: {
    restart: () => request<RestartResult>('/gateway/restart', { method: 'POST' }),
    logs: (n = 5) => request<LogsResult>(`/gateway/logs?n=${n}`),
  },
  integrations: {
    list: () => request<AgentInfo[]>('/integrations'),
    addServer: (body: { agent_id: string; name: string; type: string; command: string; args: string[]; url: string; env: Record<string, string> }) =>
      request<{ status: string }>('/integrations/add-server', { method: 'POST', body: JSON.stringify(body) }),
    autoAdd: (agentId: string, mcpName: string) =>
      request<{ status: string }>(`/integrations/auto-add/${encodeURIComponent(agentId)}/${encodeURIComponent(mcpName)}`, { method: 'POST' }),
    removeServer: (agentId: string, serverName: string) =>
      request<{ status: string }>(`/integrations/remove-server/${encodeURIComponent(agentId)}/${encodeURIComponent(serverName)}`, { method: 'POST' }),
  },
  stopContainer: (mcpName: string) =>
    request<{ status: string }>(`/connections/${encodeURIComponent(mcpName)}/stop`, { method: 'POST' }),
}
