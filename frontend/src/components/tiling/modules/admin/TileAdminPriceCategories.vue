<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { PencilIcon, PlusIcon, Trash2Icon } from 'lucide-vue-next'
import * as materialsApi from '@/api/materials'
import type { MaterialPriceCategory, MaterialPriceTier, MaterialPriceTierCreate } from '@/types/admin-user'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import Modal from '@/components/ui/Modal.vue'
import Input from '@/components/ui/Input.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import { ICON_SIZE_SM } from '@/config/design'

const cats = ref<MaterialPriceCategory[]>([])
const loading = ref(false)
const error = ref(false)
const search = ref('')
const saving = ref(false)
const ui = useUiStore()

// Modal state
const modalOpen = ref(false)
const modalCat = ref<MaterialPriceCategory | null>(null)
const modalTiers = ref<MaterialPriceTier[]>([])
const tiersLoading = ref(false)

// Draft for category properties
interface CatDraft {
  name: string
  iso_group: string | null
  shape: string | null
  cutting_speed_turning: number | null
  cutting_speed_milling: number | null
  version: number
}
const catDraft = ref<CatDraft>({
  name: '',
  iso_group: null,
  shape: null,
  cutting_speed_turning: null,
  cutting_speed_milling: null,
  version: 0,
})

// New tier form
const newTier = ref<{ min_weight: number | null; max_weight: number | null; price_per_kg: number | null }>({
  min_weight: null,
  max_weight: null,
  price_per_kg: null,
})
const addingTier = ref(false)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return cats.value
  return cats.value.filter(c =>
    c.code.toLowerCase().includes(q) ||
    c.name.toLowerCase().includes(q) ||
    (c.iso_group ?? '').toLowerCase().includes(q) ||
    (c.material_group?.name ?? '').toLowerCase().includes(q),
  )
})

function tierPreview(cat: MaterialPriceCategory): string {
  if (!cat.tiers || cat.tiers.length === 0) return '—'
  const sorted = [...cat.tiers].sort((a, b) => a.min_weight - b.min_weight)
  const prices = sorted.slice(0, 3).map(t => formatNumber(t.price_per_kg, 0))
  return prices.join(' / ') + ' Kč'
}

