<script setup lang="ts">
import { ref, watch } from 'vue'
import { useUiStore } from '@/stores/ui'
import * as materialsApi from '@/api/materials'
import type { MaterialItemDetail } from '@/types/material-item'
import { formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  materialNumber: string
}

const props = defineProps<Props>()
const ui = useUiStore()

const detail = ref<MaterialItemDetail | null>(null)
const loading = ref(false)

const SHAPE_LABELS: Record<string, string> = {
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Plech',
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
          <div v-if="detail.weight_per_meter != null" class="rib-i">
            <span class="rib-l">kg/m</span>
            <span class="rib-v m">{{ formatNumber(detail.weight_per_meter, 3) }}</span>
          </div>
          <div v-if="detail.standard_length != null" class="rib-i">
            <span class="rib-l">Std. délka</span>
            <span class="rib-v m">{{ formatNumber(detail.standard_length) }} mm</span>
          </div>
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
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

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
.det-bgs { display: flex; gap: 3px; flex-shrink: 0; }

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
.rib-v.m { font-family: var(--mono); }
</style>
