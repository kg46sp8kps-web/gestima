<script setup lang="ts">
/**
 * TimeVision Features Panel (FT v2) - Feature extraction + editable table
 */
import { ref, computed, watch } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import type { FeatureItem, FeaturesExtraction } from '@/types/time-vision'
import { exportFeaturesTrainingDataUrl, calculateFeaturesTime } from '@/api/time-vision'
import TimeVisionFeaturesTable from './TimeVisionFeaturesTable.vue'
import { Loader, Sparkles, Download, Save, Calculator } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  filename: string | null
}
const props = defineProps<Props>()
const store = useTimeVisionStore()

const estimation = computed(() => store.featuresEstimation)
const cuttingMode = ref<'low' | 'mid' | 'high'>('mid')
const calculating = ref(false)
const saving = ref(false)

const featuresData = computed<FeaturesExtraction | null>(() => {
  if (!estimation.value) return null
  const jsonStr = estimation.value.features_corrected_json || estimation.value.features_json
  if (!jsonStr) return null
  try {
    return JSON.parse(jsonStr) as FeaturesExtraction
  } catch {
    return null
  }
})

const editableFeatures = ref<FeatureItem[]>([])

watch(featuresData, (newData) => {
  if (newData?.features) {
    editableFeatures.value = JSON.parse(JSON.stringify(newData.features))
  } else {
    editableFeatures.value = []
  }
}, { immediate: true })

const progressPercent = computed(() => {
  if (!store.featuresProcessingStep) return 0
  return Math.round((store.featuresProcessingStep.step / store.featuresProcessingStep.total) * 100)
})

async function runExtraction() {
  if (!props.filename) return
  const drawing = store.drawings.find(d => d.filename === props.filename)
  await store.processFeaturesOpenAI(props.filename, drawing?.file_id ?? null)
}

async function handleSaveFeatures() {
  if (!estimation.value || !featuresData.value) return
  saving.value = true
  try {
    const corrected: FeaturesExtraction = {
      ...featuresData.value,
      features: editableFeatures.value,
    }
    await store.saveCorrectedFeatures(
      estimation.value.id,
      JSON.stringify(corrected, null, 2),
      estimation.value.version,
    )
  } finally {
    saving.value = false
  }
}

async function handleCalculate() {
  if (!estimation.value) return
  calculating.value = true
  try {
    const result = await calculateFeaturesTime(estimation.value.id, cuttingMode.value)
    if (result.feature_times) {
      // Clear all times first
      editableFeatures.value.forEach(f => { f.time_sec = undefined })
      // Match by type+detail (handles duplicates)
      const used = new Set<number>()
      for (const ft of result.feature_times) {
        const idx = editableFeatures.value.findIndex(
          (f, i) => f.type === ft.type && f.detail === ft.detail && !used.has(i)
        )
        if (idx >= 0 && editableFeatures.value[idx]) {
          editableFeatures.value[idx].time_sec = ft.time_sec
          used.add(idx)
        }
      }
    }
  } finally {
    calculating.value = false
  }
}

function downloadTrainingData() {
  const token = localStorage.getItem('gestima_token')
  const url = exportFeaturesTrainingDataUrl()
  window.open(`${url}${token ? `?token=${token}` : ''}`, '_blank')
}
</script>

