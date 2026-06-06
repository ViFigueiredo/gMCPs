import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGatewayStore } from '@/stores/gateway'
import { api } from '@/api'

vi.mock('@/api', () => ({
  api: {
    servers: {
      list: vi.fn(),
      detail: vi.fn(),
      install: vi.fn(),
      installMany: vi.fn(),
      uninstall: vi.fn(),
      toggle: vi.fn(),
    },
    catalog: { list: vi.fn() },
    state: { get: vi.fn() },
    stats: { get: vi.fn() },
    gateway: {
      restart: vi.fn(),
      logs: vi.fn(),
    },
  },
}))

const mockServers = [
  { name: 'memory', title: 'Memory', desc: 'Persistent memory', secrets: false, installed: true, enabled: true },
  { name: 'fetch', title: 'Fetch', desc: 'Fetch URLs', secrets: false, installed: true, enabled: false },
  { name: 'exa', title: 'Exa', desc: 'Search', secrets: true, installed: false, enabled: false },
]

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('gateway store', () => {
  it('fetches servers on demand', async () => {
    vi.mocked(api.servers.list).mockResolvedValue(mockServers)
    const store = useGatewayStore()
    await store.fetchServers()
    expect(store.servers).toHaveLength(3)
  })

  it('computes stats from servers', async () => {
    vi.mocked(api.servers.list).mockResolvedValue(mockServers)
    const store = useGatewayStore()
    await store.fetchServers()
    expect(store.stats.installed).toBe(2)
    expect(store.stats.enabled).toBe(1)
    expect(store.stats.catalog).toBe(3)
  })

  it('filters installed servers', async () => {
    vi.mocked(api.servers.list).mockResolvedValue(mockServers)
    const store = useGatewayStore()
    await store.fetchServers()
    expect(store.installedServers).toHaveLength(2)
  })

  it('calls install and refreshes', async () => {
    vi.mocked(api.servers.list).mockResolvedValue(mockServers)
    vi.mocked(api.servers.install).mockResolvedValue(mockServers[2])
    const store = useGatewayStore()
    await store.install('exa')
    expect(api.servers.install).toHaveBeenCalledWith('exa')
    expect(api.servers.list).toHaveBeenCalled()
  })

  it('calls toggle and refreshes', async () => {
    vi.mocked(api.servers.list).mockResolvedValue(mockServers)
    vi.mocked(api.servers.toggle).mockResolvedValue({ ...mockServers[1], enabled: true })
    const store = useGatewayStore()
    await store.toggle('fetch')
    expect(api.servers.toggle).toHaveBeenCalledWith('fetch')
  })
})
