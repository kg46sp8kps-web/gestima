<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperatorStore } from '@/stores/operator'

const router = useRouter()
const operator = useOperatorStore()

const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  ticker = setInterval(() => { now.value = Date.now() }, 1000)
})
onUnmounted(() => {
  if (ticker) clearInterval(ticker)
})

const firstJob = computed(() => operator.activeJobs[0] ?? null)
const activeJobsCount = computed(() => operator.activeJobs.length)
const extraJobsCount = computed(() => Math.max(0, activeJobsCount.value - 1))
const unresolvedErrors = computed(() => operator.unresolvedErrorCount)

const elapsed = computed(() => {
  if (!firstJob.value) return ''
  const start = new Date(firstJob.value.started_at).getTime()
  const diff = Math.max(0, Math.floor((now.value - start) / 1000))
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const isSetup = computed(() => firstJob.value?.trans_type === 'setup_start')

function goToJob() {
  if (!firstJob.value) return
  router.push({
    name: 'terminal-job-detail',
    params: { job: firstJob.value.job, oper: firstJob.value.oper_num },
  })
}
</script>

<template>
  <div v-if="firstJob" class="active-bar" @click="goToJob">
    <span :class="['pulse', { setup: isSetup }]" />
    <span class="bar-info">
      <strong>{{ firstJob.job }}</strong>
      <span class="bar-sep">/</span>
      <span>Op {{ firstJob.oper_num }}</span>
      <span v-if="firstJob.wc" class="bar-wc">{{ firstJob.wc }}</span>
      <span v-if="isSetup" class="bar-tag">Seřízení</span>
      <span v-if="extraJobsCount > 0" class="bar-multi">+{{ extraJobsCount }} další</span>
    </span>
    <span v-if="unresolvedErrors > 0" class="bar-alert">
      {{ unresolvedErrors }} chyb
    </span>
    <span class="bar-timer">{{ elapsed }}</span>
  </div>
</template>

<style scoped>
.active-bar {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  background: rgba(76, 175, 80, 0.08);
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.active-bar:active {
  background: rgba(76, 175, 80, 0.14);
}

/* Pulsing dot */
.pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ok);
  flex-shrink: 0;
  animation: pulse-glow 1.5s ease-in-out infinite;
}
.pulse.setup {
  background: var(--warn);
  animation: pulse-glow-setup 1.5s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.5); }
  50% { box-shadow: 0 0 0 6px rgba(76, 175, 80, 0); }
}
@keyframes pulse-glow-setup {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.5); }
  50% { box-shadow: 0 0 0 6px rgba(255, 193, 7, 0); }
}

.bar-info {
  flex: 1;
  font-size: 14px;
  color: var(--t1);
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
.bar-sep { color: var(--t4); }
.bar-wc {
  color: var(--t3);
  font-size: 12px;
  margin-left: 4px;
}
.bar-tag {
  font-size: 11px;
  color: var(--warn);
  border: 1px solid rgba(255, 193, 7, 0.3);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
}
.bar-multi {
  font-size: 11px;
  color: var(--t2);
  border: 1px solid var(--b2);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
}

.bar-alert {
  font-size: 11px;
  color: var(--red);
  border: 1px solid rgba(167, 17, 17, 0.4);
  border-radius: 4px;
  padding: 1px 6px;
  margin-right: 6px;
}

.bar-timer {
  font-size: 16px;
  font-weight: 600;
  color: var(--ok);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
</style>
