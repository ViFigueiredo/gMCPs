export interface Server {
  name: string
  title: string
  desc: string
  secrets: boolean
  installed: boolean
  enabled: boolean
}

export interface CatalogItem {
  name: string
  title: string
  desc: string
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
