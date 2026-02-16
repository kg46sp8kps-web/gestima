/**
 * GESTIMA - Files Store
 *
 * Pinia store for centralized file management (ADR-044).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { FileWithLinks, FileFilters, FileUploadOptions, FileLinkRequest } from '@/types/file'
import { filesApi } from '@/api/files'
import { useUiStore } from './ui'

export const useFilesStore = defineStore('files', () => {
  const ui = useUiStore()

  // State
  const files = ref<FileWithLinks[]>([])
  const selectedFile = ref<FileWithLinks | null>(null)
  const loading = ref(false)
  const filters = ref<FileFilters>({})
  const total = ref(0)

  // Computed
  const hasFiles = computed(() => files.value.length > 0)
  const orphanFiles = computed(() =>
    files.value.filter(f => f.links.length === 0 && f.status !== 'temp')
  )

  // Actions
  async function fetchFiles(newFilters?: FileFilters) {
    loading.value = true
    try {
      if (newFilters !== undefined) {
        filters.value = newFilters
      }
      const response = await filesApi.list(filters.value)
      files.value = response.files
      total.value = response.total
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání souborů')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchOrphans() {
    loading.value = true
    try {
      const response = await filesApi.getOrphans()
      files.value = response.files
      total.value = response.total
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání osiřelých souborů')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function selectFile(fileId: number) {
    loading.value = true
    try {
      selectedFile.value = await filesApi.get(fileId)
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při načítání souboru')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function uploadFile(file: File, options?: FileUploadOptions) {
    loading.value = true
    try {
      const uploaded = await filesApi.upload(file, options)

      // Create FileWithLinks from upload response
      const fileWithLinks: FileWithLinks = {
        ...uploaded,
        links: uploaded.link ? [uploaded.link] : []
      }

      files.value.unshift(fileWithLinks)
      total.value++
      ui.showSuccess('Soubor nahrán')
      return fileWithLinks
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při nahrávání souboru')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deleteFile(fileId: number) {
    loading.value = true
    try {
      await filesApi.delete(fileId)

      // Remove from list
      const index = files.value.findIndex(f => f.id === fileId)
      if (index !== -1) {
        files.value.splice(index, 1)
        total.value--
      }

      // Clear selection if deleted
      if (selectedFile.value?.id === fileId) {
        selectedFile.value = null
      }

      ui.showSuccess('Soubor smazán')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při mazání souboru')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function linkFile(fileId: number, linkData: FileLinkRequest) {
    loading.value = true
    try {
      await filesApi.link(fileId, linkData)

      // Refresh file to get updated links
      await selectFile(fileId)

      ui.showSuccess('Soubor propojen')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při propojení souboru')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function unlinkFile(fileId: number, entityType: string, entityId: number) {
    loading.value = true
    try {
      await filesApi.unlink(fileId, entityType, entityId)

      // Update links in selected file
      if (selectedFile.value?.id === fileId) {
        selectedFile.value.links = selectedFile.value.links.filter(
          l => !(l.entity_type === entityType && l.entity_id === entityId)
        )
      }

      // Update in list
      const file = files.value.find(f => f.id === fileId)
      if (file) {
        file.links = file.links.filter(
          l => !(l.entity_type === entityType && l.entity_id === entityId)
        )
      }

      ui.showSuccess('Vazba odpojena')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při odpojení vazby')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function setPrimary(fileId: number, entityType: string, entityId: number) {
    loading.value = true
    try {
      await filesApi.setPrimary(fileId, entityType, entityId)

      // Refresh file to get updated links
      await selectFile(fileId)

      ui.showSuccess('Nastaven jako primární')
    } catch (error: any) {
      ui.showError(error.message || 'Chyba při nastavení primárního')
      throw error
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: FileFilters) {
    filters.value = newFilters
  }

  function reset() {
    files.value = []
    selectedFile.value = null
    loading.value = false
    filters.value = {}
    total.value = 0
  }

  return {
    // State
    files,
    selectedFile,
    loading,
    filters,
    total,
    // Computed
    hasFiles,
    orphanFiles,
    // Actions
    fetchFiles,
    fetchOrphans,
    selectFile,
    uploadFile,
    deleteFile,
    linkFile,
    unlinkFile,
    setPrimary,
    setFilters,
    reset
  }
})
