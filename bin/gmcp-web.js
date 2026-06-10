#!/usr/bin/env node
/**
 * gmcp-web — starts the Docker MCP Gateway + backend API + serves the built frontend.
 * Usage: gmcp-web [--port 8000] [--gateway-port 3099]
 */

import { spawn, execSync } from 'child_process'
import { existsSync, readFileSync, appendFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { createServer } from 'http'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const args = process.argv.slice(2)
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '8000'
const gatewayPort = args.includes('--gateway-port') ? args[args.indexOf('--gateway-port') + 1] : '3099'
const dist = join(ROOT, 'dist')
const GATEWAY_LOG = '/tmp/gateway.log'

const EXT_RE = /\.\w+$/

/**
 * Kill any process holding the gateway port, then clean up orphan containers.
 * Uses fuser(1) which reliably kills the actual docker-mcp process by port,
 * unlike pkill -f which only matched the docker CLI wrapper.
 */
function killPreviousGateway(port) {
  try {
    execSync(`fuser -k "${port}/tcp" 2>/dev/null`, { stdio: 'ignore', timeout: 5000 })
  } catch { /* no process on port — ok */ }
  try {
    execSync('docker rm -f $(docker ps -aq --filter "label=docker-mcp=true") 2>/dev/null', { stdio: 'ignore', timeout: 15000 })
  } catch { /* ok */ }
}

/**
 * Health-check the gateway SSE endpoint.
 */
function isGatewayOnline(port, token) {
  try {
    const code = execSync(
      `curl -s -o /dev/null -w '%{http_code}' 'http://localhost:${port}/sse?server=memory' -H 'Authorization: Bearer ${token}' --max-time 3`,
      { stdio: 'pipe', timeout: 5000 }
    ).toString().trim()
    return code === '200'
  } catch {
    return false
  }
}

function startGateway() {
  const token = process.env.MCP_GATEWAY_AUTH_TOKEN || 'mcp-local-token'

  // Kill previous gateway by port (always kills the real docker-mcp, not just CLI wrapper)
  killPreviousGateway(gatewayPort)

  // Reset log for a clean session
  try {
    appendFileSync(GATEWAY_LOG, `--- gmcp-web started at ${new Date().toISOString()} ---\n`)
  } catch { /* ok */ }

  // Start gateway in background
  const gw = spawn('docker', [
    'mcp', 'gateway', 'run',
    '--profile', 'profile',
    '--transport', 'sse',
    '--port', gatewayPort,
    '--long-lived',
  ], {
    env: { ...process.env, MCP_GATEWAY_AUTH_TOKEN: token },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
  })

  // Log gateway output
  gw.stdout.on('data', d => appendFileSync(GATEWAY_LOG, d))
  gw.stderr.on('data', d => appendFileSync(GATEWAY_LOG, d))
  gw.unref()

  console.log(`gmcp-web: Gateway starting on :${gatewayPort} (PID ${gw.pid})`)

  // Poll until gateway is online (max 30s)
  let attempts = 0
  const check = setInterval(() => {
    if (isGatewayOnline(gatewayPort, token)) {
      clearInterval(check)
      console.log(`gmcp-web: Gateway online on :${gatewayPort}`)
      return
    }
    attempts++
    if (attempts >= 10) {
      clearInterval(check)
      console.error(`gmcp-web: Gateway not ready after 30s. Check ${GATEWAY_LOG}`)
    }
  }, 3000)
}

function startBackend() {
  const uvicorn = join(ROOT, '.venv', 'bin', 'uvicorn')
  const cmd = existsSync(uvicorn) ? uvicorn : 'uvicorn'
  const proc = spawn(cmd, ['backend.main:app', '--port', port], {
    stdio: 'inherit',
    cwd: ROOT,
    env: { ...process.env, PYTHONPATH: ROOT },
  })
  proc.on('exit', () => process.exit())
  return proc
}

function serveFrontend(apiPort) {
  const index = join(dist, 'index.html')
  if (!existsSync(index)) {
    console.error('gmcp-web: dist/index.html not found. Run: npm run build-only')
    process.exit(1)
  }

  const indexContent = readFileSync(index)

  const mime = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.json': 'application/json',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
  }

  const server = createServer((req, res) => {
    let path = req.url === '/' ? '/index.html' : req.url

    // SPA fallback: routes like /mcps, /market, /logs serve index.html
    if (!EXT_RE.test(path)) {
      res.writeHead(200, { 'Content-Type': 'text/html' })
      res.end(indexContent)
      return
    }

    const file = join(dist, path)
    if (existsSync(file)) {
      const ext = path.slice(path.lastIndexOf('.'))
      res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' })
      res.end(readFileSync(file))
    } else {
      // Fallback to index.html even for unknown paths (e.g. favicon.ico)
      res.writeHead(200, { 'Content-Type': 'text/html' })
      res.end(indexContent)
    }
  })

  const webPort = parseInt(apiPort) + 173
  server.listen(webPort, () => {
    const url = `http://localhost:${webPort}/`
    console.log(`gmcp-web: API on :${apiPort}, frontend on :${webPort}`)
    console.log(`  Open: ${url}`)
  })
}

function openBrowser(url) {
  const cmd = process.platform === 'darwin' ? 'open' :
              process.platform === 'win32' ? 'cmd' :
              'xdg-open'
  const args = process.platform === 'win32' ? ['/c', 'start', url] : [url]
  try {
    spawn(cmd, args, { detached: true, stdio: 'ignore' }).unref()
  } catch { /* browser may not be available */ }
}

function main() {
  // Cleanup on exit — kill gateway by port, remove orphan containers
  const cleanup = () => {
    killPreviousGateway(gatewayPort)
    process.exit()
  }
  process.on('SIGINT', cleanup)
  process.on('SIGTERM', cleanup)

  startGateway()
  startBackend()
  const webPort = parseInt(port) + 173
  const url = `http://localhost:${webPort}/`
  serveFrontend(port)
  setTimeout(() => openBrowser(url), 3000)
}

main()
