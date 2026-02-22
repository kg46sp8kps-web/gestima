<template>
  <div class="login-page">
    <!-- Background layers -->
    <div class="bg-grid" aria-hidden="true"></div>
    <div class="bg-vignette" aria-hidden="true"></div>
    <div class="bg-glow" aria-hidden="true"></div>
    <div class="scan-line" aria-hidden="true"></div>

    <main class="login-main">
      <!-- CNC precision mark -->
      <div class="precision-mark anim-enter anim-d1" aria-hidden="true"></div>

      <!-- Logo -->
      <h1 class="logo anim-enter anim-d2">
        <span class="logo-red">GESTI</span><span class="logo-white">MA</span>
      </h1>

      <!-- Accent line (draws itself on entrance) -->
      <div class="accent-line anim-line" aria-hidden="true"></div>

      <!-- Tagline -->
      <p class="tagline anim-enter anim-d3">Kalkulace CNC výroby</p>

      <!-- Login form -->
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-field anim-enter anim-d4">
          <input
            v-model="username"
            type="text"
            required
            autofocus
            placeholder="Uživatelské jméno"
            :disabled="loading"
            data-testid="username-input"
          />
        </div>

        <div class="form-field anim-enter anim-d5">
          <input
            v-model="password"
            type="password"
            required
            placeholder="Heslo"
            :disabled="loading"
            data-testid="password-input"
          />
        </div>

        <button
          type="submit"
          class="submit-btn anim-enter anim-d6"
          :disabled="loading"
          data-testid="login-button"
        >
          <template v-if="!loading">Přihlásit se</template>
          <template v-else>
            <span class="btn-spinner"></span>
            Ověřování…
          </template>
        </button>
      </form>

      <!-- Rotating quotes -->
      <div class="quote-area anim-enter anim-d7">
        <Transition name="quote" mode="out-in">
          <p :key="quoteIdx" class="quote-text">{{ quotes[quoteIdx] }}</p>
        </Transition>
      </div>

      <!-- Footer -->
      <footer class="login-footer anim-enter anim-d8">
        <span class="clock">{{ clock }}</span>
        <span class="sep" aria-hidden="true">·</span>
        <span>KOVO RYBKA s.r.o.</span>
        <span class="sep" aria-hidden="true">·</span>
        <span>© 2026</span>
        <span class="sep" aria-hidden="true">·</span>
        <span class="version">v2.0</span>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
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

// Rotating manufacturing quotes
const quotes = [
  'Přesnost není cíl — je to standard.',
  'Každý mikron má svůj význam.',
  'Od výkresu k výrobku. Bez kompromisů.',
  'Čas stroje je nejcennější materiál.',
  'Kvalita se neměří — kvalita se žije.',
  'Technologie ve službách přesnosti.',
]
const quoteIdx = ref(0)
let quoteTimer: ReturnType<typeof setInterval>

// Live clock
const clock = ref('')
let clockTimer: ReturnType<typeof setInterval>

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString('cs-CZ', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 10_000)
  quoteTimer = setInterval(() => {
    quoteIdx.value = (quoteIdx.value + 1) % quotes.length
  }, 5_000)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  clearInterval(quoteTimer)
})

// Login handler
async function handleLogin() {
  if (!username.value || !password.value) {
    return
  }

  loading.value = true

  try {
    await auth.login({
      username: username.value,
      password: password.value,
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
/* ═══════════════════════════════════════════
   LOGIN PAGE — Industrial Precision Theme
   CNC coordinate grid + brand glow + staggered entrance
   ═══════════════════════════════════════════ */

/* ── PAGE ── */
.login-page {
  min-height: 100vh;
  background: var(--base);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* ── BACKGROUND: CNC COORDINATE GRID ── */
.bg-grid {
  position: absolute;
  inset: -120px;
  background-image:
    linear-gradient(var(--b1) 1px, transparent 1px),
    linear-gradient(90deg, var(--b1) 1px, transparent 1px);
  background-size: 80px 80px;
  animation: gridShift 30s linear infinite;
  opacity: 0.5;
}

/* Vignette: fades grid at edges using bg-base overlay */
.bg-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, transparent 20%, var(--base) 72%);
  pointer-events: none;
}

/* ── BACKGROUND: AMBIENT BRAND GLOW ── */
.bg-glow {
  position: absolute;
  width: 600px;
  height: 420px;
  top: 38%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse at center, var(--red-10) 0%, transparent 70%);
  animation: glowBreath 6s ease-in-out infinite alternate;
  pointer-events: none;
}

/* ── SCAN LINE (one-time entrance laser effect) ── */
.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--red), transparent);
  animation: scanAcross 1.8s var(--ease) 0.15s both;
}

/* ── MAIN CONTENT STACK ── */
.login-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 340px;
  padding: 20px;
}

