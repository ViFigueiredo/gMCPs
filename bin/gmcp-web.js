#!/usr/bin/env node
/**
 * gmcp-web — starts the backend API + frontend dev server.
 * Usage: gmcp-web [--port 8000] [--host 0.0.0.0]
 */

import { spawn } from 'child_process'
import { existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const args = process.argv.slice(2)
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '8000'

function startBackend() {
  const uvicorn = join(ROOT, '.venv', 'bin', 'uvicorn')
  const cmd = existsSync(uvicorn) ? uvicorn : 'uvicorn'
  const proc = spawn(cmd, ['backend.main:app', '--port', port, '--reload'], {
    stdio: 'inherit',
    cwd: ROOT,
    env: { ...process.env, PYTHONPATH: ROOT },
  })
  proc.on('exit', () => process.exit())
  return proc
}

function startFrontend() {
  const vite = join(ROOT, 'node_modules', '.bin', 'vite')
  const cmd = existsSync(vite) ? vite : 'npx vite'
  const proc = spawn(cmd, [], { stdio: 'inherit', cwd: ROOT, shell: true })
  proc.on('exit', () => process.exit())
  return proc
}

function main() {
  console.log(`gmcp-web: starting backend on :${port} and frontend on :5173`)
  const back = startBackend()
  startFrontend()
  process.on('SIGINT', () => { back.kill(); process.exit() })
  process.on('SIGTERM', () => { back.kill(); process.exit() })
}

main()
