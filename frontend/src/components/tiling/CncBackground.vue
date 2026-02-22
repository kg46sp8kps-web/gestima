<script setup lang="ts">
// Pure visual background component — CNC/industrial atmosphere
// No props, no emits — decoration only
</script>

<template>
  <div class="cnc-background" aria-hidden="true">
    <!-- CNC Line Grid -->
    <div class="bg-grid"></div>

    <!-- Breathing Glow -->
    <div class="bg-glow"></div>

    <!-- Vignette -->
    <div class="bg-vignette"></div>

    <!-- Red Orbs -->
    <div class="bg-orb orb-a"></div>
    <div class="bg-orb orb-b"></div>

    <!-- Green Pricing Orb -->
    <div class="bg-orb orb-c"></div>

    <!-- CNC Toolpath SVG -->
    <svg
      class="bg-toolpath"
      viewBox="0 0 1920 1080"
      preserveAspectRatio="none"
    >
      <path
        class="toolpath-line tp-1"
        d="M-100,200 C200,150 400,350 600,280 S900,400 1100,320 S1400,200 1600,350 S1900,280 2100,400"
        fill="none"
        stroke="var(--red)"
        stroke-width="1"
        stroke-dasharray="1000"
      />
      <path
        class="toolpath-line tp-2"
        d="M-50,600 C150,550 350,700 550,650 S850,500 1050,580 S1350,700 1550,620 S1750,500 2000,650"
        fill="none"
        stroke="var(--t4)"
        stroke-width="0.8"
        stroke-dasharray="1000"
      />
      <path
        class="toolpath-line tp-3"
        d="M200,-50 C250,200 180,400 300,500 S350,700 280,900 S400,1000 350,1200"
        fill="none"
        stroke="var(--red)"
        stroke-width="0.6"
        stroke-dasharray="1000"
        opacity="0.6"
      />
      <path
        class="toolpath-line tp-4"
        d="M1400,-50 C1350,150 1420,300 1380,500 S1300,650 1400,800 S1350,950 1420,1200"
        fill="none"
        stroke="var(--t4)"
        stroke-width="0.6"
        stroke-dasharray="1000"
        opacity="0.8"
      />
    </svg>

    <!-- Floating Coordinates -->
    <div class="coords coords-tl">X0.000 Y0.000<br>Z+42.500</div>
    <div class="coords coords-tr">G54 WCS<br>T01 D1</div>
    <div class="coords coords-bl">F2400 S8000<br>M03 CW</div>
    <!-- eslint-disable-next-line vue/no-irregular-whitespace -->
    <div class="coords coords-br">DRO ACTIVE<br>RAPID &#x2192;</div>

    <!-- Grain Texture Overlay -->
    <div class="grain-overlay"></div>

    <!-- SVG Defs (sparkline gradients, markers) -->
    <svg
      class="svg-defs"
      aria-hidden="true"
      :style="{ position: 'absolute', width: 0, height: 0 }"
    >
      <defs>
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--t4)" stop-opacity="0.3" />
          <stop offset="100%" stop-color="var(--t4)" stop-opacity="0" />
        </linearGradient>
        <marker
          id="arrowMarker"
          markerWidth="6"
          markerHeight="4"
          refX="6"
          refY="2"
          orient="auto"
        >
          <path d="M0,0 L6,2 L0,4" fill="var(--t4)" />
        </marker>
      </defs>
    </svg>
  </div>
</template>

<style scoped>
/* ── Container ── */
.cnc-background {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

/* ── CNC Line Grid ── */
.bg-grid {
  position: fixed;
  inset: -200px;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: cnc-drift 40s linear infinite;
}

/* ── Breathing Glow ── */
.bg-glow {
  position: fixed;
  z-index: 0;
  pointer-events: none;
  width: 700px;
  height: 500px;
  top: 35%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    ellipse at center,
    rgba(229, 57, 53, 0.12) 0%,
    transparent 65%
  );
  animation: cnc-breathe 6s ease infinite alternate;
  will-change: opacity, transform;
}

/* ── Vignette ── */
.bg-vignette {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(
    ellipse at center,
    transparent 40%,
    var(--base) 100%
  );
}

/* ── Orbs (shared) ── */
.bg-orb {
  position: fixed;
  z-index: 0;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(80px);
}

/* Red Orb A */
.orb-a {
  width: 600px;
  height: 600px;
  top: -10%;
  right: -5%;
  background: radial-gradient(
    circle at center,
    rgba(229, 57, 53, 0.25) 0%,
    transparent 65%
  );
  animation: cnc-orb-float 12s ease-in-out infinite alternate;
}

/* Red Orb B */
.orb-b {
  width: 500px;
  height: 500px;
  bottom: -15%;
  left: 10%;
  background: radial-gradient(
    circle at center,
    rgba(229, 57, 53, 0.12) 0%,
    transparent 65%
  );
  animation: cnc-orb-float 15s ease-in-out infinite alternate-reverse;
}

/* Green Pricing Orb */
.orb-c {
  width: 400px;
  height: 400px;
  top: 50%;
  left: 60%;
  background: radial-gradient(
    circle at center,
    rgba(0, 255, 0, 0.04) 0%,
    transparent 65%
  );
  animation: cnc-orb-float 18s ease-in-out infinite alternate;
}

/* ── CNC Toolpath SVG ── */
.bg-toolpath {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  width: 100%;
  height: 100%;
  opacity: 0.12;
}

.toolpath-line {
  animation: cnc-trace-path 20s linear infinite;
}

.tp-1 {
  animation-duration: 20s;
}

.tp-2 {
  animation-duration: 25s;
  animation-delay: -5s;
}

.tp-3 {
  animation-duration: 30s;
  animation-delay: -10s;
}

.tp-4 {
  animation-duration: 22s;
  animation-delay: -15s;
}

/* ── Floating Coordinates ── */
.coords {
  position: fixed;
  z-index: 0;
  pointer-events: none;
  font-family: var(--mono);
  font-size: var(--fs);
  opacity: 0.35;
  color: var(--t3);
  line-height: 1.5;
  white-space: nowrap;
}

.coords-tl {
  top: 42px;
  left: 12px;
}

.coords-tr {
  top: 42px;
  right: 12px;
  text-align: right;
}

.coords-bl {
  bottom: 28px;
  left: 12px;
}

.coords-br {
  bottom: 28px;
  right: 12px;
  text-align: right;
}

/* ── Grain Texture Overlay ── */
.grain-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.02;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='256' height='256' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
  background-size: 128px 128px;
}

/* ── SVG Defs (hidden) ── */
.svg-defs {
  overflow: hidden;
}

/* ── Keyframe Animations ── */
@keyframes cnc-drift {
  from {
    transform: translate(0, 0);
  }
  to {
    transform: translate(60px, 60px);
  }
}

@keyframes cnc-breathe {
  from {
    opacity: 0.25;
    transform: translate(-50%, -50%) scale(0.97);
  }
  to {
    opacity: 0.55;
    transform: translate(-50%, -50%) scale(1.04);
  }
}

@keyframes cnc-orb-float {
  from {
    transform: translate(0, 0);
  }
  to {
    transform: translate(-30px, 20px);
  }
}

@keyframes cnc-trace-path {
  from {
    stroke-dashoffset: 1000;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
