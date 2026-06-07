#!/usr/bin/env node
/**
 * gmcp-web — starts the backend API + serves the built frontend.
 * Usage: gmcp-web [--port 8000]
 */

import { spawn } from 'child_process'
import { existsSync, readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { createServer } from 'http'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const args = process.argv.slice(2)
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '8000'
const dist = join(ROOT, 'dist')

const EXT_RE = /\.\w+$/

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
  startBackend()
  const webPort = parseInt(port) + 173
  const url = `http://localhost:${webPort}/`
  serveFrontend(port)
  // Wait a bit then open browser
  setTimeout(() => openBrowser(url), 2000)
  process.on('SIGINT', () => process.exit())
  process.on('SIGTERM', () => process.exit())
}

main()
