<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Header with Logo -->
      <div class="login-header">
        <div class="logo-title">
          <div class="logo-text">
            <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
          </div>
        </div>
      </div>

      <!-- Login Card (Ribbon style) -->
      <div class="ribbon">
        <div class="ribbon-header">
          <div class="ribbon-title">Přihlášení</div>
        </div>
        <div class="ribbon-body">
          <!-- Split Layout -->
          <div class="split-layout">
            <!-- Left Panel: Placeholder for Facts/Weather (future) -->
            <div class="left-panel">
              <div class="info-section">
                <div class="info-label">GESTIMA Vue SPA</div>
                <div class="info-content">
                  <div class="info-item">
                    <div class="info-title">Phase 1: Foundation</div>
                    <div class="info-text">Core Infrastructure + Authentication</div>
                  </div>
                  <div class="info-item">
                    <div class="info-title">Vue 3 + TypeScript</div>
                    <div class="info-text">Pinia stores, Vue Router, Axios client</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Right Panel: Login Form -->
            <div class="right-panel">
              <div class="form-wrapper">
                <form @submit.prevent="handleLogin">
                  <!-- Username -->
                  <div class="form-field">
                    <input
                      v-model="username"
                      type="text"
                      required
                      autofocus
                      placeholder="Uživatelské jméno"
                      class="input"
                      :disabled="loading"
                      data-testid="username-input"
                    />
                  </div>

                  <!-- Password -->
                  <div class="form-field">
                    <input
                      v-model="password"
                      type="password"
                      required
                      placeholder="Heslo"
                      class="input"
                      :disabled="loading"
                      data-testid="password-input"
                    />
                  </div>

                  <!-- Submit Button -->
                  <button
                    type="submit"
                    class="btn-submit"
                    :disabled="loading"
                    data-testid="login-button"
                  >
                    <span v-if="!loading">Přihlásit se</span>
                    <span v-else>Přihlašování...</span>
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="login-footer">
        <div class="footer-quote">
          Be lazy. It's way better than talking to people.
        </div>
        <div class="footer-copyright">
          <span>KOVO RYBKA s.r.o.</span>
          <span class="footer-separator">•</span>
          <span>© 2026</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePrefetch } from '@/composables/usePrefetch'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const { prefetchAll } = usePrefetch()

// Form state
const username = ref('')
const password = ref('')
const loading = ref(false)

// Login handler
async function handleLogin() {
  if (!username.value || !password.value) {
    return
  }

  loading.value = true

  try {
    await auth.login({
      username: username.value,
      password: password.value
    })

    // Background prefetch — fire-and-forget, don't block redirect
    void prefetchAll()

    // Redirect to original destination or dashboard
    const redirect = (route.query.redirect as string) || '/'

    await router.push(redirect)

    ui.showSuccess('Přihlášení úspěšné')
  } catch (err: unknown) {
    ui.showError((err as Error).message || 'Neplatné přihlašovací údaje')
    loading.value = false
  }
}
</script>

<style scoped>
/* GESTIMA CSS is imported globally in main.ts */

.login-page {
  min-height: 100vh;
  min-width: 0;
  background: var(--bg-primary);
  padding: var(--space-6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-container {
  width: 100%;
  max-width: 700px;
}

/* Header */
.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.logo-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.logo-text {
  font-size: var(--text-6xl);
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: var(--brand);
}

.logo-black {
  color: var(--text-primary);
}

/* Ribbon */
.ribbon {
  margin-bottom: 1.5rem;
}

.ribbon-header {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-bottom: none;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  padding: var(--space-2) var(--space-3);
  cursor: default;
}

.ribbon-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.3px;
}

.ribbon-body {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  padding: 0;
}

/* Split Layout */
.split-layout {
  display: flex;
  min-height: 280px;
}

.left-panel {
  width: 420px;
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
}

.info-section {
  flex: 1;
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
}

.info-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-item {
  padding: var(--space-2);
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
}

.info-title {
  font-size: var(--text-base);
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: var(--space-1);
}

.info-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.3;
}

.right-panel {
  flex: 1;
  padding: var(--space-5);
  display: flex;
  align-items: center;
}

.form-wrapper {
  width: 100%;
  max-width: 280px;
  margin: 0 auto;
}

/* Form */
.form-field {
  margin-bottom: var(--space-4);
}

.input {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-lg);
  padding: var(--space-2) var(--space-2);
  width: 100%;
  transition: border-color 0.2s;
}

.input:focus {
  outline: none;
  border-color: var(--brand);
}

.input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-submit {
  width: 100%;
  justify-content: center;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-lg);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  border-radius: var(--radius-md);
  font-weight: 500;
  margin-top: var(--space-5);
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background: var(--brand-subtle);
  border-color: var(--brand);
  color: var(--brand-text);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Footer */
.login-footer {
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.footer-quote {
  margin-bottom: var(--space-2);
  font-style: italic;
  opacity: 0.8;
}

.footer-copyright {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.footer-separator {
  margin: 0 0.5rem;
}
</style>
