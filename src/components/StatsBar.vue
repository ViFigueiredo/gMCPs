<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'

const { t } = useI18n()
const store = useGatewayStore()

function formatMem(mb: number): string {
  if (mb < 0.1) return '0 MB'
  if (mb < 1024) return mb.toFixed(1) + ' MB'
  return (mb / 1024).toFixed(2) + ' GB'
}

function formatStorage(gb: number): string {
  if (gb < 0.001) return '0 MB'
  if (gb < 0.1) return (gb * 1024).toFixed(0) + ' MB'
  return gb.toFixed(2) + ' GB'
}
</script>

<template>
  <div class="grid grid-cols-3 gap-4 mb-4">
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.ram') }}</span>
      <span class="block text-2xl font-bold text-purple-400">{{ formatMem(store.resources.ram_used_mb) }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.cpu') }}</span>
      <span class="block text-2xl font-bold text-orange-400">{{ store.resources.cpu_percent }}<span class="text-sm font-normal text-neutral-500">%</span></span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.storage') }}</span>
      <span class="block text-2xl font-bold text-blue-400">{{ formatStorage(store.resources.storage_used_gb) }}</span>
    </div>
  </div>

  <!-- MCP Stats -->
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.installed') }}</span>
      <span class="block text-3xl font-bold text-primary">{{ store.stats.installed }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.active') }}</span>
      <span class="block text-3xl font-bold text-success">{{ store.stats.enabled }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.catalog') }}</span>
      <span class="block text-3xl font-bold text-warning">{{ store.stats.catalog }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.containers') }}</span>
      <span class="block text-3xl font-bold text-danger">{{ store.resources.active_containers }}</span>
    </div>
  </div>
</template>
