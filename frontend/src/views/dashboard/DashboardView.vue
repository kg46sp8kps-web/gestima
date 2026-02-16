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
          <BarChart3 :size="ICON_SIZE.HERO" />
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

      <!-- Admin Section (only for admin users) -->
      <div v-if="auth.isAdmin" class="admin-section">
        <h3 class="admin-title">Administrace</h3>
        <div class="admin-buttons">
          <button class="admin-btn" @click="router.push('/admin/master-data')">
            📊 Kmenová data
          </button>
        </div>
      </div>

      <!-- Work Button -->
      <button class="work-button" @click="goToWork">
        <span class="work-icon">
          <Rocket :size="ICON_SIZE.XLARGE" />
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
import { ICON_SIZE } from '@/config/design'

const router = useRouter()
const auth = useAuthStore()

function goToWork() {
  router.push('/windows')
}
</script>

<style scoped>
.dashboard-view {
  padding: 2rem;
  background: var(--bg-base);
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
  background: transparent;
  border: 1px solid var(--brand);
  border-radius: var(--radius-2xl);
  padding: 2rem;
  color: var(--text-primary);
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
  gap: var(--space-2);
  background: rgba(255, 255, 255, 0.15);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-xl);
  margin-top: var(--space-5);
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
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  text-transform: uppercase;
  font-weight: 600;
}

/* Coming Soon */
.coming-soon-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-2xl);
  padding: 2rem;
  width: 100%;
}

.coming-soon-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  color: var(--text-secondary);
}

.coming-soon-section h2 {
  margin: 0 0 0.5rem;
  font-size: var(--text-4xl);
  color: var(--text-primary);
}

.coming-soon-text {
  margin: 0 0 1.5rem;
  color: var(--text-secondary);
  font-size: var(--text-xl);
}

.coming-soon-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.coming-soon-features li {
  color: var(--text-secondary);
  font-size: var(--text-lg);
  padding: var(--space-2) var(--space-4);
  background: var(--bg-raised);
  border-radius: var(--radius-lg);
}

.coming-soon-features li::before {
  content: '◦ ';
  color: var(--brand);
}

/* Admin Section */
.admin-section {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-2xl);
  padding: var(--space-5);
}

.admin-title {
  margin: 0 0 1rem;
  font-size: var(--text-2xl);
  color: var(--text-primary);
  text-align: center;
}

.admin-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.admin-btn {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  font-size: var(--text-lg);
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.admin-btn:hover {
  background: var(--brand);
  color: white;
  border-color: var(--brand);
  transform: translateY(-1px);
}

/* Work Button */
.work-button {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) 3rem;
  background: var(--brand);
  color: white;
  border: none;
  border-radius: var(--radius-xl);
  font-size: var(--text-4xl);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.work-button:hover {
  background: var(--brand-hover);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(220, 38, 38, 0.4);
}

.work-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
