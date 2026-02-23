<script setup lang="ts">
import { useDialog } from '@/composables/useDialog'
import Button from './Button.vue'

const { confirmDialog, resolveConfirm } = useDialog()
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="confirmDialog" class="modal-backdrop" @click.self="resolveConfirm(false)">
        <div class="confirm-box" role="alertdialog">
          <h3 class="confirm-title">{{ confirmDialog.title }}</h3>
          <p class="confirm-message">{{ confirmDialog.message }}</p>
          <div class="confirm-actions">
            <Button
              variant="secondary"
              data-testid="confirm-cancel"
              @click="resolveConfirm(false)"
            >
              {{ confirmDialog.cancelLabel ?? 'Zrušit' }}
            </Button>
            <Button
              :variant="confirmDialog.dangerous ? 'danger' : 'primary'"
              data-testid="confirm-ok"
              @click="resolveConfirm(true)"
            >
              {{ confirmDialog.confirmLabel ?? 'Potvrdit' }}
            </Button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.confirm-box {
  background: var(--surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--b2);
  border-radius: 10px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
  padding: 24px;
  width: 380px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirm-title {
  font-size: var(--fsh);
  font-weight: 600;
  color: var(--t1);
}

.confirm-message {
  font-size: var(--fs);
  color: var(--t2);
  line-height: 1.6;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>
