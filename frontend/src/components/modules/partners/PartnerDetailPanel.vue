<script setup lang="ts">
/**
 * Partner Detail Panel
 * Handles partner CRUD operations and displays partner details
 */
import { ref, computed, reactive, watch } from 'vue'
import { usePartnersStore } from '@/stores/partners'
import type { Partner, PartnerCreate, PartnerUpdate } from '@/types/partner'
import { Building2, Edit, Trash2, Save } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  partner: Partner | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'updated': []
  'deleted': []
}>()

const partnersStore = usePartnersStore()

// Local state
const activeTab = ref<'basic' | 'contact' | 'address' | 'notes'>('basic')
const isEditing = ref(false)
const showCreateForm = ref(false)
const showDeleteConfirm = ref(false)

const editForm = reactive<{
  company_name: string
  ico: string
  dic: string
  email: string
  phone: string
  contact_person: string
  street: string
  city: string
  postal_code: string
  country: string
  is_customer: boolean
  is_supplier: boolean
  notes: string
}>({
  company_name: '',
  ico: '',
  dic: '',
  email: '',
  phone: '',
  contact_person: '',
  street: '',
  city: '',
  postal_code: '',
  country: 'CZ',
  is_customer: false,
  is_supplier: false,
  notes: ''
})

const newPartner = reactive<PartnerCreate>({
  company_name: '',
  ico: '',
  dic: '',
  email: '',
  phone: '',
  contact_person: '',
  street: '',
  city: '',
  postal_code: '',
  country: 'CZ',
  is_customer: true,
  is_supplier: false,
  notes: ''
})

const saving = computed(() => partnersStore.loading)

// Initialize edit form when partner changes
watch(() => props.partner, (partner) => {
  if (partner) {
    editForm.company_name = partner.company_name
    editForm.ico = partner.ico || ''
    editForm.dic = partner.dic || ''
    editForm.email = partner.email || ''
    editForm.phone = partner.phone || ''
    editForm.contact_person = partner.contact_person || ''
    editForm.street = partner.street || ''
    editForm.city = partner.city || ''
    editForm.postal_code = partner.postal_code || ''
    editForm.country = partner.country
    editForm.is_customer = partner.is_customer
    editForm.is_supplier = partner.is_supplier
    editForm.notes = partner.notes || ''
    isEditing.value = false
  }
}, { immediate: true })

function startEdit() {
  isEditing.value = true
}

function cancelEdit() {
  if (props.partner) {
    editForm.company_name = props.partner.company_name
    editForm.ico = props.partner.ico || ''
    editForm.dic = props.partner.dic || ''
    editForm.email = props.partner.email || ''
    editForm.phone = props.partner.phone || ''
    editForm.contact_person = props.partner.contact_person || ''
    editForm.street = props.partner.street || ''
    editForm.city = props.partner.city || ''
    editForm.postal_code = props.partner.postal_code || ''
    editForm.country = props.partner.country
    editForm.is_customer = props.partner.is_customer
    editForm.is_supplier = props.partner.is_supplier
    editForm.notes = props.partner.notes || ''
  }
  isEditing.value = false
}

