<script setup lang="ts">
/**
 * Users Panel - CRUD for user management (admin only)
 */

import { ref, onMounted, computed } from 'vue'
import { confirm } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'
import Modal from '@/components/ui/Modal.vue'
import { UserRole } from '@/types/auth'
import type { User, UserCreateRequest, UserUpdateRequest } from '@/types/auth'
import * as usersApi from '@/api/users'
import { formatDate } from '@/utils/formatters'

const uiStore = useUiStore()
const authStore = useAuthStore()

// State
const users = ref<User[]>([])
const loadingUsers = ref(false)
const showUserModal = ref(false)
const showPasswordModal = ref(false)
const editingUser = ref<User | null>(null)
const savingUser = ref(false)
const savingPassword = ref(false)

const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: UserRole.OPERATOR as UserRole,
  is_active: true,
  version: 0
})

const passwordForm = ref({
  password: ''
})

const roleOptions = [
  { value: UserRole.ADMIN, label: 'Admin' },
  { value: UserRole.OPERATOR, label: 'Operátor' },
  { value: UserRole.VIEWER, label: 'Prohlížeč' }
]

const columns: Column[] = [
  { key: 'username', label: 'Uživatel', sortable: true, width: '180px' },
  { key: 'email', label: 'Email', sortable: true },
  { key: 'role', label: 'Role', sortable: true, width: '120px' },
  { key: 'is_active', label: 'Stav', sortable: true, width: '100px' },
  { key: 'created_at', label: 'Vytvořen', sortable: true, width: '140px', format: 'date' }
]

const isCurrentUser = computed(() => {
  if (!editingUser.value || !authStore.user) return false
  return editingUser.value.id === authStore.user.id
})

function roleLabel(role: string): string {
  switch (role) {
    case 'admin': return 'Admin'
    case 'operator': return 'Operátor'
    case 'viewer': return 'Prohlížeč'
    default: return role
  }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    users.value = await usersApi.getUsers()
  } catch {
    uiStore.showError('Chyba při načítání uživatelů')
  } finally {
    loadingUsers.value = false
  }
}

function openCreateModal() {
  editingUser.value = null
  userForm.value = {
    username: '',
    email: '',
    password: '',
    role: UserRole.OPERATOR,
    is_active: true,
    version: 0
  }
  showUserModal.value = true
}

function openEditModal(row: Record<string, unknown>) {
  const u = row as unknown as User
  editingUser.value = u
  userForm.value = {
    username: u.username,
    email: u.email ?? '',
    password: '',
    role: u.role,
    is_active: u.is_active,
    version: (u as User & { version?: number }).version ?? 0
  }
  showUserModal.value = true
}

async function saveUser() {
  savingUser.value = true
  try {
    if (editingUser.value) {
      const updateData: UserUpdateRequest = {
        email: userForm.value.email || null,
        role: userForm.value.role,
        is_active: userForm.value.is_active,
        version: userForm.value.version
      }
      await usersApi.updateUser(editingUser.value.id, updateData)
      uiStore.showSuccess('Uživatel aktualizován')
    } else {
      if (!userForm.value.password) {
        uiStore.showError('Heslo je povinné pro nového uživatele')
        savingUser.value = false
        return
      }
      const createData: UserCreateRequest = {
        username: userForm.value.username,
        password: userForm.value.password,
        email: userForm.value.email || null,
        role: userForm.value.role
      }
      await usersApi.createUser(createData)
      uiStore.showSuccess('Uživatel vytvořen')
    }
    showUserModal.value = false
    await loadUsers()
  } catch (error: unknown) {
    uiStore.showError(error instanceof Error ? error.message : 'Chyba při ukládání')
  } finally {
    savingUser.value = false
  }
}

function openPasswordModal() {
  if (!editingUser.value) return
  passwordForm.value = { password: '' }
  showPasswordModal.value = true
}

async function savePassword() {
  if (!editingUser.value) return
  if (!passwordForm.value.password || passwordForm.value.password.length < 8) {
    uiStore.showError('Heslo musí mít alespoň 8 znaků')
    return
  }
  savingPassword.value = true
  try {
    await usersApi.changeUserPassword(editingUser.value.id, {
      password: passwordForm.value.password
    })
    uiStore.showSuccess('Heslo změněno')
    showPasswordModal.value = false
  } catch (error: unknown) {
    uiStore.showError(error instanceof Error ? error.message : 'Chyba při změně hesla')
  } finally {
    savingPassword.value = false
  }
}

async function deleteUserItem(user: User) {
  if (authStore.user && user.id === authStore.user.id) {
    uiStore.showError('Nemůžete smazat vlastní účet')
    return
  }
  const confirmed = await confirm({
    title: 'Smazat uživatele?',
    message: `Opravdu chcete smazat uživatele "${user.username}"?`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })
  if (!confirmed) return
  try {
    await usersApi.deleteUser(user.id)
    uiStore.showSuccess('Uživatel smazán')
    showUserModal.value = false
    await loadUsers()
  } catch (error: unknown) {
    uiStore.showError(error instanceof Error ? error.message : 'Chyba při mazání uživatele')
  }
}

onMounted(() => { loadUsers() })
</script>

