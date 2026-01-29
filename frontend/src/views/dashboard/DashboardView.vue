<template>
  <div class="dashboard-view">
    <div class="dashboard-content">
      <!-- Welcome Card -->
      <div class="welcome-card">
        <div class="welcome-header">
          <h1>Vítejte v GESTIMA</h1>
          <p class="welcome-subtitle">Systém pro výrobní kalkulaci a správu operací</p>
        </div>
        <div class="welcome-user" v-if="auth.user">
          <span class="user-greeting">Přihlášen jako</span>
          <span class="user-name">{{ auth.user.username }}</span>
          <span class="user-role-badge">{{ auth.user.role }}</span>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <h2 class="section-title">Rychlé akce</h2>
        <div class="actions-grid">
          <router-link to="/parts/new" class="action-card">
            <span class="action-icon">➕</span>
            <span class="action-label">Nový díl</span>
          </router-link>
          <router-link to="/parts" class="action-card">
            <span class="action-icon">📦</span>
            <span class="action-label">Seznam dílů</span>
          </router-link>
          <router-link to="/pricing/batch-sets" class="action-card">
            <span class="action-icon">💰</span>
            <span class="action-label">Sady cen</span>
          </router-link>
          <router-link to="/work-centers" class="action-card">
            <span class="action-icon">🏭</span>
            <span class="action-label">Pracoviště</span>
          </router-link>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-section">
        <h2 class="section-title">Přehled</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ stats.partsCount }}</div>
            <div class="stat-label">Dílů celkem</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.batchSetsCount }}</div>
            <div class="stat-label">Cenových sad</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.workCentersCount }}</div>
            <div class="stat-label">Pracovišť</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ permissionsSummary }}</div>
            <div class="stat-label">Vaše oprávnění</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// Stats (placeholder - would come from API)
const stats = ref({
  partsCount: '...',
  batchSetsCount: '...',
  workCentersCount: '...'
})

const permissionsSummary = computed(() => {
  if (auth.isAdmin) return 'Admin'
  if (auth.isOperator) return 'Operátor'
  return 'Prohlížeč'
})

// Load stats on mount (placeholder)
onMounted(async () => {
  // TODO: Fetch real stats from API
  stats.value = {
    partsCount: '-',
    batchSetsCount: '-',
    workCentersCount: '-'
  }
})
</script>

<style scoped>
.dashboard-view {
  padding: 2rem;
  background: var(--bg-default, #f9fafb);
  min-height: 100%;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Welcome Card */
.welcome-card {
  background: linear-gradient(135deg, var(--accent-red, #dc2626) 0%, #991b1b 100%);
  border-radius: 16px;
  padding: 2rem;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.welcome-header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
}

.welcome-subtitle {
  margin: 0.5rem 0 0;
  opacity: 0.9;
  font-size: 0.95rem;
}

.welcome-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.15);
  padding: 0.75rem 1.25rem;
  border-radius: 12px;
}

.user-greeting {
  font-size: 0.8rem;
  opacity: 0.8;
}

.user-name {
  font-weight: 600;
}

.user-role-badge {
  background: rgba(255, 255, 255, 0.25);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  text-transform: uppercase;
  font-weight: 600;
}

/* Section Title */
.section-title {
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #111);
}

/* Quick Actions */
.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-default, #e5e7eb);
  border-radius: 12px;
  text-decoration: none;
  color: var(--text-primary, #111);
  transition: all 0.15s ease;
}

.action-card:hover {
  border-color: var(--accent-red, #dc2626);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.action-icon {
  font-size: 2rem;
}

.action-label {
  font-size: 0.875rem;
  font-weight: 500;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-default, #e5e7eb);
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent-red, #dc2626);
}

.stat-label {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-muted, #6b7280);
}
</style>
