<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  show: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60" @click="emit('cancel')" />
      <div class="relative bg-neutral-800 border border-neutral-600 rounded-xl p-6 w-80 shadow-2xl">
        <h3 class="text-lg font-semibold text-white mb-2">{{ title }}</h3>
        <p class="text-neutral-300 mb-6">{{ message }}</p>
        <div class="flex gap-3 justify-end">
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
            @click="emit('cancel')"
          >
            {{ cancelLabel || t('dialog.cancel') }}
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-500 transition-colors"
            @click="emit('confirm')"
          >
            {{ confirmLabel || t('dialog.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