async function load() {
  loading.value = true
  error.value = false
  try {
    cats.value = await materialsApi.getPriceCategories()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

async function openModal(cat: MaterialPriceCategory) {
  modalCat.value = cat
  catDraft.value = {
    name: cat.name,
    iso_group: cat.iso_group,
    shape: cat.shape,
    cutting_speed_turning: cat.cutting_speed_turning,
    cutting_speed_milling: cat.cutting_speed_milling,
    version: cat.version,
  }
  newTier.value = { min_weight: null, max_weight: null, price_per_kg: null }
  modalOpen.value = true

  tiersLoading.value = true
  try {
    modalTiers.value = await materialsApi.getPriceTiers(cat.id)
    modalTiers.value.sort((a, b) => a.min_weight - b.min_weight)
  } catch {
    ui.showError('Chyba při načítání tierů')
  } finally {
    tiersLoading.value = false
  }
}

async function saveCategory() {
  const cat = modalCat.value
  if (!cat) return
  saving.value = true
  try {
    const updated = await materialsApi.updatePriceCategory(cat.id, catDraft.value)
    const idx = cats.value.findIndex(c => c.id === cat.id)
    if (idx !== -1) {
      const existing = cats.value[idx]!
      const existingTiers = existing.tiers
      cats.value[idx] = updated
      cats.value[idx]!.tiers = existingTiers ?? modalTiers.value
    }
    modalCat.value = updated
    catDraft.value.version = updated.version
    ui.showSuccess('Kategorie uložena')
  } catch {
    ui.showError('Chyba při ukládání kategorie')
  } finally {
    saving.value = false
  }
}

async function addTier() {
  const cat = modalCat.value
  if (!cat || newTier.value.min_weight == null || newTier.value.price_per_kg == null) return
  addingTier.value = true
  try {
    const payload: MaterialPriceTierCreate = {
      price_category_id: cat.id,
      min_weight: newTier.value.min_weight,
      max_weight: newTier.value.max_weight,
      price_per_kg: newTier.value.price_per_kg,
    }
    const created = await materialsApi.createPriceTier(payload)
    modalTiers.value.push(created)
    modalTiers.value.sort((a, b) => a.min_weight - b.min_weight)
    newTier.value = { min_weight: null, max_weight: null, price_per_kg: null }
    syncTiersPreview(cat.id)
    ui.showSuccess('Tier přidán')
  } catch {
    ui.showError('Chyba při přidávání tieru')
  } finally {
    addingTier.value = false
  }
}

async function deleteTier(tier: MaterialPriceTier) {
  const cat = modalCat.value
  if (!cat) return
  try {
    await materialsApi.deletePriceTier(tier.id)
    modalTiers.value = modalTiers.value.filter(t => t.id !== tier.id)
    syncTiersPreview(cat.id)
    ui.showSuccess('Tier smazán')
  } catch {
    ui.showError('Chyba při mazání tieru')
  }
}

async function updateTierField(tier: MaterialPriceTier, field: 'min_weight' | 'max_weight' | 'price_per_kg', value: number | null) {
  const cat = modalCat.value
  if (!cat) return
  const old = tier[field]
  if (old === value) return
  const idx = modalTiers.value.findIndex(t => t.id === tier.id)
  if (idx === -1) return
  const snapshot = modalTiers.value[idx]!
  // Optimistic update
  if (field === 'min_weight') modalTiers.value[idx] = { ...snapshot, min_weight: value ?? snapshot.min_weight }
  else if (field === 'max_weight') modalTiers.value[idx] = { ...snapshot, max_weight: value }
  else modalTiers.value[idx] = { ...snapshot, price_per_kg: value ?? snapshot.price_per_kg }
  try {
    const payload = field === 'min_weight'
      ? { min_weight: value ?? undefined, version: tier.version }
      : field === 'max_weight'
        ? { max_weight: value, version: tier.version }
        : { price_per_kg: value ?? undefined, version: tier.version }
    const updated = await materialsApi.updatePriceTier(tier.id, payload)
    modalTiers.value[idx] = updated
    modalTiers.value.sort((a, b) => a.min_weight - b.min_weight)
    syncTiersPreview(cat.id)
  } catch {
    // revert
    modalTiers.value[idx] = snapshot
    ui.showError('Chyba při ukládání tieru')
  }
}

function syncTiersPreview(catId: number) {
  const idx = cats.value.findIndex(c => c.id === catId)
  if (idx !== -1) {
    cats.value[idx]!.tiers = [...modalTiers.value]
  }
}

function numVal(v: number | null): string {
  return v != null ? String(v) : ''
}

function parseOpt(v: string | number | null): number | null {
  if (v == null || v === '') return null
  const n = typeof v === 'number' ? v : parseFloat(String(v))
  return isNaN(n) ? null : n
}

onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="srch-bar">
      <Input
        bare
        v-model="search"
        class="srch-inp"
        type="text"
        placeholder="Hledat kód, název, ISO skupinu…"
        data-testid="price-cats-search-input"
      />
      <span class="srch-count">{{ filtered.length }} / {{ cats.length }}</span>
    </div>

    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!filtered.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádné kategorie' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:82px">Kód</th>
            <th>Název</th>
            <th style="width:55px">ISO sk.</th>
            <th style="width:65px">Tvar</th>
            <th>Skupina</th>
            <th style="width:140px">Tiery (Kč/kg)</th>
            <th style="width:28px" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in filtered"
            :key="c.id"
            class="row-clickable"
            :data-testid="`price-cat-row-${c.id}`"
            @click="openModal(c)"
          >
            <td class="t3">{{ c.code }}</td>
            <td>{{ c.name }}</td>
            <td class="t4">{{ c.iso_group ?? '—' }}</td>
            <td class="t4">{{ c.shape ?? '—' }}</td>
            <td class="t4">{{ c.material_group?.name ?? '—' }}</td>
            <td class="t4">{{ tierPreview(c) }}</td>
            <td class="act-cell">
              <button
                class="icon-btn icon-btn-brand icon-btn-sm"
                :data-testid="`price-cat-edit-${c.id}`"
                title="Upravit"
                @click.stop="openModal(c)"
              >
                <PencilIcon :size="ICON_SIZE_SM" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <Modal
      v-model="modalOpen"
      :title="modalCat ? `Cenová kategorie ${modalCat.code}` : 'Cenová kategorie'"
      size="md"
    >
      <div class="modal-form">

        <!-- Sekce 1: Vlastnosti -->
        <div class="form-section">
          <div class="section-title">Vlastnosti</div>
          <div class="form-grid">
            <div class="span-2">
              <Input
                label="Název"
                :modelValue="catDraft.name"
                @update:modelValue="catDraft.name = String($event ?? '')"
                data-testid="pc-modal-name"
              />
            </div>
            <Input
              label="ISO skupina"
              :modelValue="catDraft.iso_group ?? ''"
              @update:modelValue="catDraft.iso_group = String($event || '') || null"
              placeholder="P / M / K / N / S / H"
              data-testid="pc-modal-iso"
            />
            <Input
              label="Tvar polotovaru"
              :modelValue="catDraft.shape ?? ''"
              @update:modelValue="catDraft.shape = String($event || '') || null"
              placeholder="round / flat / tube…"
              data-testid="pc-modal-shape"
            />
            <Input
              label="Vc soustružení [m/min]"
              type="number"
              :modelValue="numVal(catDraft.cutting_speed_turning)"
              @update:modelValue="catDraft.cutting_speed_turning = parseOpt($event)"
              data-testid="pc-modal-vc-turn"
            />
            <Input
              label="Vc frézování [m/min]"
              type="number"
              :modelValue="numVal(catDraft.cutting_speed_milling)"
              @update:modelValue="catDraft.cutting_speed_milling = parseOpt($event)"
              data-testid="pc-modal-vc-mill"
            />
          </div>
        </div>

        <!-- Sekce 2: Cenové tiery -->
        <div class="form-section">
          <div class="section-title">Cenové tiery</div>

          <div v-if="tiersLoading" class="tiers-loading">
            <Spinner size="sm" />
          </div>
          <div v-else>
            <table v-if="modalTiers.length > 0" class="tiers-table">
              <thead>
                <tr>
                  <th>Od [kg]</th>
                  <th>Do [kg]</th>
                  <th class="r">Kč/kg</th>
                  <th style="width:28px" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="tier in modalTiers" :key="tier.id" :data-testid="`tier-row-${tier.id}`">
                  <td>
                    <InlineInput
                      numeric
                      :modelValue="tier.min_weight"
                      @update:modelValue="updateTierField(tier, 'min_weight', $event as number | null)"
                      type="number"
                      step="0.1"
                      class="ti-num"
                      :data-testid="`tier-min-${tier.id}`"
                    />
                  </td>
                  <td>
                    <InlineInput
                      numeric
                      :modelValue="tier.max_weight"
                      @update:modelValue="updateTierField(tier, 'max_weight', $event as number | null)"
                      type="number"
                      step="0.1"
                      class="ti-num"
                      :placeholder="'∞'"
                      :data-testid="`tier-max-${tier.id}`"
                    />
                  </td>
                  <td class="r">
                    <InlineInput
                      numeric
                      :modelValue="tier.price_per_kg"
                      @update:modelValue="updateTierField(tier, 'price_per_kg', $event as number | null)"
                      type="number"
                      step="0.01"
                      class="ti-num"
                      :data-testid="`tier-price-${tier.id}`"
                    />
                  </td>
                  <td class="act-cell-sm">
                    <button
                      class="icon-btn icon-btn-danger icon-btn-sm"
                      :data-testid="`tier-delete-${tier.id}`"
                      title="Smazat tier"
                      @click="deleteTier(tier)"
                    >
                      <Trash2Icon :size="ICON_SIZE_SM" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="tiers-empty">Žádné tiery</div>

            <!-- Přidat nový tier -->
            <div class="add-tier-row">
              <InlineInput
                numeric
                :modelValue="newTier.min_weight"
                @update:modelValue="newTier.min_weight = $event as number | null"
                type="number"
                step="0.1"
                placeholder="Od kg"
                class="ti-num"
                data-testid="tier-new-min"
              />
              <InlineInput
                numeric
                :modelValue="newTier.max_weight"
                @update:modelValue="newTier.max_weight = $event as number | null"
                type="number"
                step="0.1"
                placeholder="Do kg (∞)"
                class="ti-num"
                data-testid="tier-new-max"
              />
              <InlineInput
                numeric
                :modelValue="newTier.price_per_kg"
                @update:modelValue="newTier.price_per_kg = $event as number | null"
                type="number"
                step="0.01"
                placeholder="Kč/kg"
                class="ti-num"
                data-testid="tier-new-price"
              />
              <button
                class="icon-btn icon-btn-brand icon-btn-sm"
                :disabled="addingTier || newTier.min_weight == null || newTier.price_per_kg == null"
                data-testid="tier-add-btn"
                title="Přidat tier"
                @click="addTier"
              >
                <PlusIcon :size="ICON_SIZE_SM" />
              </button>
            </div>
          </div>
        </div>

      </div>

      <template #footer>
        <button class="btn-secondary" data-testid="pc-modal-cancel" @click="modalOpen = false">
          Zrušit
        </button>
        <button
          class="btn-primary"
          data-testid="pc-modal-save"
          :disabled="saving || !catDraft.name"
          @click="saveCategory"
        >
          {{ saving ? 'Ukládám…' : 'Uložit' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.srch-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.srch-inp {
  flex: 1; height: 28px; background: rgba(255,255,255,0.04); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t2); font-size: var(--fs);
  padding: 3px 6px; outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.srch-count { font-size: var(--fsm); color: var(--t4); white-space: nowrap; }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }
.row-clickable { cursor: pointer; }
.act-cell { text-align: right; padding: 2px 4px; }
.act-cell-sm { text-align: right; padding: 1px 2px; }

/* Modal */
.modal-form { display: flex; flex-direction: column; gap: 20px; }
.form-section { display: flex; flex-direction: column; gap: 10px; }
.section-title {
  font-size: var(--fsm); color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid var(--b1); padding-bottom: 4px;
}
.form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.span-2 { grid-column: 1 / -1; }

/* Tiers table */
.tiers-loading { display: flex; justify-content: center; padding: 12px; }
.tiers-empty { font-size: var(--fsm); color: var(--t4); padding: 6px 0; }
.tiers-table {
  width: 100%; border-collapse: collapse; font-size: var(--fs);
  margin-bottom: 8px;
}
.tiers-table th {
  font-size: var(--fsm); color: var(--t4); font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.04em;
  padding: 2px 4px 4px; text-align: left; border-bottom: 1px solid var(--b1);
}
.tiers-table th.r { text-align: right; }
.tiers-table td { padding: 3px 4px; border-bottom: 1px solid var(--b1); vertical-align: middle; }
.ti-num { width: 80px; }

/* Add tier row */
.add-tier-row {
  display: flex; align-items: center; gap: 8px;
  padding-top: 6px; border-top: 1px dashed var(--b2);
}
</style>
