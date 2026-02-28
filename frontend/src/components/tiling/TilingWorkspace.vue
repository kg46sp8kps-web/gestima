<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { SaveIcon, SettingsIcon, PlusIcon, ArrowLeftIcon, ArrowUpIcon, ArrowDownIcon } from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { useAuthStore } from '@/stores/auth'
import { MODULE_REGISTRY } from '@/types/workspace'
import type { ModuleId } from '@/types/workspace'
import TileNode from './TileNode.vue'
import TileGlobalDropZones from './TileGlobalDropZones.vue'
import LayoutManager from './LayoutManager.vue'
import { ICON_SIZE_SM } from '@/config/design'
import Input from '@/components/ui/Input.vue'

const ws = useWorkspaceStore()
const auth = useAuthStore()

const fabOpen = ref(false)
const clock = ref('')
const showLayoutManager = ref(false)
const moduleSearchOpen = ref(false)
const moduleSearchQuery = ref<string | null>('')

const topModules = computed(() =>
  Object.values(MODULE_REGISTRY).filter((m) => !m.isSub),
)
const filteredTopModules = computed(() => {
  const query = (moduleSearchQuery.value ?? '').trim().toLocaleLowerCase('cs-CZ')
  if (!query) return topModules.value
  return topModules.value.filter((mod) =>
    mod.label.toLocaleLowerCase('cs-CZ').includes(query)
    || mod.id.toLocaleLowerCase('cs-CZ').includes(query),
  )
})

const userInitials = computed(() => {
  const name = auth.user?.username ?? 'US'
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

function addModule(id: ModuleId, zone: 'left' | 'right' | 'top' | 'bottom' = 'right') {
  const ctx = ws.leaves.find(l => l.id === ws.focusedLeafId)?.ctx
    ?? ws.leaves[ws.leaves.length - 1]?.ctx
    ?? 'ca'
  ws.dockToEdge(id, zone, ctx)
  fabOpen.value = false
}

function selectModuleFromSearch(moduleId: ModuleId) {
  addModule(moduleId, 'right')
  moduleSearchQuery.value = ''
  moduleSearchOpen.value = false
}

function onModuleSearchKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    moduleSearchOpen.value = false
    return
  }
  if (event.key === 'Enter') {
    const firstMatch = filteredTopModules.value[0]
    if (firstMatch) selectModuleFromSearch(firstMatch.id)
  }
}

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })
}

let clockInterval: ReturnType<typeof setInterval>

onMounted(() => {
  updateClock()
  clockInterval = setInterval(updateClock, 30_000)
  ws.fetchLayouts()
})

onUnmounted(() => {
  clearInterval(clockInterval)
})
</script>

<template>
  <div class="ws-root" @click="fabOpen = false; moduleSearchOpen = false">
    <!-- Ambient background -->
    <div class="bg-grid" />
    <div class="bg-orb a" />
    <div class="bg-orb b" />

    <!-- Header -->
    <header class="hdr">
      <div class="hlogo-wrap">
        <img src="/logo.png" class="hlogo-img" alt="logo" />
        <div class="logo"><em>GESTI</em><span>MA</span></div>
      </div>
      <span class="logo-div" />

      <!-- Layout chips from backend -->
      <div class="lchips">
        <button
          v-for="layout in ws.headerLayouts"
          :key="layout.id"
          :class="['lchip', { on: ws.currentLayoutId === layout.id }]"
          :data-testid="`layout-chip-${layout.id}`"
          @click.stop="ws.loadLayout(layout.id)"
        >
          {{ layout.name }}
        </button>
      </div>

      <div class="module-search" @click.stop>
        <Input
          v-model="moduleSearchQuery"
          bare
          class="module-search-input"
          testid="module-search-input"
          type="search"
          placeholder="Hledat..."
          @focus="moduleSearchOpen = true"
          @keydown="onModuleSearchKeydown"
        />
        <div
          v-if="moduleSearchOpen"
          class="module-search-dropdown"
          data-testid="module-search-dropdown"
        >
          <button
            v-for="mod in filteredTopModules"
            :key="mod.id"
            class="module-search-item"
            :data-testid="`module-search-item-${mod.id}`"
            @click.stop="selectModuleFromSearch(mod.id)"
          >
            <span class="module-search-label">{{ mod.label }}</span>
            <span class="module-search-id">{{ mod.id }}</span>
          </button>
          <div
            v-if="filteredTopModules.length === 0"
            class="module-search-empty"
            data-testid="module-search-empty"
          >
            Žádný panel neodpovídá filtru
          </div>
        </div>
      </div>

      <div class="hfill" />

      <!-- Header actions -->
      <div class="hactions">
        <button
          class="icon-btn"
          title="Uložit layout"
          :class="{ 'hbtn-dim': ws.currentLayoutId === null }"
          data-testid="save-layout-btn"
          @click.stop="ws.saveCurrentLayout()"
        >
          <SaveIcon :size="ICON_SIZE_SM" />
        </button>
        <button
          class="icon-btn"
          title="Správa layoutů"
          data-testid="layout-manager-btn"
          @click.stop="showLayoutManager = true"
        >
          <SettingsIcon :size="ICON_SIZE_SM" />
        </button>
        <div class="ava" data-testid="user-avatar-btn" :title="auth.user?.username ?? ''" @click.stop="auth.logout()">
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
        <span class="mpk-hint">klik → vpravo</span>
      </div>
      <div
        v-for="mod in topModules"
        :key="mod.id"
        class="mpk-i"
      >
        <button class="mpk-name-btn" :data-testid="`module-btn-${mod.id}`" @click="addModule(mod.id, 'right')">{{ mod.label }}</button>
        <span v-if="mod.shortcut" class="mpk-key">{{ mod.shortcut }}</span>
        <div class="mpk-acts">
          <button class="mpk-act" :data-testid="`module-left-${mod.id}`" title="Přidat vlevo" @click.stop="addModule(mod.id, 'left')">
            <ArrowLeftIcon :size="10" />
          </button>
          <button class="mpk-act" :data-testid="`module-top-${mod.id}`" title="Přidat nahoře" @click.stop="addModule(mod.id, 'top')">
            <ArrowUpIcon :size="10" />
          </button>
          <button class="mpk-act" :data-testid="`module-bottom-${mod.id}`" title="Přidat dole" @click.stop="addModule(mod.id, 'bottom')">
            <ArrowDownIcon :size="10" />
          </button>
        </div>
      </div>
    </div>

    <!-- Layout Manager modal -->
    <LayoutManager v-model="showLayoutManager" />
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

