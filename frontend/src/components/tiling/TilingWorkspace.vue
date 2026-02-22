<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { SaveIcon, SettingsIcon, PlusIcon, ArrowRightIcon, ArrowDownIcon } from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { useAuthStore } from '@/stores/auth'
import { MODULE_REGISTRY } from '@/types/workspace'
import type { ModuleId, LayoutPreset, DropZone } from '@/types/workspace'
import TileNode from './TileNode.vue'
import TileGlobalDropZones from './TileGlobalDropZones.vue'
import { ICON_SIZE_SM } from '@/config/design'

const ws = useWorkspaceStore()
const auth = useAuthStore()

const fabOpen = ref(false)
const clock = ref('')

const layouts: { id: LayoutPreset; label: string }[] = [
  { id: 'std', label: 'Standardní' },
  { id: 'cmp', label: 'Porovnání' },
  { id: 'hor', label: 'Horizontální' },
  { id: 'qd', label: 'Kompletní' },
]

const topModules = computed(() =>
  Object.values(MODULE_REGISTRY).filter((m) => !m.isSub),
)

const userInitials = computed(() => {
  const name = auth.user?.username ?? 'US'
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

function addModule(id: ModuleId, zone: DropZone = 'center') {
  const ctx = ws.leaves.find(l => l.id === ws.focusedLeafId)?.ctx
    ?? ws.leaves[ws.leaves.length - 1]?.ctx
    ?? 'ca'
  if (zone === 'right' || zone === 'bottom') {
    ws.dockToEdge(id, zone, ctx)
  } else {
    const targetId = ws.focusedLeafId ?? ws.leaves[ws.leaves.length - 1]?.id
    if (!targetId) return
    ws.changeModule(targetId, id)
  }
  fabOpen.value = false
}

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  updateClock()
  setInterval(updateClock, 30_000)
})
</script>

<template>
  <div class="ws-root" @click="fabOpen = false">
    <!-- Ambient background -->
    <div class="bg-grid" />
    <div class="bg-orb a" />
    <div class="bg-orb b" />

    <!-- Header -->
    <header class="hdr">
      <div class="hlogo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <div class="logo"><em>G</em><span>ESTIMA</span></div>
      <span class="logo-div" />

      <!-- Layout presets -->
      <div class="lchips">
        <button
          v-for="layout in layouts"
          :key="layout.id"
          :class="['lchip', { on: ws.currentLayout === layout.id }]"
          @click.stop="ws.setLayout(layout.id)"
        >
          {{ layout.label }}
        </button>
      </div>

      <div class="hfill" />

      <!-- Header actions -->
      <div class="hactions">
        <button class="hbtn" title="Uložit">
          <SaveIcon :size="ICON_SIZE_SM" />
        </button>
        <button class="hbtn" title="Nastavení" @click.stop>
          <SettingsIcon :size="ICON_SIZE_SM" />
        </button>
        <div class="ava" :title="auth.user?.username ?? ''" @click.stop="auth.logout()">
          {{ userInitials }}
        </div>
      </div>
    </header>

    <!-- Tiles area -->
    <main class="tiles">
      <TileNode :node="ws.tree" />
      <TileGlobalDropZones />
    </main>

    <!-- Status bar -->
    <footer class="sbar">
      <span class="sbar-dot" />
      <span class="sbar-label">Připojeno</span>
      <span class="sbar-fill" />
      <span class="sbar-right">
        <span class="sbar-clock">{{ clock }}</span>
        <span class="sbar-sep">·</span>
        <span>Gestima v3</span>
      </span>
    </footer>

    <!-- FAB + Module picker -->
    <button
      class="fab"
      title="Přidat modul"
      data-testid="fab-btn"
      @click.stop="fabOpen = !fabOpen"
    >
      <PlusIcon :size="15" />
    </button>

    <div :class="['mpk', { open: fabOpen }]" @click.stop>
      <div class="mpk-h">
        <span>Přidat modul</span>
        <span class="mpk-hint">→ vpravo · ↓ dole</span>
      </div>
      <div
        v-for="mod in topModules"
        :key="mod.id"
        class="mpk-i"
      >
        <button class="mpk-name-btn" @click="addModule(mod.id, 'center')">{{ mod.label }}</button>
        <span v-if="mod.shortcut" class="mpk-key">{{ mod.shortcut }}</span>
        <div class="mpk-acts">
          <button class="mpk-act" title="Přidat vpravo" @click.stop="addModule(mod.id, 'right')">
            <ArrowRightIcon :size="10" />
          </button>
          <button class="mpk-act" title="Přidat dole" @click.stop="addModule(mod.id, 'bottom')">
            <ArrowDownIcon :size="10" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ws-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  position: relative;
  overflow: hidden;
  background: var(--base);
}

/* Background */
.bg-grid {
  position: fixed;
  inset: -200px;
  z-index: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: drift 40s linear infinite;
  pointer-events: none;
}
.bg-orb {
  position: fixed;
  z-index: 0;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(80px);
}
.bg-orb.a {
  width: 500px; height: 500px; top: -10%; right: -5%;
  background: radial-gradient(circle, var(--red-glow) 0%, transparent 70%);
  animation: orbFloat 12s ease-in-out infinite alternate;
}
.bg-orb.b {
  width: 400px; height: 400px; bottom: -15%; left: 10%;
  background: radial-gradient(circle, rgba(229,57,53,0.06) 0%, transparent 70%);
  animation: orbFloat 15s ease-in-out infinite alternate-reverse;
}

