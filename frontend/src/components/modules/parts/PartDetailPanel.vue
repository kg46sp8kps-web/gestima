<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Part, PartUpdate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import DrawingsManagementModal from './DrawingsManagementModal.vue'
import CopyPartModal from './CopyPartModal.vue'
import CustomizableModule from '@/components/layout/CustomizableModule.vue'
import { partDetailConfig } from '@/config/layouts/part-detail'
import { updatePart, deletePart } from '@/api/parts'
import { useAuthStore } from '@/stores/auth'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
  'refresh': []
}>()

// Auth store
const authStore = useAuthStore()

// Modals
const showDrawingsModal = ref(false)
const showCopyModal = ref(false)

// Widget context
const widgetContext = computed(() => ({
  'part-info-edit': {
    part: props.part,
    isAdmin: authStore.isAdmin
  },
  'part-actions': {
    hasDrawing: !!props.part?.drawing_path,
    disabled: !props.part
  }
}))

// Widget action handler
async function handleWidgetAction(widgetId: string, action: string, payload?: any) {
  if (action === 'action:save') {
    // Save part changes
    try {
      const updateData: PartUpdate = {
        article_number: payload.article_number,
        drawing_number: payload.drawing_number,
        name: payload.name,
        customer_revision: payload.customer_revision,
        version: props.part.version
      }
      await updatePart(props.part.part_number, updateData)
      emit('refresh')
    } catch (error: any) {
      console.error('Failed to update part:', error)
      throw error
    }
  } else if (action === 'action:delete') {
    // Delete part
    try {
      await deletePart(props.part.part_number)
      emit('refresh')
    } catch (error: any) {
      console.error('Failed to delete part:', error)
      throw error
    }
  } else if (action === 'action:copy') {
    // Open copy modal
    showCopyModal.value = true
  } else if (action === 'action:material') {
    emit('open-material')
  } else if (action === 'action:operations') {
    emit('open-operations')
  } else if (action === 'action:pricing') {
    emit('open-pricing')
  } else if (action === 'action:drawing') {
    // Left-click: open drawing or upload modal
    if (props.part.drawing_path) {
      emit('open-drawing')
    } else {
      showDrawingsModal.value = true
    }
  } else if (action === 'action:drawing-manage') {
    // Right-click: always open management modal
    showDrawingsModal.value = true
  }
}

function handleCopySuccess() {
  emit('refresh')
}

function handleOpenDrawing(drawingId?: number) {
  emit('open-drawing', drawingId)
  showDrawingsModal.value = false
}
</script>

<template>
  <div class="part-detail-panel">
    <CustomizableModule
      :config="partDetailConfig"
      :widget-context="widgetContext"
      @widget-action="handleWidgetAction"
    />

    <!-- Drawings Management Modal -->
    <DrawingsManagementModal
      v-model="showDrawingsModal"
      :part-number="part.part_number"
      @refresh="emit('refresh')"
      @open-drawing="handleOpenDrawing"
    />

    <!-- Copy Part Modal -->
    <CopyPartModal
      v-model="showCopyModal"
      :part-number="part.part_number"
      :source-part="part"
      @success="handleCopySuccess"
    />
  </div>
</template>

<style scoped>
.part-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
