<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePrefetch } from '@/composables/usePrefetch'

const auth = useAuthStore()
const router = useRouter()
const { prefetchAll } = usePrefetch()

const username = ref('')
const password = ref('')
const booting = ref(false)

async function submit() {
  if (!username.value || !password.value) return

  // Form zmizí okamžitě — progress bar pokryje vše
  booting.value = true

  const ok = await auth.login(username.value, password.value)
  if (!ok) {
    // Chyba přihlášení — form se vrátí zpět
    booting.value = false
    return
  }

  await Promise.all([
    prefetchAll(),
    new Promise(r => setTimeout(r, 1400)),
  ])
  await router.push('/')
}
</script>

<template>
  <div class="lr">
    <div class="bg-grid" />
    <div class="bg-vig" />
    <div class="bg-glow" />
    <div :class="['laser', { replay: booting }]" />

    <!-- Jediný centrovaný blok — logo zůstane vždy na místě -->
    <div class="lc">

      <!-- Logo sekce — statická, nikdy se nehýbe -->
      <div class="lmark">
        <img src="/logo.png" alt="Logo" />
      </div>
      <div class="llogo"><em>GESTI</em><span>MA</span></div>
      <div class="lsub">Kalkulace CNC výroby</div>

      <!-- Swap zóna — form nebo progress bar -->
      <div class="lswap">
        <Transition name="swap">
          <form v-if="!booting" key="form" class="lform" @submit.prevent="submit">
            <input
              v-model="username"
              type="text"
              class="linput"
              placeholder="Uživatelské jméno"
              autocomplete="username"
              data-testid="login-username"
              required
              :disabled="auth.loading"
            />
            <input
              v-model="password"
              type="password"
              class="linput"
              placeholder="Heslo"
              autocomplete="current-password"
              data-testid="login-password"
              required
              :disabled="auth.loading"
            />
            <button
              type="submit"
              class="lbtn"
              :disabled="!username || !password"
              data-testid="login-submit"
            >
              Přihlásit se
            </button>
          </form>

          <div v-else key="prog" class="lprog">
            <div class="lpbar" />
          </div>
        </Transition>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* ── ROOT ── */
.lr {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--base); overflow: hidden;
}

/* ── BACKGROUND ── */
.bg-grid {
  position: absolute; inset: -200px;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: drift 30s linear infinite, fadeIn 1s 0.1s var(--ease) forwards;
  opacity: 0;
}
.bg-vig {
  position: absolute; inset: 0;
  background: radial-gradient(circle, transparent 20%, var(--base) 70%);
}
.bg-glow {
  position: absolute; width: 500px; height: 350px;
  top: 40%; left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse, var(--red-dim) 0%, transparent 70%);
  opacity: 0;
  animation: breatheSlow 4s cubic-bezier(0.45,0,0.55,1) infinite alternate,
             fadeIn 1.2s 0.2s var(--ease) forwards;
}

/* ── LASER ── */
.laser {
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 20%, var(--red) 50%, transparent 80%);
  box-shadow: 0 0 20px var(--red), 0 0 60px var(--red-glow);
  animation: laserSweep 1.2s 0.15s var(--ease) both;
  pointer-events: none;
}
.laser.replay { animation: laserSweep 1.2s var(--ease) both; }

/* ── CENTER COLUMN — nikdy se nepohne ── */
.lc {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  width: 100%; max-width: 300px;
}

/* Logo sekce */
.lmark {
  width: 64px; height: 64px; border-radius: 50%;
  filter: drop-shadow(0 0 20px rgba(229,57,53,0.4)) drop-shadow(0 0 40px rgba(229,57,53,0.15));
  flex-shrink: 0;
  opacity: 0; animation: fadeUp 0.5s 0.3s var(--ease) forwards;
}
.lmark img { width: 100%; height: 100%; object-fit: contain; border-radius: 50%; }

.llogo {
  font-size: 28px; font-weight: 700; letter-spacing: 0.14em;
  opacity: 0; animation: fadeUp 0.5s 0.4s var(--ease) forwards;
}
.llogo em { color: var(--red); font-style: normal; }
.llogo span { color: var(--t1); }

