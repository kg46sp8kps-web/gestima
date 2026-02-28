<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Check, X } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'
import * as materialsApi from '@/api/materials'
import type { MaterialItemDetail } from '@/types/material-item'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import InlineSelect from '@/components/ui/InlineSelect.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  materialNumber: string
}

const props = defineProps<Props>()
const ui = useUiStore()

const detail = ref<MaterialItemDetail | null>(null)
const loading = ref(false)
const saving = ref(false)

// ── Edit state (vždy aktivní, edit-in-place) ──
const editUom = ref<string>('kg')
const editConvUom = ref<string>('')       // '' = žádná konverze
const editConvFactor = ref<number | null>(null)

watch(editConvUom, (val) => {
  if (!val) editConvFactor.value = null
})

function initEdit(d: MaterialItemDetail) {
  editUom.value = d.uom
  editConvUom.value = d.conv_uom ?? ''
  editConvFactor.value = d.conv_factor
}

const isDirty = computed(() => {
  if (!detail.value) return false
  return (
    editUom.value !== detail.value.uom ||
    (editConvUom.value || null) !== detail.value.conv_uom ||
    editConvFactor.value !== detail.value.conv_factor
  )
})

const previewText = computed(() => {
  if (!editConvUom.value || editConvFactor.value == null) return null
  return `1 ${editConvUom.value} = ${editConvFactor.value} ${editUom.value}`
})

function discardChanges() {
  if (detail.value) initEdit(detail.value)
}

async function saveChanges() {
  if (!detail.value) return
  if (editConvUom.value && (editConvFactor.value == null || editConvFactor.value <= 0)) {
    ui.showError('Konverzní faktor musí být kladné číslo')
    return
  }
  saving.value = true
  try {
    detail.value = await materialsApi.updateItem(detail.value.material_number, {
      uom: editUom.value,
      conv_uom: editConvUom.value || null,
      conv_factor: editConvFactor.value,
      version: detail.value.version,
    })
    initEdit(detail.value)
    ui.showSuccess('UOM uloženo')
  } catch {
    ui.showError('Chyba při ukládání UOM')
  } finally {
    saving.value = false
  }
}

