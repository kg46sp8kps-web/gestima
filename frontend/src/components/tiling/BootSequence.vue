<script setup lang="ts">
/**
 * BootSequence — CNC-themed loading sequence for workspace initialization
 *
 * Shows a cinematic boot animation with toolpath SVG traces, laser sweep,
 * and branded logo reveal. Emits 'done' when complete.
 */

import { ref, watch, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{ show: boolean; duration?: number }>(), {
  duration: 1800,
})
const emit = defineEmits<{ done: [] }>()

const fading = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      fading.value = false
      timer = setTimeout(() => {
        fading.value = true
        setTimeout(() => emit('done'), 500)
      }, props.duration)
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <div
    v-if="show"
    class="boot-overlay"
    :class="{ 'boot-overlay--fading': fading }"
    data-testid="boot-sequence"
  >
    <!-- CNC Grid -->
    <div class="boot-grid" />

    <!-- Vignette -->
    <div class="boot-vignette" />

    <!-- Center glow -->
    <div class="boot-glow" />

    <!-- Laser sweep line -->
    <div class="boot-laser" />

    <!-- Toolpath SVG traces -->
    <svg
      class="boot-toolpath"
      viewBox="0 0 1000 600"
      preserveAspectRatio="xMidYMid slice"
      fill="none"
    >
      <!-- v2: --red -->
      <path
        d="M100,300 C200,100 350,500 500,300 S700,100 900,300"
        stroke="#E53935"
        stroke-width="0.8"
        stroke-dasharray="1200"
        stroke-dashoffset="1200"
        style="animation: boot-trace 1.8s ease forwards"
      /><!-- v2: --red -->
      <path
        d="M150,350 C250,150 400,450 550,280 S750,150 950,350"
        :style="{
          stroke: 'var(--t4)',
          strokeWidth: 0.5,
          strokeDasharray: 1200,
          strokeDashoffset: 1200,
          animation: 'boot-trace 2s 0.3s ease forwards',
        }"
      />
      <circle
        cx="500"
        cy="300"
        r="60"
        stroke="rgba(229, 57, 53, 0.1)"
        stroke-width="0.5"
        stroke-dasharray="380"
        stroke-dashoffset="380"
        style="animation: boot-trace 1.5s 0.5s ease forwards"
      />
      <circle
        cx="500"
        cy="300"
        r="90"
        :style="{
          stroke: 'rgba(255, 255, 255, 0.03)',
          strokeWidth: 0.3,
          strokeDasharray: 570,
          strokeDashoffset: 570,
          animation: 'boot-trace 1.8s 0.3s ease forwards',
        }"
      />
    </svg>

    <!-- Center content -->
    <div class="boot-center">
      <!-- Logo mark -->
      <div class="boot-logo-mark">
        <img src="/logo.png" alt="KOVO RYBKA" class="boot-logo-img" />
      </div>

      <!-- Logo text -->
      <div class="boot-logo-text">
        <em>GESTI</em><span>MA</span>
      </div>

      <!-- Subtitle -->
      <div class="boot-subtitle">Kalkulace CNC výroby</div>

      <!-- Progress bar -->
      <div class="boot-progress">
        <div class="boot-progress-bar" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Overlay ── */
.boot-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--base);
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    opacity 0.5s ease,
    visibility 0.5s;
}

.boot-overlay--fading {
  opacity: 0;
  visibility: hidden;
}

/* ── Grid ── */
.boot-grid {
  position: absolute;
  inset: -200px;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  opacity: 0;
  animation:
    boot-drift 30s linear infinite,
    boot-fade-in 1s 0.1s ease forwards;
}

/* ── Vignette ── */
.boot-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 20%, var(--base) 70%);
}

/* ── Glow ── */
.boot-glow {
  position: absolute;
  width: 500px;
  height: 350px;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse at center, rgba(229, 57, 53, 0.08), transparent 70%);
  opacity: 0;
  animation:
    boot-breathe 4s ease infinite alternate,
    boot-fade-in 1.2s 0.2s ease forwards;
}

/* ── Laser sweep ── */
.boot-laser {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent 20%, var(--red) 50%, transparent 80%);
  box-shadow:
    0 0 20px var(--red),
    0 0 60px rgba(229, 57, 53, 0.15);
  animation: boot-laser 1.2s 0.15s ease both;
}

/* ── Toolpath SVG ── */
.boot-toolpath {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.04;
}

/* ── Center content ── */
.boot-center {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

/* ── Logo mark ── */
.boot-logo-mark {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  filter: drop-shadow(0 0 20px rgba(229, 57, 53, 0.4))
    drop-shadow(0 0 40px rgba(229, 57, 53, 0.15));
  opacity: 0;
  animation: boot-fade-up 0.5s 0.3s ease forwards;
}

.boot-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 50%;
}

/* ── Logo text ── */
.boot-logo-text {
  font-family: var(--mono);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.14em;
  opacity: 0;
  animation: boot-fade-up 0.5s 0.4s ease forwards;
}

.boot-logo-text em {
  font-style: normal;
  color: var(--red);
}

.boot-logo-text span {
  color: var(--t1);
}

/* ── Subtitle ── */
.boot-subtitle {
  font-size: var(--fs);
  color: var(--t3);
  letter-spacing: 0.3em;
  text-transform: uppercase;
  opacity: 0;
  animation: boot-fade-up 0.4s 0.6s ease forwards;
}

/* ── Progress bar ── */
.boot-progress {
  width: 120px;
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 99px;
  overflow: hidden;
  margin-top: 8px;
}

.boot-progress-bar {
  height: 100%;
  width: 0;
  background: var(--red);
  animation: boot-fill 1s 0.8s ease forwards;
}

/* ── Keyframes ── */
@keyframes boot-drift {
  from {
    transform: translate(0, 0);
  }
  to {
    transform: translate(60px, 60px);
  }
}

@keyframes boot-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes boot-fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes boot-breathe {
  from {
    opacity: 0.25;
    transform: translate(-50%, -50%) scale(0.97);
  }
  to {
    opacity: 0.55;
    transform: translate(-50%, -50%) scale(1.04);
  }
}

@keyframes boot-laser {
  0% {
    transform: translateY(-100vh);
    opacity: 0;
  }
  15% {
    opacity: 1;
  }
  100% {
    transform: translateY(100vh);
    opacity: 0;
  }
}

@keyframes boot-fill {
  0% {
    width: 0;
  }
  60% {
    width: 75%;
  }
  100% {
    width: 100%;
  }
}

@keyframes boot-trace {
  from {
    stroke-dashoffset: 1200;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
