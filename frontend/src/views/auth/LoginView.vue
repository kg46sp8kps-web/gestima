<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const username = ref('')
const password = ref('')

async function submit() {
  if (!username.value || !password.value) return
  await auth.login(username.value, password.value)
}
</script>

<template>
  <div class="login-root">
    <div class="login-bg-grid" />
    <div class="login-vig" />
    <div class="login-glow" />

    <div class="login-card">
      <div class="login-logo-wrap">
        <div class="login-logo-mark">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <div class="login-logo-text">
          <em>G</em><span>ESTIMA</span>
        </div>
        <div class="login-sub">CNC Cost Intelligence</div>
      </div>

      <form @submit.prevent="submit">
        <div class="login-field">
          <label class="login-label" for="login-user">Uživatelské jméno</label>
          <input
            id="login-user"
            v-model="username"
            type="text"
            class="login-input"
            placeholder="admin"
            autocomplete="username"
            data-testid="login-username"
            required
          />
        </div>
        <div class="login-field">
          <label class="login-label" for="login-pass">Heslo</label>
          <input
            id="login-pass"
            v-model="password"
            type="password"
            class="login-input"
            placeholder="••••••••"
            autocomplete="current-password"
            data-testid="login-password"
            required
          />
        </div>
        <button
          type="submit"
          class="login-btn"
          :disabled="auth.loading || !username || !password"
          data-testid="login-submit"
        >
          {{ auth.loading ? 'Přihlašování…' : 'Přihlásit se' }}
        </button>
      </form>

      <div class="login-footer">Gestima v3 · {{ new Date().getFullYear() }}</div>
    </div>
  </div>
</template>

<style scoped>
.login-root {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--base);
  overflow: hidden;
}
.login-bg-grid {
  position: absolute;
  inset: -200px;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: drift 30s linear infinite;
  opacity: 0.7;
}
.login-vig {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, transparent 20%, var(--base) 70%);
}
.login-glow {
  position: absolute;
  width: 500px;
  height: 350px;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse, var(--red-dim) 0%, transparent 70%);
  animation: breatheSlow 4s cubic-bezier(0.45,0,0.55,1) infinite alternate;
}
.login-card {
  position: relative;
  z-index: 1;
  width: 320px;
  background: var(--surface);
  backdrop-filter: blur(24px) saturate(1.4);
  -webkit-backdrop-filter: blur(24px) saturate(1.4);
  border: 1px solid var(--b2);
  border-radius: 12px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04);
  padding: 32px 28px 28px;
  animation: fadeUp 0.5s 0.2s var(--ease) both;
}
.login-logo-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 28px;
}
.login-logo-mark {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid rgba(229,57,53,0.3);
  background: var(--red-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
  filter: drop-shadow(0 0 16px rgba(229,57,53,0.3));
}
.login-logo-mark svg {
  width: 22px;
  height: 22px;
  stroke: var(--red);
}
.login-logo-text {
 
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.12em;
}
.login-logo-text em { color: var(--red); font-style: normal; }
.login-logo-text span { color: var(--t1); }
.login-sub {
  font-size: var(--fsm);
  color: var(--t4);
  letter-spacing: 0.25em;
  text-transform: uppercase;
}
.login-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.login-label {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  letter-spacing: 0.04em;
}
.login-input {
  width: 100%;
  padding: 8px 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: inherit;
  outline: none;
  height: 34px;
  transition: border-color 0.12s, background 0.12s;
}
.login-input:focus { border-color: var(--b3); background: rgba(255,255,255,0.06); }
.login-input:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }
.login-input[type='password'] { letter-spacing: 0.15em; }
.login-btn {
  width: 100%;
  height: 36px;
  margin-top: 20px;
  background: var(--red);
  border: none;
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  letter-spacing: 0.04em;
  transition: background 0.12s, box-shadow 0.12s, transform 0.08s;
  box-shadow: 0 4px 16px rgba(229,57,53,0.3);
}
.login-btn:hover:not(:disabled) { background: var(--red); filter: brightness(1.1); box-shadow: 0 4px 20px rgba(229,57,53,0.45); }
.login-btn:active:not(:disabled) { transform: scale(0.99); }
.login-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.login-btn:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }
.login-footer {
  margin-top: 16px;
  text-align: center;
  font-size: var(--fsm);
  color: var(--t4);
}
@keyframes drift {
  from { transform: translate(0, 0); }
  to   { transform: translate(60px, 60px); }
}
@keyframes breatheSlow {
  from { opacity: 0.5; transform: translate(-50%,-50%) scale(1); }
  to   { opacity: 1;   transform: translate(-50%,-50%) scale(1.08); }
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