/* ── CNC PRECISION MARK (crosshair) ── */
.precision-mark {
  width: 48px;
  height: 48px;
  border: 1px solid var(--red);
  border-radius: 99px;
  position: relative;
  margin-bottom: 20px;
  opacity: 0.8;
}

.precision-mark::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 1px;
  background: var(--red);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.6;
}

.precision-mark::after {
  content: '';
  position: absolute;
  width: 1px;
  height: 22px;
  background: var(--red);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.6;
}

/* ── LOGO ── */
.logo {
  font-family: var(--mono);
  font-size: calc(16px * 2.8);
  font-weight: 700;
  letter-spacing: 0.12em;
  line-height: 1;
  margin: 0 0 12px 0;
  text-align: center;
  user-select: none;
}

.logo-red {
  color: var(--red);
}

.logo-white {
  color: var(--t1);
}

/* ── ACCENT LINE (draws itself) ── */
.accent-line {
  height: 1px;
  background: var(--red);
  margin-bottom: var(--pad);
  opacity: 0.5;
}

.anim-line {
  animation: lineExpand 0.8s 0.25s var(--ease) both;
}

/* ── TAGLINE ── */
.tagline {
  font-size: var(--fs);
  color: var(--t3);
  letter-spacing: 0.25em;
  text-transform: uppercase;
  margin: 0 0 40px 0;
  text-align: center;
}

/* ── FORM ── */
.login-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-field input {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  font-family: inherit;
  padding: var(--pad) 12px;
  outline: none;
  transition: all 150ms var(--ease);
}

.form-field input::placeholder {
  color: var(--t4);
  font-size: var(--fs);
}

.form-field input:hover:not(:focus):not(:disabled) {
  border-color: var(--b3);
}

.form-field input:focus {
  border-color: var(--red);
  background: var(--raised);
  box-shadow: 0 0 0 3px var(--red-10);
}

.form-field input:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── SUBMIT BUTTON (ghost + accent underline on hover) ── */
.submit-btn {
  width: 100%;
  margin-top: 6px;
  padding: var(--pad) 12px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  position: relative;
  overflow: hidden;
  transition: all 150ms var(--ease);
}

.submit-btn::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--red);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform 300ms var(--ease);
}

.submit-btn:hover:not(:disabled) {
  border-color: var(--red);
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
}

.submit-btn:hover:not(:disabled)::after {
  transform: scaleX(1);
}

.submit-btn:active:not(:disabled) {
  background: var(--red-20);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--b2);
  border-top-color: var(--red);
  border-radius: 99px;
  animation: spin 0.8s linear infinite;
}

/* ── QUOTE AREA ── */
.quote-area {
  margin-top: 40px;
  min-height: 24px;
  text-align: center;
  width: 100%;
}

.quote-text {
  font-size: var(--fs);
  color: var(--t3);
  font-style: italic;
  letter-spacing: 0.03em;
  margin: 0;
}

/* Quote transition (slide up/down fade) */
.quote-enter-active,
.quote-leave-active {
  transition: opacity 300ms var(--ease),
              transform 300ms var(--ease);
}

.quote-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.quote-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── FOOTER ── */
.login-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
  color: var(--t4);
  flex-wrap: wrap;
  justify-content: center;
}

.clock {
  font-family: var(--mono);
  color: var(--t3);
}

.version {
  font-family: var(--mono);
  opacity: 0.5;
}

.sep {
  opacity: 0.3;
}

/* ── ENTRANCE ANIMATIONS (staggered) ── */
.anim-enter {
  animation: fadeSlideUp 0.7s var(--ease) both;
}

.anim-d1 { animation-delay: 0.05s; }
.anim-d2 { animation-delay: 0.15s; }
.anim-d3 { animation-delay: 0.25s; }
.anim-d4 { animation-delay: 0.4s; }
.anim-d5 { animation-delay: 0.5s; }
.anim-d6 { animation-delay: 0.6s; }
.anim-d7 { animation-delay: 0.8s; }
.anim-d8 { animation-delay: 0.9s; }

/* ── KEYFRAMES ── */
@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes lineExpand {
  from {
    width: 0;
    opacity: 0;
  }
  to {
    width: 48px;
    opacity: 0.5;
  }
}

@keyframes gridShift {
  from { transform: translate(0, 0); }
  to { transform: translate(80px, 80px); }
}

@keyframes glowBreath {
  from {
    opacity: 0.3;
    transform: translate(-50%, -50%) scale(0.95);
  }
  to {
    opacity: 0.7;
    transform: translate(-50%, -50%) scale(1.08);
  }
}

@keyframes scanAcross {
  0% {
    transform: translateX(-100%);
    opacity: 0;
  }
  30% {
    opacity: 1;
  }
  100% {
    transform: translateX(100%);
    opacity: 0;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
