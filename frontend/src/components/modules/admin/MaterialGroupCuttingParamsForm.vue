<script setup lang="ts">
/**
 * Material Group Cutting Parameters Form
 * Reusable component for editing cutting conditions
 */

interface CuttingParams {
  iso_group: string | null
  hardness_hb: number | null
  mrr_turning_roughing: number | null
  mrr_turning_finishing: number | null
  mrr_milling_roughing: number | null
  mrr_milling_finishing: number | null
  cutting_speed_turning: number | null
  cutting_speed_milling: number | null
  feed_turning: number | null
  feed_milling: number | null
  deep_pocket_penalty: number
  thin_wall_penalty: number
  cutting_data_source: string | null
}

const model = defineModel<CuttingParams>({ required: true })
</script>

<template>
  <div class="cutting-params-form">
    <h4>Klasifikace</h4>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>ISO Skupina</label>
        <select v-model="model.iso_group" class="form-select">
          <option :value="null">-- Nezadano --</option>
          <option value="P">P - Ocel</option>
          <option value="M">M - Nerez</option>
          <option value="K">K - Litina/Nastrojova</option>
          <option value="N">N - Nezelezne</option>
          <option value="S">S - Superslitiny</option>
          <option value="H">H - Kalene</option>
        </select>
      </div>
      <div class="form-field">
        <label>Tvrdost (HB)</label>
        <input v-model.number="model.hardness_hb" type="number" step="1" class="form-input" />
      </div>
    </div>

    <h4>Material Removal Rate (cm3/min)</h4>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>Soustruzeni - hrubovani</label>
        <input v-model.number="model.mrr_turning_roughing" type="number" step="1" class="form-input" />
      </div>
      <div class="form-field">
        <label>Soustruzeni - dokoncovani</label>
        <input v-model.number="model.mrr_turning_finishing" type="number" step="1" class="form-input" />
      </div>
    </div>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>Frezovani - hrubovani</label>
        <input v-model.number="model.mrr_milling_roughing" type="number" step="1" class="form-input" />
      </div>
      <div class="form-field">
        <label>Frezovani - dokoncovani</label>
        <input v-model.number="model.mrr_milling_finishing" type="number" step="1" class="form-input" />
      </div>
    </div>

    <h4>Rezne rychlosti (m/min)</h4>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>Soustruzeni</label>
        <input v-model.number="model.cutting_speed_turning" type="number" step="1" class="form-input" />
      </div>
      <div class="form-field">
        <label>Frezovani</label>
        <input v-model.number="model.cutting_speed_milling" type="number" step="1" class="form-input" />
      </div>
    </div>

    <h4>Posuvy</h4>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>Soustruzeni (mm/ot)</label>
        <input v-model.number="model.feed_turning" type="number" step="0.01" class="form-input" />
      </div>
      <div class="form-field">
        <label>Frezovani (mm/zub)</label>
        <input v-model.number="model.feed_milling" type="number" step="0.01" class="form-input" />
      </div>
    </div>

    <h4>Penalizace</h4>
    <div class="form-grid-2col">
      <div class="form-field">
        <label>Hluboka kapsa (multiplikator)</label>
        <input v-model.number="model.deep_pocket_penalty" type="number" step="0.1" min="1.0" class="form-input" />
      </div>
      <div class="form-field">
        <label>Tenka stena (multiplikator)</label>
        <input v-model.number="model.thin_wall_penalty" type="number" step="0.1" min="1.0" class="form-input" />
      </div>
    </div>

    <div class="form-field">
      <label>Zdroj dat</label>
      <input v-model="model.cutting_data_source" type="text" placeholder="Sandvik 2024, Iscar 2024" class="form-input" />
    </div>
  </div>
</template>

<style scoped>
.cutting-params-form h4 {
  margin: var(--space-4) 0 var(--space-2) 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
  padding-bottom: var(--space-2);
}

.cutting-params-form h4:first-child {
  margin-top: 0;
}
</style>