async function savePartner() {
  if (!props.partner) return

  const data: PartnerUpdate = {
    company_name: editForm.company_name,
    ico: editForm.ico || undefined,
    dic: editForm.dic || undefined,
    email: editForm.email || undefined,
    phone: editForm.phone || undefined,
    contact_person: editForm.contact_person || undefined,
    street: editForm.street || undefined,
    city: editForm.city || undefined,
    postal_code: editForm.postal_code || undefined,
    country: editForm.country,
    is_customer: editForm.is_customer,
    is_supplier: editForm.is_supplier,
    notes: editForm.notes || undefined,
    version: props.partner.version
  }

  try {
    await partnersStore.updatePartner(props.partner.partner_number, data)
    isEditing.value = false
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

function openCreateForm() {
  newPartner.company_name = ''
  newPartner.ico = ''
  newPartner.dic = ''
  newPartner.email = ''
  newPartner.phone = ''
  newPartner.contact_person = ''
  newPartner.street = ''
  newPartner.city = ''
  newPartner.postal_code = ''
  newPartner.country = 'CZ'
  newPartner.is_customer = true
  newPartner.is_supplier = false
  newPartner.notes = ''
  showCreateForm.value = true
}

async function createPartner() {
  try {
    await partnersStore.createPartner({
      company_name: newPartner.company_name,
      ico: newPartner.ico || undefined,
      dic: newPartner.dic || undefined,
      email: newPartner.email || undefined,
      phone: newPartner.phone || undefined,
      contact_person: newPartner.contact_person || undefined,
      street: newPartner.street || undefined,
      city: newPartner.city || undefined,
      postal_code: newPartner.postal_code || undefined,
      country: newPartner.country,
      is_customer: newPartner.is_customer,
      is_supplier: newPartner.is_supplier,
      notes: newPartner.notes || undefined
    })
    showCreateForm.value = false
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

function confirmDelete() {
  showDeleteConfirm.value = true
}

async function executeDelete() {
  if (!props.partner) return

  try {
    await partnersStore.deletePartner(props.partner.partner_number)
    showDeleteConfirm.value = false
    emit('deleted')
  } catch (error) {
    // Error handled in store
  }
}
</script>

<template>
  <div class="partner-detail-panel">
    <!-- Empty State -->
    <div v-if="!partner" class="empty">
      <Building2 :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Vyberte partnera pro zobrazení detailů</p>
      <button class="btn-primary" @click="openCreateForm">
        + Vytvořit nového partnera
      </button>
    </div>

    <!-- Partner Details -->
    <div v-else class="detail-content">
      <!-- Action Buttons -->
      <div class="panel-actions">
        <button
          v-if="!isEditing"
          class="btn-primary"
          @click="startEdit"
        >
          <Edit :size="ICON_SIZE.STANDARD" />
          Upravit
        </button>
        <template v-else>
          <button class="btn-secondary" @click="cancelEdit">
            Zrušit
          </button>
          <button class="btn-primary" @click="savePartner" :disabled="saving">
            <Save :size="ICON_SIZE.STANDARD" />
            {{ saving ? 'Ukládám...' : 'Uložit' }}
          </button>
        </template>
        <button
          v-if="!isEditing"
          class="btn-danger"
          @click="confirmDelete"
        >
          <Trash2 :size="ICON_SIZE.STANDARD" />
          Smazat
        </button>
      </div>

      <!-- Tabs -->
      <div class="detail-tabs">
        <button
          :class="{ active: activeTab === 'basic' }"
          @click="activeTab = 'basic'"
          class="tab-button"
        >
          Základní info
        </button>
        <button
          :class="{ active: activeTab === 'contact' }"
          @click="activeTab = 'contact'"
          class="tab-button"
        >
          Kontakt
        </button>
        <button
          :class="{ active: activeTab === 'address' }"
          @click="activeTab = 'address'"
          class="tab-button"
        >
          Adresa
        </button>
        <button
          :class="{ active: activeTab === 'notes' }"
          @click="activeTab = 'notes'"
          class="tab-button"
        >
          Poznámky
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Basic Info Tab -->
        <div v-if="activeTab === 'basic'" class="tab-panel">
          <form @submit.prevent="savePartner" class="detail-form">
            <div class="form-group">
              <label>Název firmy <span class="required">*</span></label>
              <input
                v-model="editForm.company_name"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                required
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>IČO</label>
                <input
                  v-model="editForm.ico"
                  type="text"
                  class="form-input"
                  :disabled="!isEditing"
                  maxlength="20"
                />
              </div>
              <div class="form-group">
                <label>DIČ</label>
                <input
                  v-model="editForm.dic"
                  type="text"
                  class="form-input"
                  :disabled="!isEditing"
                  maxlength="20"
                />
              </div>
            </div>

            <div class="form-group">
              <label>Typ partnera</label>
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input
                    v-model="editForm.is_customer"
                    type="checkbox"
                    :disabled="!isEditing"
                  />
                  <span>Zákazník</span>
                </label>
                <label class="checkbox-label">
                  <input
                    v-model="editForm.is_supplier"
                    type="checkbox"
                    :disabled="!isEditing"
                  />
                  <span>Dodavatel</span>
                </label>
              </div>
            </div>
          </form>
        </div>

        <!-- Contact Tab -->
        <div v-if="activeTab === 'contact'" class="tab-panel">
          <form @submit.prevent="savePartner" class="detail-form">
            <div class="form-group">
              <label>Kontaktní osoba</label>
              <input
                v-model="editForm.contact_person"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                maxlength="100"
              />
            </div>

            <div class="form-group">
              <label>Email</label>
              <input
                v-model="editForm.email"
                type="email"
                class="form-input"
                :disabled="!isEditing"
                maxlength="100"
              />
            </div>

            <div class="form-group">
              <label>Telefon</label>
              <input
                v-model="editForm.phone"
                type="tel"
                class="form-input"
                :disabled="!isEditing"
                maxlength="50"
              />
            </div>
          </form>
        </div>

        <!-- Address Tab -->
        <div v-if="activeTab === 'address'" class="tab-panel">
          <form @submit.prevent="savePartner" class="detail-form">
            <div class="form-group">
              <label>Ulice a číslo</label>
              <input
                v-model="editForm.street"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                maxlength="200"
              />
            </div>

            <div class="form-row">
              <div class="form-group city-field">
                <label>Město</label>
                <input
                  v-model="editForm.city"
                  type="text"
                  class="form-input"
                  :disabled="!isEditing"
                  maxlength="100"
                />
              </div>
              <div class="form-group postal-field">
                <label>PSČ</label>
                <input
                  v-model="editForm.postal_code"
                  type="text"
                  class="form-input"
                  :disabled="!isEditing"
                  maxlength="20"
                />
              </div>
            </div>

            <div class="form-group">
              <label>Země</label>
              <input
                v-model="editForm.country"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                maxlength="2"
              />
            </div>
          </form>
        </div>

        <!-- Notes Tab -->
        <div v-if="activeTab === 'notes'" class="tab-panel">
          <form @submit.prevent="savePartner" class="detail-form">
            <div class="form-group">
              <label>Poznámky</label>
              <textarea
                v-model="editForm.notes"
                class="form-textarea"
                :disabled="!isEditing"
                rows="10"
                maxlength="1000"
              ></textarea>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Create Partner Modal -->
    <Teleport to="body">
      <div v-if="showCreateForm" class="modal-overlay" @click.self="showCreateForm = false">
        <div class="modal-content modal-wide">
          <h3>Nový partner</h3>
          <form @submit.prevent="createPartner" class="create-form">
            <!-- Basic Info -->
            <div class="form-group">
              <label>Název firmy <span class="required">*</span></label>
              <input
                v-model="newPartner.company_name"
                type="text"
                class="form-input"
                required
                maxlength="200"
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>IČO</label>
                <input
                  v-model="newPartner.ico"
                  type="text"
                  class="form-input"
                  maxlength="20"
                />
              </div>
              <div class="form-group">
                <label>DIČ</label>
                <input
                  v-model="newPartner.dic"
                  type="text"
                  class="form-input"
                  maxlength="20"
                />
              </div>
            </div>

            <!-- Type -->
            <div class="form-group">
              <label>Typ partnera <span class="required">*</span></label>
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input v-model="newPartner.is_customer" type="checkbox" />
                  <span>Zákazník</span>
                </label>
                <label class="checkbox-label">
                  <input v-model="newPartner.is_supplier" type="checkbox" />
                  <span>Dodavatel</span>
                </label>
              </div>
            </div>

            <!-- Contact -->
            <div class="form-group">
              <label>Email</label>
              <input
                v-model="newPartner.email"
                type="email"
                class="form-input"
                maxlength="100"
              />
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showCreateForm = false">
                Zrušit
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="saving || !newPartner.company_name || (!newPartner.is_customer && !newPartner.is_supplier)"
              >
                {{ saving ? 'Vytvářím...' : 'Vytvořit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-content">
          <h3>Smazat partnera?</h3>
          <p>Opravdu chcete smazat partnera <strong>{{ partner?.company_name }}</strong>?</p>
          <div class="modal-actions">
            <button class="btn-secondary" @click="showDeleteConfirm = false">
              Zrušit
            </button>
            <button class="btn-danger" @click="executeDelete">
              Smazat
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.partner-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* Empty State */

.empty-icon {
  margin-bottom: 6px;
  opacity: 0.5;
  color: var(--t3);
}

.empty p {
  font-size: var(--fs);
}

/* Detail Content */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding-bottom: var(--pad);
  border-bottom: 1px solid var(--b2);
}

.detail-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--b2);
}

.tab-content {
  flex: 1;
  overflow-y: auto;
}

.tab-panel {
  padding: 12px 0;
}

/* Forms */
.detail-form,
.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  gap: var(--pad);
}

.city-field {
  flex: 2;
}

.postal-field {
  flex: 1;
}

.required {
  color: var(--err);
}

.checkbox-group {
  display: flex;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.checkbox-label input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

/* Buttons */

/* Modal */

.modal-wide {
  max-width: 600px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 12px;
}
</style>
