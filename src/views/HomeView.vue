<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGatewayStore } from '@/stores/gateway'
import StatsBar from '@/components/StatsBar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const store = useGatewayStore()
const { t } = useI18n()
const logs = ref<string[]>([])
const showRestartDialog = ref(false)

onMounted(async () => {
  logs.value = await store.fetchLogs()
  store.fetchResources()
})

async function handleRestart() {
  showRestartDialog.value = false
  await store.restartGateway()
  logs.value = await store.fetchLogs()
}
</script>

<template>
  <div>
    <div class="flex flex-col items-center justify-center mb-6 pt-2">
      <div class="flex items-center gap-3">
        <span class="text-3xl md:text-4xl font-black tracking-tight"
              style="background: linear-gradient(135deg, #27C2FF 0%, #0B8DFF 50%, #0059D6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
          gMCP
        </span>
      </div>
      <span class="text-xs md:text-sm font-medium tracking-widest uppercase mt-1"
            style="background: linear-gradient(135deg, #27C2FF 0%, #0B8DFF 50%, #0059D6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        Gateway MCP Manager
      </span>
    </div>
    <StatsBar />

    <div v-if="store.error" class="bg-danger/20 border border-red-700 rounded-lg p-3 text-red-200 mb-4">
      {{ store.error }}
    </div>

    <section class="mb-6">
      <h2 class="text-lg font-semibold text-white mb-3">{{ t('home.recent') }}</h2>
      <div v-if="logs.length" class="bg-neutral-900 rounded-lg p-4 font-mono text-sm text-neutral-400 space-y-1">
        <div v-for="(line, i) in logs" :key="i">{{ line }}</div>
      </div>
      <p v-else class="text-neutral-500 italic">{{ t('home.no_logs') }}</p>
    </section>

    <section>
      <h2 class="text-lg font-semibold text-white mb-3">{{ t('home.quick_actions') }}</h2>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-white rounded-lg transition-colors text-sm font-medium"
          @click="showRestartDialog = true"
        >
          {{ t('home.restart') }}
        </button>
      </div>
    </section>

    <ConfirmDialog
      :show="showRestartDialog"
      :title="t('home.restart_title')"
      :message="t('home.restart_msg')"
      :confirm-label="t('home.restart_confirm')"
      @confirm="handleRestart"
      @cancel="showRestartDialog = false"
    />
  </div>
</template>
