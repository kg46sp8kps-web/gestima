<script setup lang="ts">
/**
 * Settings View - Full Design Token Editor
 * Uživatelská nastavení včetně přesného nastavení všech font sizes, spacing a density
 */

import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useRouter } from 'vue-router'
import { useDarkMode } from '@/composables/useDarkMode'

const auth = useAuthStore()
const uiStore = useUiStore()
const router = useRouter()
const { setTheme } = useDarkMode()

const SETTINGS_KEY = 'gestima_settings'
const DESIGN_TOKENS_KEY = 'gestima_design_tokens'

// Expanded sections state
const expandedSections = reactive({
  account: true,
  preferences: true,
  typography: true,
  spacing: false,
  density: false
})

// Default design token values (in pixels) — must match design-system.css :root
// 3 font sizes + bold for hierarchy
const defaultTokens = {
  // Font sizes (3 sizes: sm=default, base=body, lg=headings)
  'text-sm': 12,
  'text-base': 12,
  'text-lg': 16,
  // Spacing
  'space-1': 4,
  'space-2': 6,
  'space-3': 8,
  'space-4': 12,
  'space-5': 16,
  'space-6': 20,
  'space-8': 24,
  'space-10': 32,
  // Density
  'density-row-height': 30,
  'density-cell-py': 3,
  'density-cell-px': 10,
  'density-input-py': 3,
  'density-input-px': 6,
  'density-btn-py': 3,
  'density-btn-px': 8,
  'density-module-padding': 6,
  'density-section-gap': 6
}

// Token descriptions for UI
const tokenDescriptions: Record<string, string> = {
  'text-sm': 'Malý text — tabulky, badges, labels (12px)',
  'text-base': 'Standardní — body, inputy, formuláře (14px)',
  'text-lg': 'Nadpisy — sekce, titulky, headery (18px)',
  'space-1': 'Tiny gaps',
  'space-2': 'Base unit',
  'space-3': 'Small padding',
  'space-4': 'Medium padding',
  'space-5': 'Standard padding',
  'space-6': 'Large padding',
  'space-8': 'Extra large',
  'space-10': 'Section gaps',
  'density-row-height': 'Výška řádku tabulky',
  'density-cell-py': 'Vertikální padding buňky',
  'density-cell-px': 'Horizontální padding buňky',
  'density-input-py': 'Vertikální padding inputu',
  'density-input-px': 'Horizontální padding inputu',
  'density-btn-py': 'Vertikální padding tlačítka',
  'density-btn-px': 'Horizontální padding tlačítka',
  'density-module-padding': 'Padding modulu/karty',
  'density-section-gap': 'Mezera mezi sekcemi'
}

// Current token values (reactive)
const tokens = reactive({ ...defaultTokens })

// Basic form state
const form = ref({
  theme: 'dark' as 'light' | 'dark',
  language: 'cs',
  notifications: true
})

// Apply single token to CSS
function applyToken(name: string, value: number) {
  const cssVar = `--${name}`
  if (name.startsWith('text-')) {
    // Font sizes in px (matching design-system.css)
    document.documentElement.style.setProperty(cssVar, `${value}px`)
  } else if (name.startsWith('space-')) {
    // Spacing in rem (matching design-system.css)
    document.documentElement.style.setProperty(cssVar, `${value / 16}rem`)
  } else {
    // Density values in px
    document.documentElement.style.setProperty(cssVar, `${value}px`)
  }
}

// Apply all tokens to CSS
function applyAllTokens() {
  Object.entries(tokens).forEach(([name, value]) => {
    applyToken(name, value)
  })
}

// Reset tokens to defaults
function resetTokens(category?: 'typography' | 'spacing' | 'density') {
  if (!category) {
    Object.assign(tokens, defaultTokens)
  } else if (category === 'typography') {
    Object.keys(defaultTokens)
      .filter(k => k.startsWith('text-'))
      .forEach(k => tokens[k as keyof typeof tokens] = defaultTokens[k as keyof typeof defaultTokens])
  } else if (category === 'spacing') {
    Object.keys(defaultTokens)
      .filter(k => k.startsWith('space-'))
      .forEach(k => tokens[k as keyof typeof tokens] = defaultTokens[k as keyof typeof defaultTokens])
  } else if (category === 'density') {
    Object.keys(defaultTokens)
      .filter(k => k.startsWith('density-'))
      .forEach(k => tokens[k as keyof typeof tokens] = defaultTokens[k as keyof typeof defaultTokens])
  }
  applyAllTokens()
  saveTokens()
  uiStore.showSuccess(`Tokeny ${category || 'všechny'} resetovány na výchozí hodnoty`)
}

// Load tokens from localStorage
function loadTokens() {
  const saved = localStorage.getItem(DESIGN_TOKENS_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(tokens, parsed)
    } catch (e) {
      console.error('Failed to load design tokens:', e)
    }
  }
  applyAllTokens()
}

// Save tokens to localStorage
function saveTokens() {
  localStorage.setItem(DESIGN_TOKENS_KEY, JSON.stringify(tokens))
}