const SHAPE_LABELS: Record<string, string> = {
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Deska',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

watch(
  () => props.materialNumber,
  async (num) => {
    if (!num) { detail.value = null; return }
    if (detail.value?.material_number === num) return
    loading.value = true
    try {
      detail.value = await materialsApi.getByNumber(num)
      initEdit(detail.value)
    } catch {
      ui.showError('Chyba při načítání polotovaru')
      detail.value = null
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="mat-det">
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <template v-else-if="detail">
      <!-- Info bar -->
      <div class="det-bar">
        <span class="det-pn">{{ detail.material_number }}</span>
        <span class="det-nm">{{ detail.name }}</span>
        <div class="det-bgs">
          <span class="bdg">
            <span class="dot o" />
            {{ SHAPE_LABELS[detail.shape] ?? detail.shape }}
          </span>
          <InlineSelect
            v-model="editUom"
            :ghost="true"
            :small="true"
            class="uom-select"
            data-testid="mat-uom-select"
            title="Základní měrná jednotka"
          >
            <option value="kg">kg</option>
            <option value="ks">ks</option>
          </InlineSelect>
        </div>
      </div>
      <!-- Dimensions ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div v-if="detail.code" class="rib-i">
            <span class="rib-l">Kód</span>
            <span class="rib-v m">{{ detail.code }}</span>
          </div>
          <div v-if="detail.diameter != null" class="rib-i">
            <span class="rib-l">∅</span>
            <span class="rib-v m">{{ formatNumber(detail.diameter) }} mm</span>
          </div>
          <div v-if="detail.width != null" class="rib-i">
            <span class="rib-l">Šířka</span>
            <span class="rib-v m">{{ formatNumber(detail.width) }} mm</span>
          </div>
          <div v-if="detail.thickness != null" class="rib-i">
            <span class="rib-l">Tloušťka</span>
            <span class="rib-v m">{{ formatNumber(detail.thickness) }} mm</span>
          </div>
          <div v-if="detail.wall_thickness != null" class="rib-i">
            <span class="rib-l">Stěna</span>
            <span class="rib-v m">{{ formatNumber(detail.wall_thickness) }} mm</span>
          </div>
          <div v-if="detail.standard_length != null" class="rib-i">
            <span class="rib-l">Std. délka</span>
            <span class="rib-v m">{{ formatNumber(detail.standard_length) }} mm</span>
          </div>
        </div>
      </div>
      <!-- Conversion ribbon -->
      <div class="rib conv-rib">
        <div class="conv-row">
          <span class="rib-l">Konverze</span>
          <span class="conv-eq">1</span>
          <InlineSelect
            v-model="editConvUom"
            :ghost="true"
            class="conv-uom-sel"
            data-testid="mat-conv-uom-select"
          >
            <option value="">—</option>
            <option value="m">m</option>
            <option value="mm">mm</option>
          </InlineSelect>
          <template v-if="editConvUom">
            <span class="conv-eq">=</span>
            <InlineInput
              v-model="editConvFactor"
              :numeric="true"
              :ghost="true"
              placeholder="0.000"
              class="conv-factor-inp"
              data-testid="mat-conv-factor-input"
            />
            <span class="conv-uom-label">{{ editUom }}</span>
          </template>
          <span v-if="previewText" class="conv-preview">{{ previewText }}</span>
          <template v-if="isDirty">
            <button
              class="icon-btn"
              :disabled="saving"
              data-testid="mat-uom-save"
              title="Uložit"
              @click="saveChanges"
            >
              <Check :size="ICON_SIZE_SM" />
            </button>
            <button
              class="icon-btn"
              :disabled="saving"
              data-testid="mat-uom-cancel"
              title="Zrušit"
              @click="discardChanges"
            >
              <X :size="ICON_SIZE_SM" />
            </button>
          </template>
        </div>
      </div>
      <!-- Extra ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div v-if="detail.norms" class="rib-i">
            <span class="rib-l">Normy</span>
            <span class="rib-v">{{ detail.norms }}</span>
          </div>
          <div v-if="detail.supplier_code" class="rib-i">
            <span class="rib-l">Kód dodavatele</span>
            <span class="rib-v m">{{ detail.supplier_code }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Cen. kat.</span>
            <span class="rib-v">{{ detail.price_category.code }} · {{ detail.price_category.name }}</span>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Polotovar nenalezen</span>
    </div>
  </div>
</template>

<style scoped>
.mat-det {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Placeholder ─── */
.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Info bar ─── */
.det-bar {
  height: 30px;
  padding: 0 var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  overflow: hidden;
}
.det-pn { font-size: var(--fs); font-weight: 600; color: var(--t1); flex-shrink: 0; letter-spacing: 0.02em; }
.det-nm { font-size: var(--fs); color: var(--t3); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.det-bgs { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

/* ─── UOM select in bar ─── */
.uom-select { flex-shrink: 0; }

/* ─── Badge ─── */
.bdg { display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px; font-size: var(--fsm); font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2); }
.bdg .dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.dot.ok { background: var(--ok); }
.dot.w  { background: var(--warn); }
.dot.e  { background: var(--err); }
.dot.o  { background: var(--t4); }

/* ─── Ribbon ─── */
.rib { padding: 4px var(--pad); background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--b1); flex-shrink: 0; }
.rib-r { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { }

/* ─── Conversion ribbon ─── */
.conv-rib { }
.conv-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  min-height: 22px;
}
.conv-eq {
  font-size: var(--fsm);
  color: var(--t4);
  font-weight: 500;
}
.conv-uom-sel { min-width: 32px; }
.conv-factor-inp { width: 64px; }
.conv-uom-label {
  font-size: var(--fsm);
  color: var(--t4);
  font-weight: 500;
}
.conv-preview {
  font-size: var(--fsm);
  color: var(--ok);
  font-weight: 500;
  letter-spacing: 0.02em;
  margin-left: 4px;
}
</style>
