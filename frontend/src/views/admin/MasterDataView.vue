<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FormTabs from '@/components/ui/FormTabs.vue'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import { useUiStore } from '@/stores/ui'
import { useOperationsStore } from '@/stores/operations'
import { Trash2, CheckCircle, XCircle } from 'lucide-vue-next'
import type { MaterialNorm, MaterialNormCreate, MaterialNormUpdate, MaterialGroup, MaterialGroupCreate, MaterialGroupUpdate, MaterialPriceCategory, MaterialPriceCategoryCreate, MaterialPriceCategoryUpdate, MaterialPriceTier, MaterialPriceTierCreate, MaterialPriceTierUpdate } from '@/types/material'
import type { WorkCenter, WorkCenterCreate, WorkCenterUpdate, WorkCenterType } from '@/types/operation'
import { confirm } from '@/composables/useDialog'
import {
  getMaterialNorms,
  createMaterialNorm,
  updateMaterialNorm,
  deleteMaterialNorm,
  getAdminMaterialGroups,
  createMaterialGroup,
  updateMaterialGroup,
  deleteMaterialGroup,
  getPriceCategories,
  createPriceCategory,
  updatePriceCategory,
  deletePriceCategory,
  getPriceTiers,
  createPriceTier,
  updatePriceTier,
  deletePriceTier
} from '@/api/materials'

const router = useRouter()
const uiStore = useUiStore()
const operationsStore = useOperationsStore()

const activeTab = ref(0)
const tabs = [
  { label: 'Normy materiálů', icon: 'ClipboardList' },
  { label: 'Skupiny materiálů', icon: 'Tag' },
  { label: 'Cenové kategorie', icon: 'DollarSign' },
  { label: 'Pracoviště', icon: 'Factory' }
]

// Tab 0: Material Norms
const norms = ref<MaterialNorm[]>([])
const groups = ref<MaterialGroup[]>([])
const loadingNorms = ref(false)
const showNormModal = ref(false)
const editingNorm = ref<MaterialNorm | null>(null)
const savingNorm = ref(false)

// Tab 1: Material Groups
const loadingGroups = ref(false)
const showGroupModal = ref(false)
const editingGroup = ref<MaterialGroup | null>(null)
const savingGroup = ref(false)

// Tab 2: Price Categories
const categories = ref<MaterialPriceCategory[]>([])
const loadingCategories = ref(false)
const showCategoryModal = ref(false)
const editingCategory = ref<MaterialPriceCategory | null>(null)
const savingCategory = ref(false)

// Price Tiers Management
const tiers = ref<MaterialPriceTier[]>([])
const selectedCategory = ref<MaterialPriceCategory | null>(null)
const loadingTiers = ref(false)
const showTierModal = ref(false)
const editingTier = ref<MaterialPriceTier | null>(null)
const savingTier = ref(false)

// Inline cell editing
const editingCell = ref<{ tierId: number; field: string } | null>(null)
const cellEditValue = ref<number | null>(null)

const normForm = ref({
  w_nr: '',
  en_iso: '',
  csn: '',
  aisi: '',
  material_group_id: 0,
  note: '',
  version: 0
})

const normColumns: Column[] = [
  { key: 'w_nr', label: 'W.Nr', sortable: true, width: '120px' },
  { key: 'en_iso', label: 'EN ISO', sortable: true, width: '120px' },
  { key: 'csn', label: 'ČSN', sortable: true, width: '100px' },
  { key: 'aisi', label: 'AISI', sortable: true, width: '100px' },
  { key: 'material_group.name', label: 'Skupina', sortable: true },
  { key: 'note', label: 'Poznámka', sortable: false }
]

const groupForm = ref({
  code: '',
  name: '',
  density: 0,
  version: 0
})

const groupColumns: Column[] = [
  { key: 'code', label: 'Kód', sortable: true, width: '120px' },
  { key: 'name', label: 'Název', sortable: true },
  { key: 'density', label: 'Hustota (kg/dm³)', sortable: true, width: '180px' }
]

const categoryForm = ref({
  code: '',
  name: '',
  material_group_id: null as number | null,
  version: 0
})

const categoryColumns: Column[] = [
  { key: 'code', label: 'Kód', sortable: true, width: '120px' },
  { key: 'name', label: 'Název', sortable: true },
  { key: 'material_group.name', label: 'Skupina materiálu', sortable: true }
]

const tierForm = ref({
  min_weight: 0,
  max_weight: null as number | null,
  price_per_kg: 0,
  version: 0
})

const tierColumns: Column[] = [
  { key: 'min_weight', label: 'Min. hmotnost (kg)', sortable: true, width: '150px' },
  { key: 'max_weight', label: 'Max. hmotnost (kg)', sortable: true, width: '150px' },
  { key: 'price_per_kg', label: 'Cena/kg (Kč)', sortable: true, format: 'currency', width: '150px' },
  { key: 'actions', label: 'Akce', sortable: false, width: '100px' }
]

// Tab 3: Work Centers
const showWorkCenterModal = ref(false)
const editingWorkCenter = ref<WorkCenter | null>(null)
const savingWorkCenter = ref(false)