// Watch for token changes and apply immediately (live preview)
watch(tokens, () => {
  applyAllTokens()
}, { deep: true })

// Load settings from localStorage
function loadSettings() {
  const saved = localStorage.getItem(SETTINGS_KEY)
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      form.value = { ...form.value, ...parsed }
      setTheme(form.value.theme)
    } catch (e) {
      console.error('Failed to load settings:', e)
    }
  }
}

async function handleSaveAll() {
  try {
    // Save basic settings
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(form.value))
    setTheme(form.value.theme)

    // Save design tokens
    saveTokens()

    uiStore.showSuccess('Všechna nastavení uložena')
  } catch (error) {
    uiStore.showError('Chyba při ukládání nastavení')
  }
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}

function toggleSection(section: keyof typeof expandedSections) {
  expandedSections[section] = !expandedSections[section]
}

// Load on mount
onMounted(() => {
  loadSettings()
  loadTokens()
})

// Grouped tokens for UI
const fontTokens = Object.keys(defaultTokens).filter(k => k.startsWith('text-'))
const spacingTokens = Object.keys(defaultTokens).filter(k => k.startsWith('space-'))
const densityTokens = Object.keys(defaultTokens).filter(k => k.startsWith('density-'))
</script>

<template>
  <div class="settings-view">
    <header class="page-header">
      <div class="header-content">
        <div>
          <h1 class="page-title">Nastavení</h1>
          <p class="page-subtitle">Správa účtu, předvoleb a design tokenů</p>
        </div>
        <button class="btn btn-primary" @click="handleSaveAll">
          Uložit vše
        </button>
      </div>
    </header>

    <div class="page-content">
      <div class="settings-grid">
        <!-- Left column: Account & Preferences -->
        <div class="settings-column">
          <!-- Account -->
          <div class="settings-card">
            <div class="card-header" @click="toggleSection('account')">
              <h2 class="card-title">Účet</h2>
              <span class="toggle-icon">{{ expandedSections.account ? '▼' : '▶' }}</span>
            </div>

            <div v-show="expandedSections.account" class="card-body">
              <div class="info-row">
                <span class="info-label">Uživatel:</span>
                <span class="info-value">{{ auth.user?.username }}</span>
              </div>

              <div class="info-row">
                <span class="info-label">Role:</span>
                <span class="info-value">{{ auth.user?.role }}</span>
              </div>

              <button class="btn btn-danger btn-sm" @click="handleLogout">
                Odhlásit se
              </button>
            </div>
          </div>

          <!-- Preferences -->
          <div class="settings-card">
            <div class="card-header" @click="toggleSection('preferences')">
              <h2 class="card-title">Předvolby</h2>
              <span class="toggle-icon">{{ expandedSections.preferences ? '▼' : '▶' }}</span>
            </div>

            <div v-show="expandedSections.preferences" class="card-body">
              <div class="form-row">
                <label class="form-label">Motiv</label>
                <select v-model="form.theme" class="form-select">
                  <option value="light">Světlý</option>
                  <option value="dark">Tmavý</option>
                </select>
              </div>

              <div class="form-row">
                <label class="form-label">Jazyk</label>
                <select v-model="form.language" class="form-select">
                  <option value="cs">Čeština</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div class="form-row checkbox">
                <label class="checkbox-label">
                  <input v-model="form.notifications" type="checkbox" />
                  Povolit notifikace
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: Design Tokens -->
        <div class="settings-column">
          <!-- Typography -->
          <div class="settings-card">
            <div class="card-header" @click="toggleSection('typography')">
              <h2 class="card-title">Typografie</h2>
              <span class="toggle-icon">{{ expandedSections.typography ? '▼' : '▶' }}</span>
            </div>

            <div v-show="expandedSections.typography" class="card-body">
              <p class="card-description">Velikosti písma v pixelech. Změny se aplikují okamžitě.</p>

              <div class="token-grid">
                <div v-for="token in fontTokens" :key="token" class="token-row">
                  <div class="token-info">
                    <code class="token-name">--{{ token }}</code>
                    <span class="token-desc">{{ tokenDescriptions[token] }}</span>
                  </div>
                  <div class="token-input-group">
                    <input
                      v-model.number="tokens[token as keyof typeof tokens]"
                      type="number"
                      min="10"
                      max="100"
                      class="token-input"
                      v-select-on-focus
                    />
                    <span class="token-unit">px</span>
                  </div>
                  <div
                    class="token-preview"
                    :style="{ fontSize: tokens[token as keyof typeof tokens] + 'px' }"
                  >
                    Abc
                  </div>
                </div>
              </div>

              <button class="btn btn-secondary btn-sm" @click="resetTokens('typography')">
                Reset typografie
              </button>
            </div>
          </div>

          <!-- Spacing -->
          <div class="settings-card">
            <div class="card-header" @click="toggleSection('spacing')">
              <h2 class="card-title">Spacing</h2>
              <span class="toggle-icon">{{ expandedSections.spacing ? '▼' : '▶' }}</span>
            </div>

            <div v-show="expandedSections.spacing" class="card-body">
              <p class="card-description">Mezery a paddingy v pixelech.</p>

              <div class="token-grid">
                <div v-for="token in spacingTokens" :key="token" class="token-row">
                  <div class="token-info">
                    <code class="token-name">--{{ token }}</code>
                    <span class="token-desc">{{ tokenDescriptions[token] }}</span>
                  </div>
                  <div class="token-input-group">
                    <input
                      v-model.number="tokens[token as keyof typeof tokens]"
                      type="number"
                      min="0"
                      max="64"
                      class="token-input"
                      v-select-on-focus
                    />
                    <span class="token-unit">px</span>
                  </div>
                  <div class="token-preview-spacing">
                    <div
                      class="spacing-box"
                      :style="{ width: tokens[token as keyof typeof tokens] + 'px', height: '16px' }"
                    ></div>
                  </div>
                </div>
              </div>

              <button class="btn btn-secondary btn-sm" @click="resetTokens('spacing')">
                Reset spacing
              </button>
            </div>
          </div>

          <!-- Density -->
          <div class="settings-card">
            <div class="card-header" @click="toggleSection('density')">
              <h2 class="card-title">Density</h2>
              <span class="toggle-icon">{{ expandedSections.density ? '▼' : '▶' }}</span>
            </div>

            <div v-show="expandedSections.density" class="card-body">
              <p class="card-description">Hustota komponent - výšky řádků, paddingy.</p>

              <div class="token-grid">
                <div v-for="token in densityTokens" :key="token" class="token-row">
                  <div class="token-info">
                    <code class="token-name">--{{ token }}</code>
                    <span class="token-desc">{{ tokenDescriptions[token] }}</span>
                  </div>
                  <div class="token-input-group">
                    <input
                      v-model.number="tokens[token as keyof typeof tokens]"
                      type="number"
                      min="0"
                      max="64"
                      class="token-input"
                      v-select-on-focus
                    />
                    <span class="token-unit">px</span>
                  </div>
                </div>
              </div>

              <button class="btn btn-secondary btn-sm" @click="resetTokens('density')">
                Reset density
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Global actions -->
      <div class="global-actions">
        <button class="btn btn-secondary" @click="resetTokens()">
          Reset vše na výchozí
        </button>
        <button class="btn btn-primary" @click="handleSaveAll">
          Uložit všechna nastavení
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px); /* Navbar height */
  background: var(--base);
  color: var(--t2);
  overflow: hidden;
}