/* Header */
.hdr {
  height: 36px;
  background: var(--surface);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 7px;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.hlogo {
  width: 21px; height: 21px; border-radius: 50%;
  background: var(--red-dim); border: 1px solid rgba(229,57,53,0.25);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  filter: drop-shadow(0 0 6px rgba(229,57,53,0.2));
}
.hlogo svg { width: 11px; height: 11px; stroke: var(--red); }

.logo {
  font-family: var(--mono); font-size: 12.5px; font-weight: 700;
  letter-spacing: 0.1em; user-select: none; flex-shrink: 0;
}
.logo em { color: var(--red); font-style: normal; }
.logo span { color: var(--t1); }

.logo-div {
  width: 1px; height: 13px; background: var(--b2);
  display: inline-block; flex-shrink: 0;
}

.lchips { display: flex; gap: 1px; flex-shrink: 0; }
.lchip {
  padding: 3px 9px; font-size: var(--fsl); font-weight: 500;
  color: var(--t3); background: transparent; border: 1px solid transparent;
  border-radius: var(--rs); cursor: pointer; transition: all 0.12s var(--ease);
  font-family: inherit; white-space: nowrap;
}
.lchip:hover { color: var(--t2); background: var(--b1); }
.lchip.on { color: var(--t1); background: var(--b1); border-color: var(--b2); }
.lchip:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }

.hfill { flex: 1; }

.hactions { display: flex; align-items: center; gap: 3px; }
.hbtn {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: var(--rs);
  color: var(--t3); cursor: pointer; transition: all 0.1s;
}
.hbtn:hover { color: var(--t1); background: var(--b1); }
.hbtn:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }

.ava {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--red-dim); border: 1px solid rgba(229,57,53,0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 8.5px; font-weight: 600; color: var(--red); cursor: pointer;
  user-select: none;
}

/* Tiles */
.tiles {
  flex: 1;
  display: flex;
  padding: var(--gap);
  position: relative;
  z-index: 1;
  min-height: 0;
  overflow: hidden;
  gap: 0;
}

/* Status bar */
.sbar {
  height: 22px;
  background: var(--surface);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--b1);
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 7px;
  font-size: 10.5px;
  color: var(--t4);
  flex-shrink: 0;
  z-index: 10;
}
.sbar-dot {
  width: 5px; height: 5px; border-radius: 50%; background: var(--ok);
  animation: pulse 3s infinite;
}
.sbar-label { color: var(--t3); }
.sbar-fill { flex: 1; }
.sbar-right { display: flex; gap: 6px; align-items: center; }
.sbar-clock { font-family: var(--mono); color: var(--t3); }
.sbar-sep { opacity: 0.2; }

/* FAB */
.fab {
  position: fixed; bottom: 30px; right: 11px;
  width: 33px; height: 33px; border-radius: 50%;
  background: var(--red); border: none;
  color: var(--t1); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 14px rgba(229,57,53,0.35), 0 0 30px rgba(229,57,53,0.1);
  transition: all 0.15s var(--ease); z-index: 20;
}
.fab:hover { background: var(--red); filter: brightness(1.1); transform: scale(1.08); }
.fab:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }

/* Module picker */
.mpk {
  position: fixed; bottom: 68px; right: 11px; width: 190px;
  background: var(--surface); backdrop-filter: blur(20px);
  border: 1px solid var(--b2); border-radius: var(--r);
  box-shadow: 0 12px 40px rgba(0,0,0,0.5); z-index: 25; overflow: hidden;
  transform-origin: bottom right;
  transition: all 0.15s var(--ease);
  opacity: 0; transform: scale(0.92) translateY(4px); pointer-events: none;
}
.mpk.open { opacity: 1; transform: scale(1) translateY(0); pointer-events: auto; }
.mpk-h {
  padding: 5px 9px; font-size: 9px; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.08em;
  border-bottom: 1px solid var(--b1); background: var(--raised);
  display: flex; align-items: center;
}
.mpk-hint { font-size: 8px; color: var(--t4); font-family: var(--mono); margin-left: auto; }

.mpk-i {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 9px; cursor: default;
  transition: background 0.06s;
}
.mpk-i:hover { background: var(--b1); }
.mpk-i:hover .mpk-acts { opacity: 1; }


.mpk-name-btn {
  flex: 1; background: none; border: none; cursor: pointer;
  font-size: var(--fs); color: var(--t2); font-family: inherit;
  text-align: left; padding: 1px 0;
}
.mpk-name-btn:hover { color: var(--t1); }

.mpk-key { font-family: var(--mono); font-size: 9px; color: var(--t4); }

.mpk-acts {
  display: flex; gap: 2px; opacity: 0;
  transition: opacity 0.08s;
}
.mpk-act {
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  background: var(--b2); border: none; border-radius: 3px;
  color: var(--t3); cursor: pointer; transition: all 0.06s;
}
.mpk-act:hover { background: var(--b3); color: var(--t1); }
.mpk-act:focus-visible { outline: 2px solid rgba(255,255,255,0.5); }

/* Animations */
@keyframes drift {
  from { transform: translate(0,0); }
  to   { transform: translate(60px,60px); }
}
@keyframes orbFloat {
  from { transform: translate(0,0); }
  to   { transform: translate(-30px, 20px); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
</style>