<template>
  <div class="features-panel">
    <div class="panel-header">
      <h3>FT v2 — Features</h3>
      <div class="model-badge">
        <Sparkles :size="ICON_SIZE.SMALL" />
        <span>gpt-4o base</span>
      </div>
    </div>

    <div v-if="store.featuresProcessing" class="progress-section">
      <div class="progress-header">
        <Loader :size="ICON_SIZE.SMALL" class="spinner" />
        <span class="progress-label">{{ store.featuresProcessingStep?.label ?? 'Připravuji...' }}</span>
        <span class="progress-pct">{{ progressPercent }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
      </div>
    </div>

    <div v-if="store.featuresError" class="error-bar">{{ store.featuresError }}</div>

    <div v-if="!estimation && !store.featuresProcessing" class="empty-state">
      <Sparkles :size="ICON_SIZE.XLARGE" class="empty-icon" />
      <p>Features ještě nebyly extrahovány.</p>
      <button class="btn-primary" :disabled="!filename" @click="runExtraction">
        <Sparkles :size="ICON_SIZE.SMALL" />
        Extrahovat features
      </button>
    </div>

    <div v-if="estimation && featuresData" :key="estimation.id" class="features-result">
      <div class="info-grid">
        <div v-if="featuresData.drawing_number" class="info-item">
          <label>Výkres</label>
          <span>{{ featuresData.drawing_number }}</span>
        </div>
        <div v-if="featuresData.part_name" class="info-item">
          <label>Název</label>
          <span>{{ featuresData.part_name }}</span>
        </div>
        <div v-if="featuresData.part_type" class="info-item">
          <label>Typ</label>
          <span class="badge">{{ featuresData.part_type }}</span>
        </div>
        <div v-if="featuresData.material?.designation" class="info-item">
          <label>Materiál</label>
          <span>{{ featuresData.material.designation }}</span>
        </div>
      </div>

      <div v-if="featuresData.overall_dimensions" class="dims-row">
        <span v-if="featuresData.overall_dimensions.max_diameter_mm">
          ø{{ featuresData.overall_dimensions.max_diameter_mm }}
        </span>
        <span v-if="featuresData.overall_dimensions.max_length_mm">
          L{{ featuresData.overall_dimensions.max_length_mm }}
        </span>
        <span v-if="featuresData.overall_dimensions.max_width_mm">
          W{{ featuresData.overall_dimensions.max_width_mm }}
        </span>
        <span v-if="featuresData.overall_dimensions.max_height_mm">
          H{{ featuresData.overall_dimensions.max_height_mm }}
        </span>
      </div>

      <TimeVisionFeaturesTable
        v-model:features="editableFeatures"
      />

      <div class="calc-controls">
        <select v-model="cuttingMode" class="mode-select">
          <option value="low">Low</option>
          <option value="mid">Mid</option>
          <option value="high">High</option>
        </select>
        <button class="btn-secondary" :disabled="calculating" @click="handleCalculate">
          <Calculator :size="ICON_SIZE.SMALL" />
          {{ calculating ? 'Počítám...' : 'Přepočítat' }}
        </button>
      </div>

      <div class="actions">
        <button class="btn-primary-sm" :disabled="saving" @click="handleSaveFeatures">
          <Save :size="ICON_SIZE.SMALL" />
          {{ saving ? 'Ukládám...' : 'Uložit korekce' }}
        </button>
        <button class="btn-secondary" :disabled="store.featuresProcessing" @click="runExtraction">
          <Sparkles :size="ICON_SIZE.SMALL" />
          Re-extrahovat
        </button>
        <button class="btn-secondary" @click="downloadTrainingData">
          <Download :size="ICON_SIZE.SMALL" />
          Export
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.features-panel { padding: var(--pad); }
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--pad);
}
.panel-header h3 {
  font-size: var(--fs); font-weight: 600; margin: 0;
}
.model-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 6px; background: var(--ground);
  color: var(--t3); border-radius: var(--rs);
  font-size: var(--fs); font-weight: 600;
}
.empty-icon { color: var(--t3); opacity: 0.5; }
.info-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 6px; margin-bottom: var(--pad);
}
.info-item { display: flex; flex-direction: column; gap: 1px; }
.info-item label {
  font-size: var(--fs); color: var(--t3); text-transform: uppercase;
}
.info-item span { font-size: var(--fs); font-weight: 500; }
.dims-row {
  display: flex; gap: var(--pad); padding: 6px;
  background: var(--ground); border-radius: var(--rs);
  font-size: var(--fs); font-weight: 500;
  margin-bottom: var(--pad); font-variant-numeric: tabular-nums;
}
.calc-controls {
  display: flex; gap: 6px; align-items: center;
  margin: var(--pad) 0;
}
.mode-select {
  padding: 4px 6px;
  border: 1px solid var(--b2); border-radius: var(--rs);
  font-size: var(--fs); background: var(--ground); color: var(--t1);
}
.actions {
  display: flex; gap: 6px; flex-wrap: wrap;
  margin-top: var(--pad); padding-top: var(--pad);
  border-top: 1px solid var(--b2);
}
.progress-section {
  padding: var(--pad); background: var(--surface);
  border-radius: var(--r); margin-bottom: 12px;
}
.progress-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
}
.progress-label { flex: 1; font-size: var(--fs); font-weight: 500; }
.progress-pct { font-size: var(--fs); color: var(--t3); }
.progress-track {
  height: 4px; background: var(--ground); border-radius: var(--rs); overflow: hidden;
}
.progress-fill {
  height: 100%; background: var(--red); border-radius: var(--rs); transition: width 0.4s ease;
}
.error-bar {
  padding: 6px var(--pad);
  background: rgba(248,113,113,0.15); color: var(--err);
  font-size: var(--fs); border-radius: var(--rs); margin-bottom: var(--pad);
}
</style>