/* Ensure all form elements use design system colors */
.settings-view select,
.settings-view input,
.settings-view option {
  color: var(--t2);
  background: var(--ground);
}

.settings-view select option {
  background: var(--surface);
  color: var(--t2);
}

.page-header {
  flex-shrink: 0;
  padding: 12px 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--t1);
}

.page-subtitle {
  margin: 4px 0 0;
  font-size: var(--fs);
  color: var(--t3);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
}

.settings-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 12px;
  max-width: 1400px;
  margin: 0 auto;
}

.settings-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-card {
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--pad) 12px;
  background: var(--raised);
  cursor: pointer;
  user-select: none;
}

.card-header:hover {
  background: var(--b1);
}

.card-title {
  margin: 0;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.toggle-icon {
  font-size: var(--fs);
  color: var(--t3);
}

.card-body {
  padding: 12px;
  color: var(--t2);
}

.card-description {
  margin: 0 0 12px;
  font-size: var(--fs);
  color: var(--t3);
}

/* Info rows (Account) */
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--b1);
  margin-bottom: 6px;
}

.info-label {
  font-size: var(--fs);
  color: var(--t3);
}

.info-value {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
}

/* Form rows (Preferences) */
.form-row {
  margin-bottom: var(--pad);
}

.form-label {
  display: block;
  margin-bottom: 4px;
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
}

.form-select {
  width: 100%;
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  font-size: var(--fs);
  background: var(--ground);
  color: var(--t2);
}

.form-row.checkbox {
  margin-top: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  color: var(--t2);
  cursor: pointer;
}

/* Token grid */
.token-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.token-row {
  display: grid;
  grid-template-columns: 1fr 90px 50px;
  gap: var(--pad);
  align-items: center;
  padding: 6px;
  background: var(--ground);
  border-radius: var(--r);
}

.token-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.token-name {
  font-family: var(--mono);
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.token-desc {
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.token-input-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.token-input {
  width: 60px;
  padding: 4px 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-family: var(--mono);
  text-align: right;
  background: var(--surface);
  color: var(--t2);
}

.token-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
  color: var(--t2);
}

.token-unit {
  font-size: var(--fs);
  color: var(--t3);
  width: 20px;
}

.token-preview {
  font-weight: 500;
  color: var(--t1);
  text-align: center;
}

.token-preview-spacing {
  display: flex;
  justify-content: center;
}

.spacing-box {
  background: var(--t3);
  border-radius: var(--rs);
  min-width: 4px;
}

/* Global actions */
.global-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--pad);
  max-width: 1400px;
  margin: 20px auto 0;
  padding-top: 12px;
  border-top: 1px solid var(--b2);
}

</style>
