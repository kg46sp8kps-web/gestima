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

// Default design token values (in pixels)
const defaultTokens = {
  // Font sizes
  'text-2xs': 9,
  'text-xs': 10,
  'text-sm': 11,
  'text-base': 12,
  'text-lg': 13,
  'text-xl': 14,
  'text-2xl': 16,
  'text-3xl': 18,
  'text-4xl': 20,
  'text-5xl': 24,
  'text-6xl': 32,
  'text-7xl': 48,
  'text-8xl': 64,
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
  'density-row-height': 24,
  'density-cell-py': 4,
  'density-cell-px': 8,
  'density-input-py': 3,
  'density-input-px': 6,
  'density-btn-py': 3,
  'density-btn-px': 8,
  'density-module-padding': 6,
  'density-section-gap': 6
}

// Token descriptions for UI
const tokenDescriptions: Record<string, string> = {
  'text-2xs': 'Nejmenší text (tiny labels)',
  'text-xs': 'Extra small (captions, badges)',
  'text-sm': 'Small (tlačítka, labely)',
  'text-base': 'Základní velikost textu',
  'text-lg': 'Large body text',
  'text-xl': 'Subheadings',
  'text-2xl': 'Headings',
  'text-3xl': 'Large headings',
  'text-4xl': 'Section titles',
  'text-5xl': 'Page headers',
  'text-6xl': 'Hero text',
  'text-7xl': 'Empty state icons',
  'text-8xl': 'Large display icons',
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
  // Font sizes and spacing in rem, density in px
  if (name.startsWith('text-')) {
    document.documentElement.style.setProperty(cssVar, `${value / 16}rem`)
  } else if (name.startsWith('space-')) {
    document.documentElement.style.setProperty(cssVar, `${value / 16}rem`)
  } else if (name === 'density-row-height') {
    document.documentElement.style.setProperty(cssVar, `${value}px`)
  } else {
    // Density padding values in rem
    document.documentElement.style.setProperty(cssVar, `${value / 16}rem`)
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
                      min="6"
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
  background: var(--bg-base);
  color: var(--text-body);
  overflow: hidden;
}

/* Ensure all form elements use design system colors */
.settings-view select,
.settings-view input,
.settings-view option {
  color: var(--text-body);
  background: var(--bg-input);
}

.settings-view select option {
  background: var(--bg-surface);
  color: var(--text-body);
}

.page-header {
  flex-shrink: 0;
  padding: var(--space-4) var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
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
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) var(--space-6);
}

.settings-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--space-4);
  max-width: 1400px;
  margin: 0 auto;
}

.settings-column {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-raised);
  cursor: pointer;
  user-select: none;
}

.card-header:hover {
  background: var(--state-hover);
}

.card-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.toggle-icon {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.card-body {
  padding: var(--space-4);
  color: var(--text-body);
}

.card-description {
  margin: 0 0 var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* Info rows (Account) */
.info-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-2);
}

.info-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.info-value {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

/* Form rows (Preferences) */
.form-row {
  margin-bottom: var(--space-3);
}

.form-label {
  display: block;
  margin-bottom: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.form-select {
  width: 100%;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-body);
}

.form-row.checkbox {
  margin-top: var(--space-4);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-body);
  cursor: pointer;
}

/* Token grid */
.token-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.token-row {
  display: grid;
  grid-template-columns: 1fr 90px 50px;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2);
  background: var(--bg-input);
  border-radius: var(--radius-md);
}

.token-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.token-name {
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  color: var(--color-info);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.token-desc {
  font-size: var(--text-2xs);
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.token-input-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.token-input {
  width: 60px;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  text-align: right;
  background: var(--bg-surface);
  color: var(--text-body);
}

.token-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
  color: var(--text-body);
}

.token-unit {
  font-size: var(--text-2xs);
  color: var(--text-tertiary);
  width: 20px;
}

.token-preview {
  font-weight: var(--font-medium);
  color: var(--text-primary);
  text-align: center;
}

.token-preview-spacing {
  display: flex;
  justify-content: center;
}

.spacing-box {
  background: var(--color-info);
  border-radius: 2px;
  min-width: 4px;
}

/* Global actions */
.global-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  max-width: 1400px;
  margin: var(--space-6) auto 0;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}

/* Button overrides - explicit colors for scoped CSS specificity */
.btn {
  color: var(--text-body);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-body);
  border-color: var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: var(--color-danger);
  color: white;
  border-color: var(--color-danger);
}

.btn-danger:hover {
  background: var(--color-danger-hover);
}
</style>
