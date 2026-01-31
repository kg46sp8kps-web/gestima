<script setup lang="ts">
/**
 * Settings View
 * Uživatelská nastavení a preference
 */

import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useRouter } from 'vue-router'
import { useDarkMode } from '@/composables/useDarkMode'

const auth = useAuthStore()
const uiStore = useUiStore()
const router = useRouter()
const { setTheme } = useDarkMode()

const SETTINGS_KEY = 'gestima_settings'

// Form state
const form = ref({
  theme: 'dark' as 'light' | 'dark',
  language: 'cs',
  notifications: true
})

// Load settings from localStorage
function loadSettings() {
  const saved = localStorage.getItem(SETTINGS_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      form.value = { ...form.value, ...parsed }
      // Apply theme via composable
      setTheme(form.value.theme)
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }
}

async function handleSave() {
  try {
    // Save to localStorage
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(form.value))

    // Apply theme immediately
    setTheme(form.value.theme)

    uiStore.showSuccess('Nastavení uloženo')
  } catch (error) {
    uiStore.showError('Chyba při ukládání nastavení')
  }
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}

// Load on mount
onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="settings-view">
    <header class="page-header">
      <h1 class="page-title">Nastavení</h1>
      <p class="page-subtitle">Správa účtu a předvoleb</p>
    </header>

    <div class="page-content">
      <div class="settings-form">
        <!-- User info -->
        <div class="settings-card">
          <h2 class="card-title">Účet</h2>
          
          <div class="info-row">
            <span class="info-label">Uživatel:</span>
            <span class="info-value">{{ auth.user?.username }}</span>
          </div>

          <div class="info-row">
            <span class="info-label">Role:</span>
            <span class="info-value">{{ auth.user?.role }}</span>
          </div>

          <button class="btn btn-danger" @click="handleLogout">
            Odhlásit se
          </button>
        </div>

        <!-- Preferences -->
        <div class="settings-card">
          <h2 class="card-title">Předvolby</h2>

          <div class="form-group">
            <label>Motiv</label>
            <select v-model="form.theme">
              <option value="light">Světlý</option>
              <option value="dark">Tmavý</option>
            </select>
          </div>

          <div class="form-group">
            <label>Jazyk</label>
            <select v-model="form.language">
              <option value="cs">Čeština</option>
              <option value="en">English</option>
            </select>
          </div>

          <div class="form-group checkbox">
            <label>
              <input v-model="form.notifications" type="checkbox" />
              Povolit notifikace
            </label>
          </div>

          <button class="btn btn-primary" @click="handleSave">
            Uložit nastavení
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

.settings-form {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.card-title {
  margin: 0 0 var(--space-5);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-3);
}

.info-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.info-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.form-group select {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

</style>
