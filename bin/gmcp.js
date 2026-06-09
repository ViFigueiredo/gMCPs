#!/usr/bin/env node
/**
 * gmcp — TUI (curses) entry point.
 * Starts the Docker MCP Gateway, then launches the TUI.
 * Usage: gmcp
 */

import { spawn, execSync } from 'child_process'
import { existsSync, appendFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const GATEWAY_LOG = '/tmp/gateway.log'
const GATEWAY_PORT = '3099'

function startGateway() {
  const token = process.env.MCP_GATEWAY_AUTH_TOKEN || 'mcp-local-token'

  // Kill previous gateway
  try { execSync('pkill -9 -f "docker mcp gateway run" 2>/dev/null', { stdio: 'ignore' }) } catch {}

  // Clean orphan containers
  try {
    execSync('docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null', { stdio: 'ignore', timeout: 15000 })
  } catch {}

  // Start gateway in background
  const gw = spawn('docker', [
    'mcp', 'gateway', 'run',
    '--profile', 'profile',
    '--transport', 'sse',
    '--port', GATEWAY_PORT,
    '--long-lived',
  ], {
    env: { ...process.env, MCP_GATEWAY_AUTH_TOKEN: token },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
  })

  gw.stdout.on('data', d => { try { appendFileSync(GATEWAY_LOG, d) } catch {} })
  gw.stderr.on('data', d => { try { appendFileSync(GATEWAY_LOG, d) } catch {} })
  gw.unref()

  console.log(`gmcp: Gateway starting on :${GATEWAY_PORT} (PID ${gw.pid})`)
  return gw
}

function ensurePipDeps() {
  const req = join(ROOT, 'requirements.txt')
  if (!existsSync(req)) return
  try {
    execSync('pip3 install -q -r ' + req, { stdio: 'ignore', timeout: 60000 })
  } catch {
    // user may not have pip — backend will fail gracefully later
  }
}

function main() {
  ensurePipDeps()

  // Start gateway before TUI
  const gw = startGateway()

  const tui = join(ROOT, 'mcp-tui.py')
  if (!existsSync(tui)) {
    console.error('gmcp: mcp-tui.py not found at', tui)
    process.exit(1)
  }

  const proc = spawn('python3', [tui], {
    stdio: 'inherit',
    cwd: ROOT,
    env: { ...process.env, PYTHONPATH: ROOT },
  })

  // When TUI exits, kill gateway and exit
  proc.on('exit', (code) => {
    try { execSync('pkill -9 -f "docker mcp gateway run" 2>/dev/null', { stdio: 'ignore' }) } catch {}
    process.exit(code ?? 0)
  })

  // Forward signals
  process.on('SIGINT', () => { try { execSync('pkill -9 -f "docker mcp gateway run" 2>/dev/null', { stdio: 'ignore' }) } catch {}; process.exit() })
  process.on('SIGTERM', () => { try { execSync('pkill -9 -f "docker mcp gateway run" 2>/dev/null', { stdio: 'ignore' }) } catch {}; process.exit() })
}

main()
