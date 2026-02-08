<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  roughingMain: number
  roughingAux: number
  finishingMain: number
  finishingAux: number
}

const props = defineProps<Props>()

const roughingTotal = computed(() => props.roughingMain + props.roughingAux)
const finishingTotal = computed(() => props.finishingMain + props.finishingAux)
const totalMin = computed(() => roughingTotal.value + finishingTotal.value)

const roughingPercent = computed(() =>
  totalMin.value > 0 ? ((roughingTotal.value / totalMin.value) * 100).toFixed(0) : '0'
)
const finishingPercent = computed(() =>
  totalMin.value > 0 ? ((finishingTotal.value / totalMin.value) * 100).toFixed(0) : '0'
)
</script>

<template>
  <div class="time-breakdown-widget">
    <h3>Rozdělení času</h3>
    <div class="breakdown-grid">
      <!-- Roughing Section -->
      <div class="breakdown-section">
        <div class="section-header">Hrubování ({{ roughingTotal.toFixed(2) }} min - {{ roughingPercent }}%)</div>

        <div class="breakdown-item roughing">
          <div class="breakdown-bar">
            <div class="bar-fill" :style="{ width: roughingPercent + '%' }"></div>
          </div>
          <div class="breakdown-content">
            <span class="label">Hlavní čas (odebírání materiálu)</span>
            <span class="value">{{ roughingMain.toFixed(2) }} min</span>
          </div>
        </div>

        <div class="breakdown-item roughing-aux">
          <div class="breakdown-bar aux">
            <div class="bar-fill" :style="{ width: ((roughingAux / totalMin) * 100).toFixed(0) + '%' }"></div>
          </div>
          <div class="breakdown-content">
            <span class="label">Vedlejší čas (přejezdy, 20%)</span>
            <span class="value">{{ roughingAux.toFixed(2) }} min</span>
          </div>
        </div>
      </div>

      <!-- Finishing Section -->
      <div class="breakdown-section">
        <div class="section-header">Dokončování ({{ finishingTotal.toFixed(2) }} min - {{ finishingPercent }}%)</div>

        <div class="breakdown-item finishing">
          <div class="breakdown-bar">
            <div class="bar-fill" :style="{ width: finishingPercent + '%' }"></div>
          </div>
          <div class="breakdown-content">
            <span class="label">Hlavní čas (povrch)</span>
            <span class="value">{{ finishingMain.toFixed(2) }} min</span>
          </div>
        </div>

        <div class="breakdown-item finishing-aux">
          <div class="breakdown-bar aux">
            <div class="bar-fill" :style="{ width: ((finishingAux / totalMin) * 100).toFixed(0) + '%' }"></div>
          </div>
          <div class="breakdown-content">
            <span class="label">Vedlejší čas (přejezdy, 15%)</span>
            <span class="value">{{ finishingAux.toFixed(2) }} min</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-breakdown-widget {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.breakdown-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.breakdown-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-base);
  border-radius: var(--radius-md);
}

.section-header {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.breakdown-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.breakdown-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.breakdown-bar.aux {
  height: 4px;
}

.breakdown-bar .bar-fill {
  height: 100%;
  transition: width var(--duration-normal) var(--ease-out);
}

.breakdown-item.roughing .bar-fill {
  background: var(--color-primary);
}

.breakdown-item.roughing-aux .bar-fill {
  background: rgba(99, 102, 241, 0.5);
}

.breakdown-item.finishing .bar-fill {
  background: var(--color-success);
}

.breakdown-item.finishing-aux .bar-fill {
  background: rgba(34, 197, 94, 0.5);
}

.breakdown-content {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-3);
  align-items: baseline;
}

.breakdown-content .label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.breakdown-content .value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
</style>
