<template>
  <footer class="app-footer">
    <div class="footer-container">
      <!-- Left: Company -->
      <div class="footer-left">
        <img src="/logo.png" alt="KOVO RYBKA" class="footer-logo" />
        <span>KOVO RYBKA s.r.o.</span>
      </div>

      <!-- Center: GESTIMA branding -->
      <div class="footer-center">
        <span class="footer-brand">
          <span class="brand-red">GESTI</span><span class="brand-gray">MA</span>
        </span>
        <span>v1.10.0</span>
        <span class="footer-sep">•</span>
        <span class="footer-motto">Be lazy. It's way better than talking to people.</span>
        <span class="footer-sep">•</span>
        <span>© 2026</span>
      </div>

      <!-- Right: Tech info -->
      <div class="footer-right">
        <span>FastAPI + SQLite + Vue.js</span>
        <span class="footer-sep">•</span>
        <span class="footer-powered">Powered by Python 🐍</span>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
// Footer component - displays company info, version, and tech stack
</script>

<style scoped>
.app-footer {
  background: var(--bg-secondary, #fff);
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding: 0.25rem 2rem;
}

.footer-container {
  width: 95%;
  min-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  box-sizing: border-box;
}

/* Left */
.footer-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary, #6b7280);
  font-size: 0.7rem;
  justify-self: start;
}

.footer-logo {
  height: 16px;
  width: auto;
  opacity: 0.75;
}

/* Center */
.footer-center {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-muted, #9ca3af);
  font-size: 0.65rem;
  justify-self: center;
}

.footer-brand {
  font-size: 0.75rem;
  font-weight: 700;
}

.brand-red {
  color: var(--accent-red, #dc2626);
}

.brand-gray {
  color: var(--text-secondary, #6b7280);
}

.footer-motto {
  font-style: italic;
  opacity: 0.8;
}

.footer-sep {
  opacity: 0.5;
}

/* Right */
.footer-right {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--text-muted, #9ca3af);
  font-size: 0.6rem;
  justify-self: end;
  text-align: right;
}

.footer-powered {
  font-style: italic;
  opacity: 0.7;
}
</style>
