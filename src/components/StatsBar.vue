<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'

const { t } = useI18n()
const store = useGatewayStore()
</script>

<template>
  <!-- System Resources -->
  <div class="grid grid-cols-3 gap-4 mb-4">
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.ram') }}</span>
      <span class="block text-2xl font-bold text-purple-400">{{ store.resources.ram_used_mb }}<span class="text-sm font-normal text-neutral-500"> / {{ store.resources.ram_total_mb }} MB</span></span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.cpu') }}</span>
      <span class="block text-2xl font-bold text-orange-400">{{ store.resources.cpu_percent }}<span class="text-sm font-normal text-neutral-500">%</span></span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.storage') }}</span>
      <span class="block text-2xl font-bold text-blue-400">{{ store.resources.storage_used_gb }}<span class="text-sm font-normal text-neutral-500"> / {{ store.resources.storage_total_gb }} GB</span></span>
    </div>
  </div>

  <!-- MCP Stats -->
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.installed') }}</span>
      <span class="block text-3xl font-bold text-cyan-400">{{ store.stats.installed }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.active') }}</span>
      <span class="block text-3xl font-bold text-green-400">{{ store.stats.enabled }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('stats.catalog') }}</span>
      <span class="block text-3xl font-bold text-yellow-400">{{ store.stats.catalog }}</span>
    </div>
    <div class="border border-neutral-700 rounded-lg p-4 text-center bg-neutral-900/50">
      <span class="block text-sm text-neutral-400 mb-1">{{ t('resources.containers') }}</span>
      <span class="block text-3xl font-bold text-red-400">{{ store.resources.active_containers }}</span>
    </div>
  </div>
</template>
