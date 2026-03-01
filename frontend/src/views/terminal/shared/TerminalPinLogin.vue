<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const pin = ref('')
const error = ref(false)
const loading = ref(false)

const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'C']

function pressKey(key: string) {
  if (loading.value) return
  error.value = false

  if (key === 'C') {
    pin.value = ''
    return
  }
  if (key === '' || pin.value.length >= 4) return
  pin.value += key
}

// Auto-submit at 4 digits
watch(pin, (v) => {
  if (v.length === 4) submit()
})

async function submit() {
  if (pin.value.length < 4 || loading.value) return
  loading.value = true

  const ok = await auth.pinLogin(pin.value)
  if (ok) {
    const target = (route.query.redirect as string) || '/terminal'
    await router.push(target)
  } else {
    error.value = true
    pin.value = ''
    loading.value = false
  }
}
</script>

<template>
  <div class="pin-root">
    <div class="pin-card">
      <div class="pin-logo">
        <img src="/logo.png" alt="GESTIMA" />
      </div>
      <div class="pin-title">Dílna</div>

      <!-- PIN dots -->
      <div :class="['pin-dots', { shake: error }]">
        <span v-for="i in 4" :key="i" :class="['dot', { filled: pin.length >= i }]" />
      </div>

      <!-- Numpad -->
      <div class="numpad">
        <button
          v-for="key in digits"
          :key="key"
          :class="['nkey', { empty: key === '', clear: key === 'C' }]"
          :disabled="key === '' || loading"
          @click="pressKey(key)"
        >
          {{ key === 'C' ? '\u232B' : key }}
        </button>
      </div>

      <!-- Status -->
      <div v-if="loading" class="pin-status">Ověřuji...</div>
      <div v-else-if="error" class="pin-error">Neplatný PIN</div>

      <!-- Fallback link -->
      <router-link class="pin-fallback" :to="{ path: '/login', query: { redirect: '/terminal' } }">
        Přihlásit heslem
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.pin-root {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--base);
}

.pin-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 320px;
  padding: 24px;
}

.pin-logo {
  width: 56px;
  height: 56px;
}
.pin-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 50%;
  filter: drop-shadow(0 0 16px rgba(229, 57, 53, 0.35));
}

.pin-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--t1);
  letter-spacing: 0.04em;
}

/* PIN dots */
.pin-dots {
  display: flex;
  gap: 12px;
  padding: 12px 0;
}
.dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--b2);
  transition: background 150ms, border-color 150ms;
}
.dot.filled {
  background: var(--red);
  border-color: var(--red);
}

/* Shake animation */
.shake {
  animation: shake 400ms ease-in-out;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-8px); }
  40% { transform: translateX(8px); }
  60% { transform: translateX(-6px); }
  80% { transform: translateX(4px); }
}

/* Numpad */
.numpad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
  max-width: 280px;
}

.nkey {
  height: 64px;
  min-width: 80px;
  font-size: 24px;
  font-weight: 500;
  font-family: var(--font);
  color: var(--t1);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 100ms, border-color 100ms;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}
.nkey:active:not(:disabled) {
  background: var(--red-10);
  border-color: var(--red);
}
.nkey.empty {
  visibility: hidden;
}
.nkey.clear {
  font-size: 28px;
  color: var(--t3);
}
.nkey:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Status / error */
.pin-status {
  color: var(--t3);
  font-size: 14px;
}
.pin-error {
  color: var(--red, #e53935);
  font-size: 14px;
  font-weight: 500;
}

/* Fallback link */
.pin-fallback {
  color: var(--t4);
  font-size: 13px;
  text-decoration: none;
  margin-top: 8px;
}
.pin-fallback:hover {
  color: var(--t2);
}
</style>
