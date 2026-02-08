<script setup lang="ts">
/**
 * Material Group Basic Form
 * Reusable component for basic material group fields
 */

interface BasicFields {
  code: string
  name: string
  density: number
}

const model = defineModel<BasicFields>({ required: true })
</script>

<template>
  <div>
    <div class="form-field">
      <label>Kod *</label>
      <input v-model="model.code" type="text" maxlength="20" class="form-input" required />
    </div>
    <div class="form-field">
      <label>Nazev *</label>
      <input v-model="model.name" type="text" maxlength="100" class="form-input" required />
    </div>
    <div class="form-field">
      <label>Hustota (kg/dm3) *</label>
      <input v-model.number="model.density" type="number" step="0.001" min="0" class="form-input" required />
    </div>
  </div>
</template>
