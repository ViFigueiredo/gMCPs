<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'

const { t } = useI18n()
const store = useGatewayStore()
</script>

<template>
  <div class="grid grid-cols-3 gap-4 mb-6">
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
  </div>
</template>
