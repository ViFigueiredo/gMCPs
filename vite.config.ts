import { fileURLToPath, URL } from 'node:url'
import { readFileSync, existsSync } from 'node:fs'

import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Version precedence: VERSION file > package.json
let appVersion = '0.0.0'
const versionFile = new URL('./VERSION', import.meta.url)
if (existsSync(versionFile)) {
  appVersion = readFileSync(versionFile, 'utf-8').trim()
} else {
  const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8'))
  appVersion = pkg.version
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  plugins: [
    tailwindcss(),
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
