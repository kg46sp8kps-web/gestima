<script setup lang="ts">
import type { FeatureItem } from '@/types/time-vision'
import { Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import type { FeatureTypeMeta } from '@/api/time-vision'
import { ICON_SIZE } from '@/config/design'

const features = defineModel<FeatureItem[]>('features', { required: true })
const store = useTimeVisionStore()

onMounted(() => store.loadFeatureTypes())

const featureTypes = computed<FeatureTypeMeta[]>(() => store.featureTypesCatalog?.types ?? [])
const featureGroups = computed<Record<string, string>>(() => store.featureTypesCatalog?.groups ?? {})

const featureMetaMap = computed(() => new Map(featureTypes.value.map(m => [m.key, m])))

const groupedFeatures = computed(() => {
  const g: Record<string, FeatureTypeMeta[]> = {}
  featureTypes.value.forEach(m => (g[m.group] = g[m.group] || []).push(m))
  return g
})

const addFeature = () => features.value.push({ type: 'through_hole', count: 1, detail: '' })
const removeFeature = (i: number) => features.value.splice(i, 1)
const getFeatureMeta = (type: string) => featureMetaMap.value.get(type)
</script>

<template>
  <div class="features-table">
    <div class="table-header">
      <span class="col-indicator"></span>
      <span class="col-type">Typ</span>
      <span class="col-count">#</span>
      <span class="col-detail">Detail</span>
      <span class="col-time">Čas</span>
      <span class="col-actions"></span>
    </div>
    <div
      v-for="(feature, index) in features"
      :key="index"
      class="table-row"
      :class="{ 'row-info': !getFeatureMeta(feature.type)?.has_time }"
    >
      <span class="col-indicator">
        <span
          class="indicator-dot"
          :class="getFeatureMeta(feature.type)?.has_time ? 'dot-time' : 'dot-info'"
        ></span>
      </span>
      <div class="col-type">
        <select
          v-model="feature.type"
          class="input-sm"
          :title="getFeatureMeta(feature.type)?.description + '\n\nPříklad: ' + getFeatureMeta(feature.type)?.example"
        >
          <optgroup
            v-for="(groupKey) in Object.keys(groupedFeatures)"
            :key="groupKey"
            :label="featureGroups[groupKey]"
          >
            <option
              v-for="meta in groupedFeatures[groupKey]"
              :key="meta.key"
              :value="meta.key"
            >
              {{ meta.label_cs }}
            </option>
          </optgroup>
        </select>
      </div>
      <div class="col-count">
        <input
          v-model.number="feature.count"
          type="number"
          min="1"
          max="100"
          class="input-sm"
        />
      </div>
      <div class="col-detail">
        <input
          v-model="feature.detail"
          type="text"
          placeholder="rozměr..."
          class="input-sm"
        />
      </div>
      <span class="col-time time-val">
        <template v-if="getFeatureMeta(feature.type)?.has_time">
          {{ feature.time_sec != null ? feature.time_sec.toFixed(0) + 's' : '?' }}
        </template>
        <template v-else>—</template>
      </span>
      <button class="col-actions btn-icon" @click="removeFeature(index)">
        <Trash2 :size="ICON_SIZE.SMALL" />
      </button>
    </div>
    <button class="btn-add" @click="addFeature">
      <Plus :size="ICON_SIZE.SMALL" />
      Přidat feature
    </button>
    <div class="table-footer">
      {{ features.length }} features
    </div>
  </div>
</template>

<style scoped>
.features-table { border: 1px solid var(--border-default); border-radius: var(--radius-sm); overflow: hidden; margin-bottom: var(--space-2); }
.table-header { display: flex; gap: var(--space-1); padding: var(--space-1) var(--space-2); background: var(--bg-raised); font-size: var(--text-sm); text-transform: uppercase; color: var(--text-tertiary); font-weight: 600; }
.table-row { display: flex; gap: var(--space-1); padding: var(--space-1) var(--space-2); border-top: 1px solid var(--border-default); align-items: center; background: var(--bg-surface); transition: background var(--duration-fast); }
.table-row:hover { background: var(--state-hover); }
.table-row.row-info { background: var(--bg-base); opacity: 0.7; }
.table-row.row-info:hover { opacity: 1; background: var(--state-hover); }
.col-indicator { width: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.indicator-dot { width: 6px; height: 6px; border-radius: 50%; }
.indicator-dot.dot-time { background: var(--status-ok); }
.indicator-dot.dot-info { background: var(--text-tertiary); }
.col-type { width: 160px; flex-shrink: 0; }
.col-count { width: 40px; flex-shrink: 0; text-align: center; }
.col-detail { flex: 1; min-width: 0; }
.col-time { width: 48px; flex-shrink: 0; text-align: right; }
.col-actions { width: 28px; flex-shrink: 0; }
.input-sm { padding: var(--space-1); border: 1px solid var(--border-default); border-radius: var(--radius-sm); font-size: var(--text-sm); background: var(--bg-input); color: var(--text-primary); width: 100%; }
.input-sm:focus { outline: none; border-color: var(--focus-ring); background: var(--focus-bg); box-shadow: 0 0 0 1px var(--active); }
.time-val { font-size: var(--text-sm); color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.btn-icon { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border: none; background: none; color: var(--text-tertiary); cursor: pointer; border-radius: var(--radius-sm); transition: var(--transition-fast); }
.btn-icon:hover { background: var(--status-error-bg); color: var(--status-error); }
.btn-add { display: flex; align-items: center; gap: var(--space-1); width: 100%; padding: var(--space-2); border: none; background: none; cursor: pointer; font-size: var(--text-sm); color: var(--text-tertiary); border-top: 1px solid var(--border-default); transition: var(--transition-fast); }
.btn-add:hover { background: var(--state-hover); color: var(--text-primary); }
.table-footer { padding: var(--space-1) var(--space-2); font-size: var(--text-sm); color: var(--text-tertiary); text-align: right; border-top: 1px solid var(--border-default); background: var(--bg-raised); }
</style>