<template>
  <div class="admin-panel">
    <div class="panel-header">
      <h2>Správa uživatelů</h2>
      <button class="btn btn-primary" data-testid="create-user-button" @click="openCreateModal">
        + Přidat uživatele
      </button>
    </div>

    <DataTable
      :data="users"
      :columns="columns"
      :loading="loadingUsers"
      :row-clickable="true"
      empty-text="Žádní uživatelé"
      data-testid="users-table"
      @row-click="openEditModal"
    >
      <template #cell-role="{ row }">
        <span :class="['role-badge', `role-${row.role}`]">
          {{ roleLabel(row.role as string) }}
        </span>
      </template>
      <template #cell-is_active="{ row }">
        <span :class="['status-badge', row.is_active ? 'active' : 'inactive']">
          {{ row.is_active ? 'Aktivní' : 'Neaktivní' }}
        </span>
      </template>
      <template #cell-created_at="{ row }">
        {{ formatDate(row.created_at) }}
      </template>
    </DataTable>

    <!-- User Create/Edit Modal -->
    <Modal v-model="showUserModal" :title="editingUser ? 'Upravit uživatele' : 'Nový uživatel'" size="md">
      <form @submit.prevent="saveUser" data-testid="user-form" autocomplete="off">
        <div class="form-grid">
          <div class="field-wrapper">
            <label class="field-label">Uživatelské jméno</label>
            <input
              v-model="userForm.username"
              type="text"
              autocomplete="off"
              :disabled="!!editingUser"
              data-testid="user-username-input"
            />
          </div>
          <div class="field-wrapper">
            <label class="field-label">Email</label>
            <input
              v-model="userForm.email"
              type="email"
              autocomplete="off"
              data-testid="user-email-input"
            />
          </div>
          <div class="role-selector-field">
            <label class="role-selector-label">Role</label>
            <div class="role-selector" data-testid="user-role-select">
              <button
                v-for="opt in roleOptions"
                :key="opt.value"
                type="button"
                :class="['role-option', { active: userForm.role === opt.value }]"
                :disabled="isCurrentUser"
                @click="userForm.role = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>
          <div v-if="!editingUser" class="field-wrapper">
            <label class="field-label">Heslo</label>
            <input
              v-model="userForm.password"
              type="password"
              placeholder="Heslo"
              autocomplete="new-password"
              data-testid="user-password-input"
            />
          </div>
          <div v-if="editingUser" class="checkbox-row">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="userForm.is_active"
                :disabled="isCurrentUser"
                data-testid="user-active-checkbox"
              />
              <span>Aktivní účet</span>
            </label>
          </div>
        </div>

        <div class="form-actions">
          <button
            v-if="editingUser && !isCurrentUser"
            type="button"
            class="btn btn-danger"
            data-testid="delete-user-button"
            @click="deleteUserItem(editingUser!)"
          >
            Smazat
          </button>
          <button
            v-if="editingUser"
            type="button"
            class="btn btn-secondary"
            data-testid="change-password-button"
            @click="openPasswordModal"
          >
            Změnit heslo
          </button>
          <div class="spacer"></div>
          <button type="button" class="btn btn-secondary" @click="showUserModal = false">Zrušit</button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="savingUser"
            data-testid="save-user-button"
          >
            {{ savingUser ? 'Ukládám...' : 'Uložit' }}
          </button>
        </div>
      </form>
    </Modal>

    <!-- Password Change Modal -->
    <Modal v-model="showPasswordModal" title="Změna hesla" size="sm">
      <form @submit.prevent="savePassword" data-testid="password-form" autocomplete="off">
        <p class="password-info">
          Nové heslo pro uživatele <strong>{{ editingUser?.username }}</strong>
        </p>
        <div class="field-wrapper">
          <label class="field-label">Nové heslo</label>
          <input
            v-model="passwordForm.password"
            type="password"
            placeholder="Heslo"
            autocomplete="new-password"
            data-testid="new-password-input"
          />
        </div>
        <div class="form-actions">
          <div class="spacer"></div>
          <button type="button" class="btn btn-secondary" @click="showPasswordModal = false">Zrušit</button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="savingPassword"
            data-testid="save-password-button"
          >
            {{ savingPassword ? 'Ukládám...' : 'Změnit heslo' }}
          </button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<style scoped>
.admin-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--pad);
  background: var(--surface);
  border-radius: 8px;
  border: 1px solid var(--b2);
}

.panel-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.role-selector-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.role-selector-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.role-selector {
  display: flex;
  gap: 0;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  overflow: hidden;
}

.role-option {
  flex: 1;
  padding: 6px var(--pad);
  background: var(--ground);
  border: none;
  border-right: 1px solid var(--b2);
  color: var(--t3);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.role-option:last-child {
  border-right: none;
}

.role-option:hover:not(:disabled) {
  background: var(--b1);
  color: var(--t1);
}

.role-option.active {
  background: var(--red);
  color: var(--t1);
}

.role-option:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkbox-row {
  display: flex;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--t2);
  font-size: var(--fs);
}

.checkbox-label input[type="checkbox"] {
  accent-color: var(--red);
}

.role-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.role-badge.role-admin {
  background: color-mix(in srgb, var(--err) 15%, transparent);
  color: var(--err);
}

.role-badge.role-operator {
  background: color-mix(in srgb, var(--warn) 15%, transparent);
  color: var(--warn);
}

.role-badge.role-viewer {
  background: color-mix(in srgb, var(--t3) 15%, transparent);
  color: var(--t3);
}

.status-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
}

.status-badge.active {
  background: color-mix(in srgb, var(--ok) 15%, transparent);
  color: var(--ok);
}

.status-badge.inactive {
  background: color-mix(in srgb, var(--err) 15%, transparent);
  color: var(--err);
}

.password-info {
  margin: 0 0 12px;
  font-size: var(--fs);
  color: var(--t3);
}

.password-info strong {
  color: var(--t1);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--b2);
}

.spacer {
  flex: 1;
}
</style>
