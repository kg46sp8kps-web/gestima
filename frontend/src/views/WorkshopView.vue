<template>
  <div class="workshop-view" data-testid="workshop-view">
    <!-- Horní lišta -->
    <header class="workshop-view__header">
      <div class="workshop-view__brand">
        <span class="workshop-view__title">Gestima Dílna</span>
        <span v-if="auth.user" class="workshop-view__user">{{ auth.user.username }}</span>
      </div>
      <div class="workshop-view__actions">
        <button
          class="btn-secondary workshop-view__txs-btn"
          data-testid="show-transactions-btn"
          @click="showTxPanel = !showTxPanel"
        >
          <ClipboardList :size="ICON_SIZE" />
          <span>Transakce</span>
        </button>
        <button
          class="btn-secondary workshop-view__logout"
          data-testid="workshop-logout"
          @click="auth.logout()"
        >
          <LogOut :size="ICON_SIZE" />
        </button>
      </div>
    </header>

    <!-- Hlavní obsah — 3 panely -->
    <div class="workshop-view__body">
      <!-- Panel 1: Seznam zakázek -->
      <section class="workshop-panel workshop-panel--jobs">
        <div class="workshop-panel__title">Zakázky</div>
        <WorkshopJobList />
      </section>

      <!-- Panel 2: Operace + časovač -->
      <section class="workshop-panel workshop-panel--opers">
        <div class="workshop-panel__title">Operace</div>
        <WorkshopOperationPanel />
      </section>

      <!-- Panel 3: Formulář odvodu -->
      <section class="workshop-panel workshop-panel--form">
        <div class="workshop-panel__title">Odvod</div>
        <WorkshopTransactionForm />
      </section>
    </div>

    <!-- Spodní lišta: přehled statusu časovače -->
    <footer v-if="store.timer.running" class="workshop-view__timer-bar">
      <span class="timer-bar__dot" />
      <span class="timer-bar__text">
        Časovač běží — {{ store.activeJob?.Job }} / Op {{ store.timer.operNum }}
        — {{ formattedTimerTime }}
      </span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ClipboardList, LogOut } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import { useAuthStore } from '@/stores/auth'
import WorkshopJobList from '@/components/modules/workshop/WorkshopJobList.vue'
import WorkshopOperationPanel from '@/components/modules/workshop/WorkshopOperationPanel.vue'
import WorkshopTransactionForm from '@/components/modules/workshop/WorkshopTransactionForm.vue'
import { ICON_SIZE } from '@/config/design'

const store = useWorkshopStore()
const auth = useAuthStore()
const showTxPanel = ref(false)

const formattedTimerTime = computed(() => {
  const s = store.timerElapsed
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [
    h.toString().padStart(2, '0'),
    m.toString().padStart(2, '0'),
    sec.toString().padStart(2, '0'),
  ].join(':')
})

onMounted(() => {
  store.fetchJobs()
  store.fetchMyTransactions()
})
</script>

<style scoped>
.workshop-view {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: var(--base);
  color: var(--t1);
  font-family: var(--font);
  overflow: hidden;
}

/* Header */
.workshop-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px var(--pad);
  background: var(--ground);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
  min-height: 56px;
}

.workshop-view__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workshop-view__title {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--t1);
}

.workshop-view__user {
  font-size: var(--fsm);
  color: var(--t3);
  padding: 2px 8px;
  background: var(--surface);
  border-radius: var(--rs);
}

.workshop-view__actions {
  display: flex;
  gap: var(--gap);
  align-items: center;
}

.workshop-view__txs-btn,
.workshop-view__logout {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 8px 12px;
}

/* Hlavní obsah — 3 panely vedle sebe */
.workshop-view__body {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

/* Na menším iPadu (portrait) — stack pod sebou */
@container (max-width: 900px) {
  .workshop-view__body {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    overflow-y: auto;
  }
}

.workshop-panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--b2);
  overflow: hidden;
  min-height: 0;
}

.workshop-panel:last-child {
  border-right: none;
}

.workshop-panel__title {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px var(--pad);
  background: var(--ground);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

/* Timer bar */
.workshop-view__timer-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px var(--pad);
  background: var(--ground);
  border-top: 1px solid var(--b2);
  flex-shrink: 0;
}

.timer-bar__dot {
  width: 8px;
  height: 8px;
  border-radius: 99px;
  background: var(--ok);
  animation: pulse 1.5s ease-in-out infinite;
}

.timer-bar__text {
  font-size: var(--fsm);
  color: var(--ok);
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
