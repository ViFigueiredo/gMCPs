#!/usr/bin/env node
/**
 * gmcp — TUI (curses) entry point.
 * Installs Python deps on first run, then launches the TUI.
 */

import { spawn, execSync } from 'child_process'
import { existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')

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
  proc.on('exit', (code) => process.exit(code ?? 0))
}

main()
