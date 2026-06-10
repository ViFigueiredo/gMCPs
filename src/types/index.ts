export interface Server {
  name: string
  title: string
  desc: string
  icon: string
  category: string
  secrets: boolean
  installed: boolean
  enabled: boolean
}

export interface CatalogItem {
  name: string
  title: string
  desc: string
  icon: string
  category: string
  secrets: boolean
}

export interface GatewayState {
  installed: string[]
  enabled: string[]
}

export interface Stats {
  catalog: number
  installed: number
  enabled: number
}

export interface RestartResult {
  status: string
}

export interface LogsResult {
  logs: string[]
}

export interface CredentialEntry {
  server: string
  key: string
  has_value: boolean
}

export interface McpServerDef {
  name: string
  type: string
  command: string | null
  args: string[]
  url: string | null
  env: Record<string, string>
  enabled: boolean | null
}

export interface ResourcesStats {
  ram_used_mb: number
  cpu_percent: number
  storage_used_gb: number
  active_servers: number
  gateway_online: boolean
}

export interface AgentInfo {
  id: string
  name: string
  config_path: string | null
  config_format: string
  installed: boolean
  servers: McpServerDef[]
  error: string | null
}