.lsub {
  font-size: var(--fsm); color: var(--t3);
  letter-spacing: 0.3em; text-transform: uppercase;
  opacity: 0; animation: fadeUp 0.4s 0.5s var(--ease) forwards;
}

/* ── SWAP ZÓNA ── */
.lswap {
  position: relative;
  width: 100%;
  /* Pevná výška = výška formuláře — aby logo neskakovalo */
  height: 148px;
  margin-top: 6px;
  opacity: 0; animation: fadeIn 0.4s 0.6s var(--ease) forwards;
}

/* Form a progress bar jsou absolutní uvnitř swap zóny */
.lform {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; gap: 8px;
}

.lprog {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
}

/* ── INPUTS ── */
.linput {
  width: 100%;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--font);
  font-weight: 420;
  letter-spacing: 0;
  padding: 9px 12px;
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease);
}
.linput::placeholder { color: var(--t4); font-weight: 400; }
.linput:focus { border-color: var(--red); background: rgba(255,255,255,0.06); outline: none; }
.linput:disabled { opacity: 0.4; cursor: not-allowed; }

/* Autofill override */
.linput:-webkit-autofill,
.linput:-webkit-autofill:hover,
.linput:-webkit-autofill:focus {
  -webkit-box-shadow: 0 0 0 1000px var(--ground) inset;
  -webkit-text-fill-color: var(--t1);
  caret-color: var(--t1);
  transition: background-color 5000s;
}

/* ── BUTTON ── */
.lbtn {
  width: 100%; margin-top: 4px;
  padding: 10px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs); font-weight: 500; font-family: var(--font);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  position: relative; overflow: hidden;
  transition: border-color 120ms var(--ease), background 120ms var(--ease);
}
.lbtn::after {
  content: '';
  position: absolute; bottom: 0; left: 0;
  width: 100%; height: 2px; background: var(--red);
  transform: scaleX(0); transform-origin: center;
  transition: transform 200ms var(--ease);
}
.lbtn:hover:not(:disabled) { border-color: var(--red); background: var(--red-10); }
.lbtn:hover:not(:disabled)::after { transform: scaleX(1); }
.lbtn:active:not(:disabled) { transform: scale(0.99); }
.lbtn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── PROGRESS BAR ── */
.lpbar-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.lprog {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.lpbar {
  width: 120px; height: 1px;
  background: var(--b1); border-radius: 99px; overflow: hidden;
  position: relative;
}
.lpbar::after {
  content: '';
  position: absolute; inset-block: 0; left: 0;
  width: 0; background: var(--red);
  animation: fill 1.2s 0.1s var(--ease) forwards;
}

/* ── SWAP PŘECHOD ── */
/* Form odchází: fade dolů + blur */
.swap-leave-active {
  transition:
    opacity 550ms var(--ease),
    transform 550ms var(--ease),
    filter 550ms var(--ease);
}
.swap-leave-to {
  opacity: 0;
  transform: translateY(14px);
  filter: blur(8px);
}

/* Progress nastupuje: fade nahoru + blur, zpožděný o 250ms aby se překryl s odchodem */
.swap-enter-active {
  transition:
    opacity 650ms 250ms var(--ease),
    transform 650ms 250ms var(--ease),
    filter 650ms 250ms var(--ease);
}
.swap-enter-from {
  opacity: 0;
  transform: translateY(-10px);
  filter: blur(8px);
}

/* ── KEYFRAMES ── */
@keyframes drift {
  from { transform: translate(0,0); }
  to   { transform: translate(60px,60px); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes breatheSlow {
  from { opacity: 0.25; transform: translate(-50%,-50%) scale(0.97); }
  to   { opacity: 0.55; transform: translate(-50%,-50%) scale(1.04); }
}
@keyframes laserSweep {
  0%   { transform: translateY(-100vh); opacity: 0; }
  15%  { opacity: 1; }
  100% { transform: translateY(100vh); opacity: 0; }
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fill {
  0%   { width: 0; }
  60%  { width: 75%; }
  100% { width: 100%; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
