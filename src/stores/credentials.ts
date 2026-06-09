import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

export const useCredentialsStore = defineStore('credentials', () => {
  const credentials = ref<Record<string, Record<string, boolean>>>({})
  const saving = ref(false)
  const message = ref<string | null>(null)

  async function fetchCredentials() {
    try {
      credentials.value = await api.credentials.list()
    } catch (e) {
      credentials.value = {}
      message.value = e instanceof Error ? e.message : 'Failed to fetch'
    }
  }

  async function setCredential(server: string, key: string, value: string) {
    saving.value = true
    try {
      await api.credentials.set(server, key, value)
      await fetchCredentials()
      message.value = 'Credencial salva!'
    } catch (e) {
      message.value = e instanceof Error ? e.message : 'Error saving'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function deleteCredential(server: string, key: string) {
    saving.value = true
    try {
      await api.credentials.delete(server, key)
      await fetchCredentials()
      message.value = 'Credencial removida!'
    } catch (e) {
      message.value = e instanceof Error ? e.message : 'Error deleting'
      throw e
    } finally {
      saving.value = false
    }
  }

  function clearMessage() {
    message.value = null
  }

  return {
    credentials,
    saving,
    message,
    fetchCredentials,
    setCredential,
    deleteCredential,
    clearMessage,
  }
})