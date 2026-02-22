<script setup lang="ts">
/**
 * GlassPanel — Glassmorphism panel wrapper for tiling workspace
 *
 * Matches v3 preview: glassmorphism surface, corner marks, context linking stripe,
 * inner panel background (grid + glow + toolpath), entrance animation, maximize/close.
 */

import { ref } from 'vue'
import type { LinkingGroup } from '@/types/workspace'

interface Props {
  title?: string
  count?: number
  linkingGroup?: LinkingGroup
  showCorners?: boolean
  showHeader?: boolean
  focused?: boolean
  enterDelay?: number
}

withDefaults(defineProps<Props>(), {
  linkingGroup: null,
  showCorners: true,
  showHeader: true,
  focused: false,
  enterDelay: 0,
})

const emit = defineEmits<{
  maximize: []
  close: []
}>()

const isMaximized = ref(false)

function handleMaximize() {
  isMaximized.value = !isMaximized.value
  emit('maximize')
}
</script>

<template>
  <div
    class="glass-panel"
    :class="[
      linkingGroup ? `ctx-${linkingGroup}` : '',
      { focused, maximized: isMaximized },
    ]"
    :style="enterDelay ? { animationDelay: `${enterDelay}ms` } : undefined"
  >
    <!-- Header -->
    <div
      v-if="showHeader"
      class="panel-header"
      @dblclick="handleMaximize"
    >
      <slot name="header-left">
        <span v-if="title" class="panel-title">
          {{ title }}
          <span v-if="count != null" class="panel-count">{{ count }}</span>
        </span>
      </slot>
      <div class="header-fill" />
      <slot name="header-right">
        <div class="header-actions">
          <button
            class="panel-btn"
            data-testid="panel-maximize"
            title="Maximalizovat"
            @click="handleMaximize"
          >
            &#9633;
          </button>
          <button
            class="panel-btn panel-btn-close"
            data-testid="panel-close"
            title="Zavřít"
            @click="emit('close')"
          >
            &#215;
          </button>
        </div>
      </slot>
    </div>

    <!-- Content -->
    <div class="panel-body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
/* ── Local tokens ── */
.glass-panel {
  --panel-radius: 7px;
}

/* ── Entrance animation ── */
@keyframes panel-enter {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* ── Panel container ── */
.glass-panel {
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  border-radius: var(--r);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(12px) saturate(1.3);
  -webkit-backdrop-filter: blur(12px) saturate(1.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  animation: panel-enter 0.35s ease both;
  transition:
    border-color 0.15s,
    box-shadow 0.2s;
}

.glass-panel:hover {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow:
    0 0 20px rgba(229, 57, 53, 0.06),
    0 4px 20px rgba(0, 0, 0, 0.3);
}

/* ── Focused state ── */
.glass-panel.focused {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow:
    0 0 30px rgba(229, 57, 53, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.10),
    0 8px 32px rgba(0, 0, 0, 0.4);
}

/* ── Maximized state ── */
.glass-panel.maximized {
  position: fixed;
  inset: 38px 3px 24px 3px;
  z-index: 50;
}

/* ── Context linking stripe (::before) ── */
.glass-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  z-index: 5;
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: none;
}

.glass-panel.ctx-red::before {
  background: linear-gradient(
    90deg,
    transparent,
    var(--red) 30%,
    var(--red) 70%,
    transparent
  );
  opacity: 0.4;
}

.glass-panel.ctx-green::before {
  background: linear-gradient(
    90deg,
    transparent,
    var(--ok) 30%,
    var(--ok) 70%,
    transparent
  );
  opacity: 0.3;
}

.glass-panel.ctx-blue::before {
  background: linear-gradient(
    90deg,
    transparent,
    var(--t3) 30%,
    var(--t3) 70%,
    transparent
  );
  opacity: 0.4;
}

.glass-panel.ctx-yellow::before {
  background: linear-gradient(
    90deg,
    transparent,
    var(--warn) 30%,
    var(--warn) 70%,
    transparent
  );
  opacity: 0.4;
}

/* Focused stripe — increased opacity */
.glass-panel.focused::before {
  opacity: 0.7;
}

/* ══════════════════════════════════════
   PANEL HEADER — 28px
   ══════════════════════════════════════ */
.panel-header {
  display: flex;
  align-items: center;
  height: 28px;
  padding: 0 8px;
  gap: 4px;
  flex-shrink: 0;
  user-select: none;
  background: rgba(255, 255, 255, 0.025);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 1;
}

/* ── Title ── */
.panel-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fsl);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Count badge ── */
.panel-count {
  font-family: var(--mono);
  font-size: var(--fsl);
  color: var(--t4);
  padding: 1px 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
}

/* ── Header spacer ── */
.header-fill {
  flex: 1;
  min-width: 0;
}

/* ── Header actions ── */
.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.panel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  border-radius: 2px;
  color: var(--t4);
  font-size: var(--fsl);
  cursor: pointer;
  transition: all 0.06s;
  padding: 0;
  line-height: 1;
  font-family: inherit;
}

.panel-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--t1);
}

.panel-btn-close:hover {
  background: rgba(255, 0, 0, 0.08);
  color: var(--err);
}

/* ── Content area ── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  position: relative;
  z-index: 1;
}
</style>