const workCenterForm = ref({
  name: '',
  work_center_type: 'CNC_LATHE' as WorkCenterType,
  subtype: null as string | null,
  hourly_rate_amortization: null as number | null,
  hourly_rate_labor: null as number | null,
  hourly_rate_tools: null as number | null,
  hourly_rate_overhead: null as number | null,
  has_bar_feeder: false,
  has_sub_spindle: false,
  has_milling: false,
  suitable_for_series: true,
  suitable_for_single: true,
  setup_base_min: 0,
  setup_per_tool_min: 0,
  is_active: true,
  priority: 1,
  notes: null as string | null,
  version: 0
})

const workCenterColumns: Column[] = [
  { key: 'work_center_number', label: 'Číslo', sortable: true, width: '120px' },
  { key: 'name', label: 'Název', sortable: true },
  { key: 'work_center_type', label: 'Typ', sortable: true, width: '150px' },
  { key: 'hourly_rate_total', label: 'Hodinová sazba', format: 'currency', width: '150px' },
  { key: 'is_active', label: 'Aktivní', format: 'boolean', width: '100px' }
]

const loadingWorkCenters = ref(false)
const workCenters = computed(() => operationsStore.workCenters)

// Tab 0: Material Norms Methods
async function loadNorms() {
  loadingNorms.value = true
  try {
    norms.value = await getMaterialNorms()
  } catch (error) {
    uiStore.showError('Chyba při načítání norem')
    console.error(error)
  } finally {
    loadingNorms.value = false
  }
}

async function loadGroups() {
  loadingGroups.value = true
  try {
    groups.value = await getAdminMaterialGroups()
  } catch (error) {
    uiStore.showError('Chyba při načítání skupin materiálů')
    console.error(error)
  } finally {
    loadingGroups.value = false
  }
}

function openCreateNormModal() {
  editingNorm.value = null
  normForm.value = {
    w_nr: '',
    en_iso: '',
    csn: '',
    aisi: '',
    material_group_id: groups.value[0]?.id || 0,
    note: '',
    version: 0
  }
  showNormModal.value = true
}

function openEditNormModal(row: Record<string, unknown>) {
  const norm = row as unknown as MaterialNorm
  editingNorm.value = norm
  normForm.value = {
    w_nr: norm.w_nr || '',
    en_iso: norm.en_iso || '',
    csn: norm.csn || '',
    aisi: norm.aisi || '',
    material_group_id: norm.material_group_id,
    note: norm.note || '',
    version: norm.version
  }
  showNormModal.value = true
}

async function saveNorm() {
  savingNorm.value = true
  try {
    if (editingNorm.value) {
      // Update
      const updateData: MaterialNormUpdate = {
        w_nr: normForm.value.w_nr || null,
        en_iso: normForm.value.en_iso || null,
        csn: normForm.value.csn || null,
        aisi: normForm.value.aisi || null,
        material_group_id: normForm.value.material_group_id,
        note: normForm.value.note || null,
        version: normForm.value.version
      }
      await updateMaterialNorm(editingNorm.value.id, updateData)
      uiStore.showSuccess('Norma aktualizována')
    } else {
      // Create
      const createData: MaterialNormCreate = {
        w_nr: normForm.value.w_nr || null,
        en_iso: normForm.value.en_iso || null,
        csn: normForm.value.csn || null,
        aisi: normForm.value.aisi || null,
        material_group_id: normForm.value.material_group_id,
        note: normForm.value.note || null
      }
      await createMaterialNorm(createData)
      uiStore.showSuccess('Norma vytvořena')
    }
    showNormModal.value = false
    await loadNorms()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    savingNorm.value = false
  }
}