.hlogo-wrap {
  display: flex; align-items: center; gap: 7px; flex-shrink: 0;
}
.hlogo-img {
  height: 22px;
  width: auto;
  object-fit: contain;
  flex-shrink: 0;
  user-select: none;
}

.logo {
  font-size: var(--fs); font-weight: 700;
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
  padding: 3px 9px; font-size: var(--fsm); font-weight: 500;
  color: var(--t3); background: transparent; border: 1px solid transparent;
  border-radius: var(--rs); cursor: pointer; transition: all 120ms var(--ease);
  font-family: inherit; white-space: nowrap;
}
.lchip:hover { color: var(--t2); background: var(--b1); }
.lchip.on { color: var(--t1); background: var(--b1); border-color: var(--b2); }
.lchip:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }

.module-search {
  position: relative;
  width: 220px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

:deep(.module-search-input) {
  width: 100%;
  height: 22px;
  border-radius: var(--rs);
  border: 1px solid var(--b2);
  background: var(--b1);
  color: var(--t2);
  font-size: var(--fs);
  padding: 0 8px;
  font-family: inherit;
  line-height: 1;
  transition: border-color 100ms var(--ease), background 100ms var(--ease);
}
:deep(.module-search-input)::placeholder { color: var(--t4); }
:deep(.module-search-input):focus {
  outline: none;
  border-color: var(--b3);
  background: var(--raised);
}
:deep(.module-search-input)::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  cursor: pointer;
  background:
    linear-gradient(45deg, transparent 42%, var(--t4) 42%, var(--t4) 58%, transparent 58%),
    linear-gradient(-45deg, transparent 42%, var(--t4) 42%, var(--t4) 58%, transparent 58%);
}

.module-search-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 12px 36px rgba(0,0,0,0.45);
  z-index: 30;
  max-height: 284px;
  overflow-y: auto;
  padding: 4px;
}

.module-search-item {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--t2);
  border-radius: var(--rs);
  min-height: 28px;
  padding: 4px 6px;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.module-search-item:hover {
  background: var(--b1);
  color: var(--t1);
}

.module-search-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-search-id {
  color: var(--t4);
  font-size: var(--fss);
  white-space: nowrap;
}

.module-search-empty {
  color: var(--t4);
  font-size: var(--fsm);
  padding: 8px 6px;
}

.hfill { flex: 1; }

.hactions { display: flex; align-items: center; gap: 3px; }
.hbtn-dim { opacity: 0.4; }

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
  font-size: var(--fsm);
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
.sbar-clock { color: var(--t3); }
.sbar-sep { opacity: 0.2; }

/* FAB */
.fab {
  position: fixed; bottom: 30px; right: 11px;
  width: 33px; height: 33px; border-radius: 50%;
  background: var(--red); border: none;
  color: var(--t1); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 14px rgba(229,57,53,0.35), 0 0 30px rgba(229,57,53,0.1);
  transition: all 150ms var(--ease); z-index: 20;
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
  transition: all 150ms var(--ease);
  opacity: 0; transform: scale(0.92) translateY(4px); pointer-events: none;
}
.mpk.open { opacity: 1; transform: scale(1) translateY(0); pointer-events: auto; }
.mpk-h {
  padding: 5px 9px; font-size: var(--fss); font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.08em;
  border-bottom: 1px solid var(--b1); background: var(--raised);
  display: flex; align-items: center;
}
.mpk-hint { font-size: 8px; color: var(--t4); margin-left: auto; }

.mpk-i {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 9px; cursor: default;
  transition: background 60ms var(--ease);
}
.mpk-i:hover { background: var(--b1); }
.mpk-i:hover .mpk-acts { opacity: 1; }


.mpk-name-btn {
  flex: 1; background: none; border: none; cursor: pointer;
  font-size: var(--fs); color: var(--t2); font-family: inherit;
  text-align: left; padding: 1px 0;
}
.mpk-name-btn:hover { color: var(--t1); }

.mpk-key { font-size: var(--fss); color: var(--t4); }

.mpk-acts {
  display: flex; gap: 2px; opacity: 0;
  transition: opacity 80ms var(--ease);
}
.mpk-act {
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  background: var(--b2); border: none; border-radius: var(--rs);
  color: var(--t3); cursor: pointer; transition: all 60ms var(--ease);
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
