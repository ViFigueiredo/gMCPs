#!/usr/bin/env node
/**
 * Postinstall hook: installs Python backend dependencies via pip.
 * Runs after `npm install` or `npm install -g`.
 */

import { execSync } from 'child_process'
import { existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const req = join(__dirname, '..', 'requirements.txt')

if (existsSync(req)) {
  try {
    execSync('pip3 install -q -r ' + req, { stdio: 'inherit', timeout: 120000 })
    console.log('gmcp: Python dependencies installed.')
  } catch {
    console.warn('gmcp: Could not install Python deps. Run: pip3 install -r ' + req)
  }
}