async function deleteNormItem(norm: MaterialNorm) {
  const normName = norm.w_nr || norm.en_iso || norm.csn || norm.aisi
  const confirmed = await confirm({
    title: 'Smazat normu?',
    message: `Opravdu chcete smazat normu ${normName}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await deleteMaterialNorm(norm.id)
    uiStore.showSuccess('Norma smazána')
    showNormModal.value = false
    await loadNorms()
  } catch (error) {
    uiStore.showError('Chyba při mazání normy')
    console.error(error)
  }
}

// Tab 1: Material Groups Methods
function openCreateGroupModal() {
  editingGroup.value = null
  groupForm.value = {
    code: '',
    name: '',
    density: 0,
    version: 0
  }
  showGroupModal.value = true
}

function openEditGroupModal(row: Record<string, unknown>) {
  const group = row as unknown as MaterialGroup
  editingGroup.value = group
  groupForm.value = {
    code: group.code,
    name: group.name,
    density: group.density,
    version: group.version
  }
  showGroupModal.value = true
}

async function saveGroup() {
  savingGroup.value = true
  try {
    if (editingGroup.value) {
      // Update
      const updateData: MaterialGroupUpdate = {
        code: groupForm.value.code,
        name: groupForm.value.name,
        density: groupForm.value.density,
        version: groupForm.value.version
      }
      await updateMaterialGroup(editingGroup.value.id, updateData)
      uiStore.showSuccess('Skupina aktualizována')
    } else {
      // Create
      const createData: MaterialGroupCreate = {
        code: groupForm.value.code,
        name: groupForm.value.name,
        density: groupForm.value.density
      }
      await createMaterialGroup(createData)
      uiStore.showSuccess('Skupina vytvořena')
    }
    showGroupModal.value = false
    await loadGroups()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    savingGroup.value = false
  }
}

async function deleteGroupItem(group: MaterialGroup) {
  const confirmed = await confirm({
    title: 'Smazat skupinu?',
    message: `Opravdu chcete smazat skupinu ${group.code} - ${group.name}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await deleteMaterialGroup(group.id)
    uiStore.showSuccess('Skupina smazána')
    showGroupModal.value = false
    await loadGroups()
  } catch (error) {
    uiStore.showError('Chyba při mazání skupiny')
    console.error(error)
  }
}

// Tab 2: Price Categories Methods
async function loadCategories() {
  loadingCategories.value = true
  try {
    categories.value = await getPriceCategories()
  } catch (error) {
    uiStore.showError('Chyba při načítání cenových kategorií')
    console.error(error)
  } finally {
    loadingCategories.value = false
  }
}

function openCreateCategoryModal() {
  editingCategory.value = null
  categoryForm.value = {
    code: '',
    name: '',
    material_group_id: null,
    version: 0
  }
  showCategoryModal.value = true
}

async function openEditCategoryModal(row: Record<string, unknown>) {
  const category = row as unknown as MaterialPriceCategory
  editingCategory.value = category
  selectedCategory.value = category
  categoryForm.value = {
    code: category.code,
    name: category.name,
    material_group_id: category.material_group_id,
    version: category.version
  }
  showCategoryModal.value = true

  // Load tiers for this category
  await loadTiers(category.id)
}

async function saveCategory() {
  savingCategory.value = true
  try {
    if (editingCategory.value) {
      // Update
      const updateData: MaterialPriceCategoryUpdate = {
        code: categoryForm.value.code,
        name: categoryForm.value.name,
        material_group_id: categoryForm.value.material_group_id,
        version: categoryForm.value.version
      }
      await updatePriceCategory(editingCategory.value.id, updateData)
      uiStore.showSuccess('Kategorie aktualizována')
    } else {
      // Create
      const createData: MaterialPriceCategoryCreate = {
        code: categoryForm.value.code,
        name: categoryForm.value.name,
        material_group_id: categoryForm.value.material_group_id
      }
      await createPriceCategory(createData)
      uiStore.showSuccess('Kategorie vytvořena')
    }
    showCategoryModal.value = false
    await loadCategories()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    savingCategory.value = false
  }
}

async function deleteCategoryItem(category: MaterialPriceCategory) {
  const confirmed = await confirm({
    title: 'Smazat kategorii?',
    message: `Opravdu chcete smazat kategorii ${category.code} - ${category.name}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await deletePriceCategory(category.id)
    uiStore.showSuccess('Kategorie smazána')
    showCategoryModal.value = false
    await loadCategories()
  } catch (error) {
    uiStore.showError('Chyba při mazání kategorie')
    console.error(error)
  }
}

// Price Tiers Methods
async function loadTiers(categoryId: number) {
  loadingTiers.value = true
  try {
    tiers.value = await getPriceTiers(categoryId)
  } catch (error) {
    uiStore.showError('Chyba při načítání cenových stupňů')
    console.error(error)
  } finally {
    loadingTiers.value = false
  }
}

function openCreateTierModal() {
  // Cancel any existing edit
  editingTier.value = null
  tierForm.value = {
    min_weight: 0,
    max_weight: null,
    price_per_kg: 0,
    version: 0
  }
  showTierModal.value = true
}

// Inline cell editing
function startEditCell(tier: MaterialPriceTier, field: 'min_weight' | 'max_weight' | 'price_per_kg') {
  editingCell.value = { tierId: tier.id, field }
  cellEditValue.value = tier[field]
}

function cancelCellEdit() {
  editingCell.value = null
  cellEditValue.value = null
}

async function saveCellEdit(tier: MaterialPriceTier) {
  if (!editingCell.value || !selectedCategory.value) return

  const field = editingCell.value.field as 'min_weight' | 'max_weight' | 'price_per_kg'
  const newValue = cellEditValue.value

  // Validation
  if (field !== 'max_weight' && (newValue === null || newValue < 0)) {
    uiStore.showError('Hodnota musí být kladné číslo')
    cancelCellEdit()
    return
  }

  try {
    const updateData: MaterialPriceTierUpdate = {
      min_weight: tier.min_weight,
      max_weight: tier.max_weight,
      price_per_kg: tier.price_per_kg,
      [field]: newValue,
      version: tier.version
    }

    await updatePriceTier(tier.id, updateData)
    uiStore.showSuccess('Hodnota aktualizována')
    cancelCellEdit()
    await loadTiers(selectedCategory.value.id)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
    cancelCellEdit()
  }
}

function cancelAddTier() {
  showTierModal.value = false
  tierForm.value = {
    min_weight: 0,
    max_weight: null,
    price_per_kg: 0,
    version: 0
  }
}

async function saveTier() {
  if (!selectedCategory.value) return

  savingTier.value = true
  try {
    if (editingTier.value) {
      // Update existing tier
      const updateData: MaterialPriceTierUpdate = {
        min_weight: tierForm.value.min_weight,
        max_weight: tierForm.value.max_weight,
        price_per_kg: tierForm.value.price_per_kg,
        version: tierForm.value.version
      }
      await updatePriceTier(editingTier.value.id, updateData)
      uiStore.showSuccess('Cenový stupeň aktualizován')
    } else {
      // Create new tier
      const createData: MaterialPriceTierCreate = {
        price_category_id: selectedCategory.value.id,
        min_weight: tierForm.value.min_weight,
        max_weight: tierForm.value.max_weight,
        price_per_kg: tierForm.value.price_per_kg
      }
      await createPriceTier(createData)
      uiStore.showSuccess('Cenový stupeň vytvořen')
    }

    // Reset state
    editingTier.value = null
    showTierModal.value = false
    tierForm.value = {
      min_weight: 0,
      max_weight: null,
      price_per_kg: 0,
      version: 0
    }

    // Reload tiers
    await loadTiers(selectedCategory.value.id)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    savingTier.value = false
  }
}

async function deleteTierItem(tier: MaterialPriceTier) {
  const confirmed = await confirm({
    title: 'Smazat cenový stupeň?',
    message: `Opravdu chcete smazat cenový stupeň ${tier.min_weight}-${tier.max_weight || '∞'} kg?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return
  if (!selectedCategory.value) return

  try {
    await deletePriceTier(tier.id)
    uiStore.showSuccess('Cenový stupeň smazán')
    await loadTiers(selectedCategory.value.id)
  } catch (error) {
    uiStore.showError('Chyba při mazání cenového stupně')
    console.error(error)
  }
}

// Tab 3: Work Centers Methods
async function loadWorkCenters() {
  loadingWorkCenters.value = true
  try {
    await operationsStore.loadWorkCenters()
  } finally {
    loadingWorkCenters.value = false
  }
}

function openCreateWorkCenterModal() {
  editingWorkCenter.value = null
  workCenterForm.value = {
    name: '',
    work_center_type: 'CNC_LATHE' as WorkCenterType,
    subtype: null,
    hourly_rate_amortization: null,
    hourly_rate_labor: null,
    hourly_rate_tools: null,
    hourly_rate_overhead: null,
    has_bar_feeder: false,
    has_sub_spindle: false,
    has_milling: false,
    suitable_for_series: true,
    suitable_for_single: true,
    setup_base_min: 0,
    setup_per_tool_min: 0,
    is_active: true,
    priority: 1,
    notes: null,
    version: 0
  }
  showWorkCenterModal.value = true
}

function openEditWorkCenterModal(row: Record<string, unknown>) {
  const wc = row as unknown as WorkCenter
  editingWorkCenter.value = wc
  workCenterForm.value = {
    name: wc.name,
    work_center_type: wc.work_center_type,
    subtype: wc.subtype ?? null,
    hourly_rate_amortization: wc.hourly_rate_amortization ?? null,
    hourly_rate_labor: wc.hourly_rate_labor ?? null,
    hourly_rate_tools: wc.hourly_rate_tools ?? null,
    hourly_rate_overhead: wc.hourly_rate_overhead ?? null,
    has_bar_feeder: wc.has_bar_feeder,
    has_sub_spindle: wc.has_sub_spindle,
    has_milling: wc.has_milling,
    suitable_for_series: wc.suitable_for_series,
    suitable_for_single: wc.suitable_for_single,
    setup_base_min: wc.setup_base_min,
    setup_per_tool_min: wc.setup_per_tool_min,
    is_active: wc.is_active,
    priority: wc.priority,
    notes: wc.notes ?? null,
    version: wc.version
  }
  showWorkCenterModal.value = true
}

async function saveWorkCenter() {
  savingWorkCenter.value = true
  try {
    if (editingWorkCenter.value) {
      // Update
      const updateData: WorkCenterUpdate = {
        name: workCenterForm.value.name,
        work_center_type: workCenterForm.value.work_center_type,
        subtype: workCenterForm.value.subtype,
        hourly_rate_amortization: workCenterForm.value.hourly_rate_amortization,
        hourly_rate_labor: workCenterForm.value.hourly_rate_labor,
        hourly_rate_tools: workCenterForm.value.hourly_rate_tools,
        hourly_rate_overhead: workCenterForm.value.hourly_rate_overhead,
        has_bar_feeder: workCenterForm.value.has_bar_feeder,
        has_sub_spindle: workCenterForm.value.has_sub_spindle,
        has_milling: workCenterForm.value.has_milling,
        suitable_for_series: workCenterForm.value.suitable_for_series,
        suitable_for_single: workCenterForm.value.suitable_for_single,
        setup_base_min: workCenterForm.value.setup_base_min,
        setup_per_tool_min: workCenterForm.value.setup_per_tool_min,
        is_active: workCenterForm.value.is_active,
        priority: workCenterForm.value.priority,
        notes: workCenterForm.value.notes,
        version: workCenterForm.value.version
      }
      await operationsStore.updateWorkCenter(editingWorkCenter.value.work_center_number, updateData)
      uiStore.showSuccess('Pracoviště aktualizováno')
    } else {
      // Create
      const createData: WorkCenterCreate = {
        name: workCenterForm.value.name,
        work_center_type: workCenterForm.value.work_center_type,
        subtype: workCenterForm.value.subtype,
        hourly_rate_amortization: workCenterForm.value.hourly_rate_amortization,
        hourly_rate_labor: workCenterForm.value.hourly_rate_labor,
        hourly_rate_tools: workCenterForm.value.hourly_rate_tools,
        hourly_rate_overhead: workCenterForm.value.hourly_rate_overhead,
        has_bar_feeder: workCenterForm.value.has_bar_feeder,
        has_sub_spindle: workCenterForm.value.has_sub_spindle,
        has_milling: workCenterForm.value.has_milling,
        suitable_for_series: workCenterForm.value.suitable_for_series,
        suitable_for_single: workCenterForm.value.suitable_for_single,
        setup_base_min: workCenterForm.value.setup_base_min,
        setup_per_tool_min: workCenterForm.value.setup_per_tool_min,
        is_active: workCenterForm.value.is_active,
        priority: workCenterForm.value.priority,
        notes: workCenterForm.value.notes
      }
      await operationsStore.createWorkCenter(createData)
      uiStore.showSuccess('Pracoviště vytvořeno')
    }
    showWorkCenterModal.value = false
    await loadWorkCenters()
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    savingWorkCenter.value = false
  }
}

async function deleteWorkCenterItem(wc: WorkCenter) {
  const confirmed = await confirm({
    title: 'Smazat pracoviště?',
    message: `Opravdu chcete smazat pracoviště ${wc.work_center_number} - ${wc.name}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await operationsStore.deleteWorkCenter(wc.work_center_number)
    uiStore.showSuccess('Pracoviště smazáno')
    showWorkCenterModal.value = false
    await loadWorkCenters()
  } catch (error) {
    uiStore.showError('Chyba při mazání pracoviště')
    console.error(error)
  }
}

onMounted(async () => {
  await loadGroups()
  await loadNorms()
  await loadCategories()
  await loadWorkCenters()
})
</script>

<template>
  <div class="master-data-view">
    <header class="page-header">
      <h1 class="page-title">Kmenová data</h1>
      <p class="page-subtitle">Správa materiálových norem, skupin a pracovišť</p>
    </header>

    <div class="page-content">
      <FormTabs v-model="activeTab" :tabs="tabs">
        <!-- Tab 0: Material Norms -->
        <template #tab-0>
          <div class="tab-content">
            <div class="tab-header">
              <h2>Normy materiálů</h2>
              <button class="btn btn-primary" @click="openCreateNormModal">
                + Přidat normu
              </button>
            </div>

            <DataTable
              :data="norms"
              :columns="normColumns"
              :loading="loadingNorms"
              :row-clickable="true"
              empty-text="Žádné normy materiálů"
              @row-click="openEditNormModal"
            />

            <!-- Create/Edit Modal -->
            <Modal v-model="showNormModal" :title="editingNorm ? 'Upravit normu' : 'Nová norma'">
              <form @submit.prevent="saveNorm">
                <div class="form-group">
                  <label>Skupina materiálu *</label>
                  <select v-model="normForm.material_group_id" required>
                    <option v-for="group in groups" :key="group.id" :value="group.id">
                      {{ group.code }} - {{ group.name }}
                    </option>
                  </select>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>W.Nr</label>
                    <input v-model="normForm.w_nr" type="text" maxlength="50" placeholder="1.0503" />
                  </div>
                  <div class="form-group">
                    <label>EN ISO</label>
                    <input v-model="normForm.en_iso" type="text" maxlength="50" placeholder="C45" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>ČSN</label>
                    <input v-model="normForm.csn" type="text" maxlength="50" placeholder="12050" />
                  </div>
                  <div class="form-group">
                    <label>AISI</label>
                    <input v-model="normForm.aisi" type="text" maxlength="50" placeholder="1045" />
                  </div>
                </div>

                <div class="form-group">
                  <label>Poznámka</label>
                  <textarea v-model="normForm.note" rows="3"></textarea>
                </div>

                <p class="form-hint">* Aspoň jedna norma (W.Nr, EN ISO, ČSN nebo AISI) musí být vyplněna</p>

                <div class="form-actions">
                  <button
                    v-if="editingNorm"
                    type="button"
                    class="btn btn-danger"
                    @click="deleteNormItem(editingNorm)"
                  >
                    Smazat
                  </button>
                  <div class="spacer"></div>
                  <button type="button" class="btn btn-secondary" @click="showNormModal = false">
                    Zrušit
                  </button>
                  <button type="submit" class="btn btn-primary" :disabled="savingNorm">
                    {{ savingNorm ? 'Ukládám...' : 'Uložit' }}
                  </button>
                </div>
              </form>
            </Modal>
          </div>
        </template>

        <!-- Tab 1: Material Groups -->
        <template #tab-1>
          <div class="tab-content">
            <div class="tab-header">
              <h2>Skupiny materiálů</h2>
              <button class="btn btn-primary" @click="openCreateGroupModal">
                + Přidat skupinu
              </button>
            </div>

            <DataTable
              :data="groups"
              :columns="groupColumns"
              :loading="loadingGroups"
              :row-clickable="true"
              empty-text="Žádné skupiny materiálů"
              @row-click="openEditGroupModal"
            />

            <!-- Create/Edit Modal -->
            <Modal v-model="showGroupModal" :title="editingGroup ? 'Upravit skupinu' : 'Nová skupina'">
              <form @submit.prevent="saveGroup">
                <div class="form-group">
                  <label>Kód *</label>
                  <input v-model="groupForm.code" type="text" maxlength="20" placeholder="STEEL" required />
                </div>

                <div class="form-group">
                  <label>Název *</label>
                  <input v-model="groupForm.name" type="text" maxlength="100" placeholder="Ocel" required />
                </div>

                <div class="form-group">
                  <label>Hustota (kg/dm³) *</label>
                  <input v-model.number="groupForm.density" type="number" step="0.001" min="0" placeholder="7.85" required />
                </div>

                <div class="form-actions">
                  <button
                    v-if="editingGroup"
                    type="button"
                    class="btn btn-danger"
                    @click="deleteGroupItem(editingGroup)"
                  >
                    Smazat
                  </button>
                  <div class="spacer"></div>
                  <button type="button" class="btn btn-secondary" @click="showGroupModal = false">
                    Zrušit
                  </button>
                  <button type="submit" class="btn btn-primary" :disabled="savingGroup">
                    {{ savingGroup ? 'Ukládám...' : 'Uložit' }}
                  </button>
                </div>
              </form>
            </Modal>
          </div>
        </template>

        <!-- Tab 2: Price Categories -->
        <template #tab-2>
          <div class="tab-content">
            <div class="tab-header">
              <h2>Cenové kategorie</h2>
              <button class="btn btn-primary" @click="openCreateCategoryModal">
                + Přidat kategorii
              </button>
            </div>

            <DataTable
              :data="categories"
              :columns="categoryColumns"
              :loading="loadingCategories"
              :row-clickable="true"
              empty-text="Žádné cenové kategorie"
              @row-click="openEditCategoryModal"
            />

            <!-- Combined Category Edit + Tiers Modal -->
            <Modal v-model="showCategoryModal" :title="editingCategory ? `Upravit kategorii - ${categoryForm.code}` : 'Nová kategorie'" size="lg">
              <div class="combined-category-modal">
                <!-- Category Edit Form -->
                <form @submit.prevent="saveCategory" class="category-form-section">
                  <h3 class="section-title">Základní informace</h3>

                  <div class="form-group">
                    <label>Kód *</label>
                    <input v-model="categoryForm.code" type="text" maxlength="20" placeholder="STEEL-STD" required />
                  </div>

                  <div class="form-group">
                    <label>Název *</label>
                    <input v-model="categoryForm.name" type="text" maxlength="100" placeholder="Ocel standardní" required />
                  </div>

                  <div class="form-group">
                    <label>Skupina materiálu</label>
                    <select v-model="categoryForm.material_group_id">
                      <option :value="null">-- Bez skupiny --</option>
                      <option v-for="group in groups" :key="group.id" :value="group.id">
                        {{ group.code }} - {{ group.name }}
                      </option>
                    </select>
                  </div>

                  <div class="form-actions">
                    <button
                      v-if="editingCategory"
                      type="button"
                      class="btn btn-danger"
                      @click="deleteCategoryItem(editingCategory)"
                    >
                      Smazat kategorii
                    </button>
                    <div class="spacer"></div>
                    <button type="button" class="btn btn-secondary" @click="showCategoryModal = false">
                      Zavřít
                    </button>
                    <button type="submit" class="btn btn-primary" :disabled="savingCategory">
                      {{ savingCategory ? 'Ukládám...' : 'Uložit' }}
                    </button>
                  </div>
                </form>

                <!-- Tiers Management (only for existing categories) -->
                <div v-if="editingCategory" class="tiers-management">
                <div class="tiers-header">
                  <h3>Cenové stupně podle hmotnosti</h3>
                  <button class="btn btn-primary btn-sm" @click="openCreateTierModal">
                    + Přidat stupeň
                  </button>
                </div>

                <!-- Tiers Table with Inline Editing -->
                <div class="tiers-table">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th style="width: 150px">Min. hmotnost (kg)</th>
                        <th style="width: 150px">Max. hmotnost (kg)</th>
                        <th style="width: 150px">Cena/kg (Kč)</th>
                        <th style="width: 100px">Akce</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="tier in tiers" :key="tier.id">
                        <!-- Min weight cell -->
                        <td @click="startEditCell(tier, 'min_weight')" class="editable-cell">
                          <input
                            v-if="editingCell?.tierId === tier.id && editingCell?.field === 'min_weight'"
                            v-model.number="cellEditValue"
                            type="number"
                            step="0.001"
                            min="0"
                            class="inline-input"
                            v-select-on-focus
                            @blur="saveCellEdit(tier)"
                            @keyup.enter="saveCellEdit(tier)"
                            @keyup.esc="cancelCellEdit"
                            ref="cellInput"
                            autofocus
                          />
                          <span v-else>{{ tier.min_weight }}</span>
                        </td>

                        <!-- Max weight cell -->
                        <td @click="startEditCell(tier, 'max_weight')" class="editable-cell">
                          <input
                            v-if="editingCell?.tierId === tier.id && editingCell?.field === 'max_weight'"
                            v-model.number="cellEditValue"
                            type="number"
                            step="0.001"
                            min="0"
                            class="inline-input"
                            placeholder="∞"
                            v-select-on-focus
                            @blur="saveCellEdit(tier)"
                            @keyup.enter="saveCellEdit(tier)"
                            @keyup.esc="cancelCellEdit"
                            ref="cellInput"
                            autofocus
                          />
                          <span v-else>{{ tier.max_weight ?? '∞' }}</span>
                        </td>

                        <!-- Price per kg cell -->
                        <td @click="startEditCell(tier, 'price_per_kg')" class="editable-cell">
                          <input
                            v-if="editingCell?.tierId === tier.id && editingCell?.field === 'price_per_kg'"
                            v-model.number="cellEditValue"
                            type="number"
                            step="0.01"
                            min="0"
                            class="inline-input"
                            v-select-on-focus
                            @blur="saveCellEdit(tier)"
                            @keyup.enter="saveCellEdit(tier)"
                            @keyup.esc="cancelCellEdit"
                            ref="cellInput"
                            autofocus
                          />
                          <span v-else>{{ tier.price_per_kg.toLocaleString('cs-CZ', { minimumFractionDigits: 2 }) }} Kč</span>
                        </td>

                        <!-- Actions -->
                        <td>
                          <button @click="deleteTierItem(tier)" class="btn-icon" title="Smazat">
                            <Trash2 :size="15" />
                          </button>
                        </td>
                      </tr>

                      <!-- Add new tier row -->
                      <tr v-if="showTierModal" class="new-row">
                        <td>
                          <input
                            v-model.number="tierForm.min_weight"
                            type="number"
                            step="0.001"
                            min="0"
                            class="inline-input"
                            placeholder="Min kg"
                            v-select-on-focus
                          />
                        </td>
                        <td>
                          <input
                            v-model.number="tierForm.max_weight"
                            type="number"
                            step="0.001"
                            min="0"
                            class="inline-input"
                            placeholder="Max kg (∞)"
                            v-select-on-focus
                          />
                        </td>
                        <td>
                          <input
                            v-model.number="tierForm.price_per_kg"
                            type="number"
                            step="0.01"
                            min="0"
                            class="inline-input"
                            placeholder="Kč/kg"
                            v-select-on-focus
                          />
                        </td>
                        <td>
                          <button @click="saveTier" class="btn-icon" title="Uložit" :disabled="savingTier">
                            <CheckCircle :size="15" />
                          </button>
                          <button @click="cancelAddTier" class="btn-icon" title="Zrušit">
                            <XCircle :size="15" />
                          </button>
                        </td>
                      </tr>

                      <!-- Empty state -->
                      <tr v-if="!loadingTiers && tiers.length === 0 && !showTierModal">
                        <td colspan="4" class="empty-cell">Žádné cenové stupně</td>
                      </tr>

                      <!-- Loading state -->
                      <tr v-if="loadingTiers">
                        <td colspan="4" class="empty-cell">Načítám...</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            </Modal>
          </div>
        </template>

        <!-- Tab 3: Work Centers -->
        <template #tab-3>
          <div class="tab-content">
            <div class="tab-header">
              <h2>Pracoviště</h2>
              <button class="btn btn-primary" @click="openCreateWorkCenterModal">
                + Přidat pracoviště
              </button>
            </div>

            <DataTable
              :data="workCenters"
              :columns="workCenterColumns"
              :loading="loadingWorkCenters"
              :row-clickable="true"
              empty-text="Žádná pracoviště"
              @row-click="openEditWorkCenterModal"
            />

            <!-- Create/Edit Modal -->
            <Modal v-model="showWorkCenterModal" :title="editingWorkCenter ? 'Upravit pracoviště' : 'Nové pracoviště'" size="lg">
              <form @submit.prevent="saveWorkCenter">
                <!-- Základní informace -->
                <div class="form-group">
                  <label>Název *</label>
                  <input v-model="workCenterForm.name" type="text" maxlength="200" placeholder="Soustruh CNC XY-500" required />
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>Typ pracoviště *</label>
                    <select v-model="workCenterForm.work_center_type" required>
                      <option value="CNC_LATHE">CNC Soustruh</option>
                      <option value="CNC_MILL_3AX">CNC Frézka 3-osá</option>
                      <option value="CNC_MILL_4AX">CNC Frézka 4-osá</option>
                      <option value="CNC_MILL_5AX">CNC Frézka 5-osá</option>
                      <option value="SAW">Pila</option>
                      <option value="DRILL">Vrtačka</option>
                      <option value="QUALITY_CONTROL">Kontrola kvality</option>
                      <option value="MANUAL_ASSEMBLY">Ruční montáž</option>
                      <option value="EXTERNAL">Externí</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label>Podtyp</label>
                    <input v-model="workCenterForm.subtype" type="text" maxlength="50" placeholder="DMG MORI NLX 2500" />
                  </div>
                </div>

                <!-- Hodinové sazby -->
                <h4 class="section-title">Hodinové sazby (Kč/hod)</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label>Odpisy</label>
                    <input v-model.number="workCenterForm.hourly_rate_amortization" type="number" step="0.01" min="0" placeholder="200" />
                  </div>
                  <div class="form-group">
                    <label>Mzdy</label>
                    <input v-model.number="workCenterForm.hourly_rate_labor" type="number" step="0.01" min="0" placeholder="300" />
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>Nástroje</label>
                    <input v-model.number="workCenterForm.hourly_rate_tools" type="number" step="0.01" min="0" placeholder="50" />
                  </div>
                  <div class="form-group">
                    <label>Režie</label>
                    <input v-model.number="workCenterForm.hourly_rate_overhead" type="number" step="0.01" min="0" placeholder="100" />
                  </div>
                </div>

                <!-- Setup times -->
                <h4 class="section-title">Seřizovací časy</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label>Základní seřízení (min) *</label>
                    <input v-model.number="workCenterForm.setup_base_min" type="number" step="1" min="0" placeholder="30" required />
                  </div>
                  <div class="form-group">
                    <label>Čas na nástroj (min) *</label>
                    <input v-model.number="workCenterForm.setup_per_tool_min" type="number" step="1" min="0" placeholder="5" required />
                  </div>
                </div>

                <!-- Capabilities -->
                <h4 class="section-title">Vybavení a možnosti</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.has_bar_feeder" type="checkbox" />
                      Podavač tyčí
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.has_sub_spindle" type="checkbox" />
                      Protivřeteno
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.has_milling" type="checkbox" />
                      Frézování
                    </label>
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.suitable_for_series" type="checkbox" />
                      Vhodné pro sérii
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.suitable_for_single" type="checkbox" />
                      Vhodné pro kusovku
                    </label>
                  </div>
                </div>

                <!-- Status -->
                <h4 class="section-title">Stav a priorita</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input v-model="workCenterForm.is_active" type="checkbox" />
                      Aktivní
                    </label>
                  </div>
                  <div class="form-group">
                    <label>Priorita *</label>
                    <input v-model.number="workCenterForm.priority" type="number" step="1" min="1" max="99" placeholder="1" required />
                  </div>
                </div>

                <!-- Notes -->
                <div class="form-group">
                  <label>Poznámky</label>
                  <textarea v-model="workCenterForm.notes" rows="3" placeholder="Další poznámky k pracovišti..."></textarea>
                </div>

                <div class="form-actions">
                  <button
                    v-if="editingWorkCenter"
                    type="button"
                    class="btn btn-danger"
                    @click="deleteWorkCenterItem(editingWorkCenter)"
                  >
                    Smazat
                  </button>
                  <div class="spacer"></div>
                  <button type="button" class="btn btn-secondary" @click="showWorkCenterModal = false">
                    Zrušit
                  </button>
                  <button type="submit" class="btn btn-primary" :disabled="savingWorkCenter">
                    {{ savingWorkCenter ? 'Ukládám...' : 'Uložit' }}
                  </button>
                </div>
              </form>
            </Modal>
          </div>
        </template>
      </FormTabs>
    </div>
  </div>
</template>

<style scoped>
.master-data-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.page-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.page-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  justify-content: center;
  padding: var(--space-4);
  background: var(--bg-default);
}

.page-content :deep(.form-tabs) {
  width: 1200px;
  min-width: 1200px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tab-content {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-2);
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  margin-bottom: var(--space-3);
}

.tab-header h2 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.form-group {
  margin-bottom: var(--space-3);
}

.form-group label {
  display: block;
  margin-bottom: var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  transition: all 0.15s ease;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
  background: var(--bg-surface);
  box-shadow: 0 0 0 3px var(--accent-primary-bg);
}

.form-hint {
  margin: var(--space-1) 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--text-lg);
  padding: var(--space-2);
  opacity: 0.6;
  transition: all 0.2s ease;
  border-radius: var(--radius-sm);
}

.btn-icon:hover {
  opacity: 1;
  background: var(--bg-hover);
  transform: scale(1.1);
}

.btn-icon:active {
  transform: scale(0.95);
}

.tiers-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border-default);
}

.tiers-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

/* Tiers inline editing table */
.tiers-table {
  width: 100%;
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background: var(--bg-default);
  border-bottom: 2px solid var(--border-default);
}

.data-table th {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.data-table td {
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--border-default);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.data-table tbody tr {
  transition: background 0.15s ease;
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.data-table tbody tr.new-row {
  background: var(--accent-primary-bg);
  border-left: 3px solid var(--accent-primary);
}

.editable-cell {
  cursor: text;
  position: relative;
  transition: all 0.15s ease;
  border-radius: var(--radius-sm);
}

.editable-cell:hover {
  background: var(--accent-primary-bg);
  box-shadow: 0 0 0 1px var(--accent-primary);
}

.editable-cell input {
  margin: -6px;
  width: calc(100% + 12px);
}

.inline-input {
  width: 100%;
  padding: var(--space-1) var(--space-2);
  border: 2px solid var(--accent-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-surface);
  color: var(--text-primary);
  box-shadow: 0 0 0 3px var(--accent-primary-bg);
}

.inline-input:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 4px var(--accent-primary-bg);
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  font-style: italic;
}

/* Combined category modal */
.combined-category-modal {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: var(--space-4);
  align-items: start;
}

.category-form-section {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.section-title {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border-default);
}

.tiers-management {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  height: 100%;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

h4.section-title {
  margin: var(--space-4) 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.spacer {
  flex: 1;
}
</style>
