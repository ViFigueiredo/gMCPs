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

  const mime = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.json': 'application/json',
  }

  const server = createServer((req, res) => {
    let path = req.url === '/' ? '/index.html' : req.url
    const file = join(dist, path)
    if (existsSync(file)) {
      const ext = path.slice(path.lastIndexOf('.'))
      res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' })
      res.end(readFileSync(file))
    } else {
      res.writeHead(404).end('Not found')
    }
  })

  const webPort = parseInt(port) + 173
  server.listen(webPort, () => {
    console.log(`gmcp-web: API on :${port}, frontend on :${webPort}`)
    console.log(`  Open: http://localhost:${webPort}/`)
  })
}

function main() {
  startBackend()
  serveFrontend(port)
  process.on('SIGINT', () => process.exit())
  process.on('SIGTERM', () => process.exit())
}

main()
