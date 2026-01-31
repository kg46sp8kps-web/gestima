<template>
  <div class="dashboard-view">
    <div class="dashboard-content">
      <!-- Welcome Card -->
      <div class="welcome-card">
        <div class="welcome-header">
          <h1>GESTIMA</h1>
          <p class="welcome-subtitle">Systém pro výrobní kalkulaci a správu operací</p>
        </div>
        <div class="welcome-user" v-if="auth.user">
          <span class="user-greeting">Přihlášen jako</span>
          <span class="user-name">{{ auth.user.username }}</span>
          <span class="user-role-badge">{{ auth.user.role }}</span>
        </div>
      </div>

      <!-- Coming Soon -->
      <div class="coming-soon-section">
        <div class="coming-soon-icon">
          <BarChart3 :size="48" />
        </div>
        <h2>Dashboard</h2>
        <p class="coming-soon-text">
          Připravujeme pro vás přehledy, KPIs a notifikace.
        </p>
        <ul class="coming-soon-features">
          <li>Počet nezpracovaných nabídek</li>
          <li>QM issues k řešení</li>
          <li>Objem zakázek</li>
          <li>Vytížení pracovišť</li>
        </ul>
      </div>

      <!-- Work Button -->
      <button class="work-button" @click="goToWork">
        <span class="work-icon">
          <Rocket :size="32" />
        </span>
        <span class="work-label">Pracuj</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { BarChart3, Rocket } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

function goToWork() {
  router.push('/windows')
}
</script>

<style scoped>
.dashboard-view {
  padding: 2rem;
  background: var(--bg-default, #f9fafb);
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dashboard-content {
  max-width: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  text-align: center;
}

/* Welcome Card */
.welcome-card {
  background: linear-gradient(135deg, var(--accent-red, #dc2626) 0%, #991b1b 100%);
  border-radius: 16px;
  padding: 2rem;
  color: white;
  width: 100%;
}

.welcome-header h1 {
  margin: 0;
  font-size: var(--text-6xl);
  font-weight: 700;
}

.welcome-subtitle {
  margin: 0.5rem 0 0;
  opacity: 0.9;
  font-size: var(--text-xl);
}

.welcome-user {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.15);
  padding: 0.75rem 1.25rem;
  border-radius: 12px;
  margin-top: 1.5rem;
}

.user-greeting {
  font-size: var(--text-lg);
  opacity: 0.8;
}

.user-name {
  font-weight: 600;
}

.user-role-badge {
  background: rgba(255, 255, 255, 0.25);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: var(--text-sm);
  text-transform: uppercase;
  font-weight: 600;
}

/* Coming Soon */
.coming-soon-section {
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-default, #e5e7eb);
  border-radius: 16px;
  padding: 2rem;
  width: 100%;
}

.coming-soon-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  color: var(--text-secondary, #6b7280);
}

.coming-soon-section h2 {
  margin: 0 0 0.5rem;
  font-size: var(--text-4xl);
  color: var(--text-primary, #111);
}

.coming-soon-text {
  margin: 0 0 1.5rem;
  color: var(--text-muted, #6b7280);
  font-size: var(--text-xl);
}

.coming-soon-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.coming-soon-features li {
  color: var(--text-secondary, #374151);
  font-size: var(--text-lg);
  padding: 0.5rem 1rem;
  background: var(--bg-muted, #f3f4f6);
  border-radius: 8px;
}

.coming-soon-features li::before {
  content: '◦ ';
  color: var(--accent-red, #dc2626);
}

/* Work Button */
.work-button {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 3rem;
  background: var(--accent-red, #dc2626);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: var(--text-4xl);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.work-button:hover {
  background: #b91c1c;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(220, 38, 38, 0.4);
}

.work-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
