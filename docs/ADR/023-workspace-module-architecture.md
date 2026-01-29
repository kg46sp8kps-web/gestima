# ADR-023: Workspace Module Architecture

**Status:** Přijato (Design Phase)
**Date:** 2026-01-28
**Context:** Budoucí UI architektura pro multi-panel linked views
**Timeline:** v3.0+ (Q2 2026+)

---

## Kontext

**Vize:** Uživatel chce flexibilní workspace systém podobný tiling window managers (i3, tmux) nebo VS Code panels:

1. **Multi-panel layout** - více modulů na obrazovce současně
2. **Resize & drag** - měnit velikost a pozici panelů
3. **Linked views** - moduly propojené barevnými "linky"
4. **Context switching** - změna v jednom modulu → reakce v propojeném

**Příklad použití:**

```
┌─ WORKSPACE "Cenování" ────────────────────────────────────────────┐
│                                                                    │
│  ┌─────────────┐  🔴  ┌─────────────┐                             │
│  │ 📋 Parts    │─────▶│ 💰 BatchSets│  ← Změním Part → změní se   │
│  │ ▶ XYZ-001   │      │ Sady pro    │     BatchSets pro ten Part  │
│  │   ABC-002   │      │ XYZ-001     │                              │
│  └─────────────┘      └─────────────┘                              │
│         │                                                          │
│         │ 🔴 (červený link)                                        │
│         ▼                                                          │
│  ┌─────────────┐                                                   │
│  │ 🔧 Operations                                                   │
│  │ Pro XYZ-001 │  ← Také propojené na Part (červený link)         │
│  └─────────────┘                                                   │
│                                                                    │
│  ┌─────────────┐  🟢  ┌─────────────┐                             │
│  │ 👥 Customers│─────▶│ 📄 Quotes   │  ← Nezávislý kontext        │
│  │ ▶ Firma ABC │      │ Pro ABC     │     (zelený link)           │
│  └─────────────┘      └─────────────┘                              │
│                              │                                     │
│                              │ 🔴 (přepnu na červený link)         │
│                              ▼                                     │
│                       ┌─────────────┐                              │
│                       │ 📋 Parts    │  ← Ukazuje Parts z Quote,    │
│                       │ z nabídky   │     propojené na horní Parts │
│                       └─────────────┘                              │
│                                                                    │
│  [+ Add module] [Save layout] [Load layout]                       │
└────────────────────────────────────────────────────────────────────┘
```

**Klíčové koncepty:**
- **Modul** = nezávislá UI komponenta (Parts, BatchSets, Quotes, Operations...)
- **Link (barva)** = propojení mezi moduly (červená, zelená, modrá...)
- **Workspace** = layout modulů s jejich propojením
- **Context** = aktuální stav linku (např. `{ partId: 123 }`)

---

## Rozhodnutí

### 1. Module Pattern (Základní stavební blok)

Každý modul v GESTIMA MUSÍ implementovat tento interface:

```javascript
// app/static/js/core/module-interface.js

/**
 * Module Interface - každý modul MUSÍ implementovat
 *
 * @property {string} moduleType - Typ modulu ('parts', 'batch-sets', 'quotes'...)
 * @property {string} moduleId - Unikátní ID instance
 * @property {string|null} linkColor - Barva linku ('red', 'green', 'blue', null)
 * @property {Object} linkContext - Kontext z linku (např. { partId: 123 })
 *
 * @method init() - Inicializace modulu
 * @method onLinkChange(context) - Reakce na změnu linku
 * @method destroy() - Cleanup při odstranění modulu
 */

const ModuleInterface = {
    // Identity
    moduleType: 'abstract',
    moduleId: null,
    linkColor: null,

    // State from link
    linkContext: {},

    // Lifecycle
    init() {
        throw new Error('Module must implement init()');
    },

    onLinkChange(context) {
        // Override in concrete module
        this.linkContext = context;
    },

    destroy() {
        // Cleanup subscriptions, timers, etc.
    },

    // Communication
    emitToLink(eventType, data) {
        if (this.linkColor) {
            LinkManager.emit(this.linkColor, {
                source: this.moduleId,
                type: eventType,
                data: data
            });
        }
    }
};
```

### 2. Konkrétní modul (příklad: BatchSets)

```javascript
// app/static/js/modules/batch-sets.js

function batchSetsModule(config = {}) {
    return {
        // Implement ModuleInterface
        moduleType: 'batch-sets',
        moduleId: config.moduleId || `batch-sets-${Date.now()}`,
        linkColor: config.linkColor || null,
        linkContext: {},

        // Module-specific state
        partId: null,
        batchSets: [],
        selectedSetId: null,
        batches: [],

        // Lifecycle
        async init() {
            // Subscribe to link (if linked)
            if (this.linkColor) {
                LinkManager.subscribe(this.linkColor, this);
            }

            // Initial load (if partId provided directly)
            if (config.partId) {
                this.partId = config.partId;
                await this.loadBatchSets();
            }
        },

        // React to link changes
        async onLinkChange(context) {
            this.linkContext = context;

            if (context.partId && context.partId !== this.partId) {
                this.partId = context.partId;
                await this.loadBatchSets();
            }
        },

        destroy() {
            if (this.linkColor) {
                LinkManager.unsubscribe(this.linkColor, this);
            }
        },

        // Module-specific methods
        async loadBatchSets() { /* ... */ },
        async freezeSet() { /* ... */ },
        // ...
    };
}

// Register module type
ModuleRegistry.register('batch-sets', batchSetsModule);
```

### 3. Link Manager (Centrální komunikace)

```javascript
// app/static/js/core/link-manager.js

const LinkManager = {
    // Link colors and their contexts
    links: {
        red: {},      // { partId: 123, ... }
        green: {},    // { customerId: 456, ... }
        blue: {},     // { orderId: 789, ... }
        yellow: {},
        purple: {}
    },

    // Subscribers per link color
    subscribers: new Map(),

    // Emit change to all subscribers on a link
    emit(color, payload) {
        const { source, type, data } = payload;

        // Update link context
        this.links[color] = { ...this.links[color], ...data };

        // Notify all subscribers (except source)
        const subs = this.subscribers.get(color) || [];
        subs.forEach(module => {
            if (module.moduleId !== source) {
                module.onLinkChange(this.links[color]);
            }
        });

        // Persist to URL/localStorage (optional)
        this.persistState();
    },

    // Subscribe module to link
    subscribe(color, module) {
        if (!this.subscribers.has(color)) {
            this.subscribers.set(color, []);
        }
        this.subscribers.get(color).push(module);

        // Send current context to new subscriber
        module.onLinkChange(this.links[color]);
    },

    // Unsubscribe module
    unsubscribe(color, module) {
        const subs = this.subscribers.get(color) || [];
        const index = subs.findIndex(m => m.moduleId === module.moduleId);
        if (index > -1) {
            subs.splice(index, 1);
        }
    },

    // Get current context for a link
    getContext(color) {
        return this.links[color] || {};
    },

    // Persist state to URL/localStorage
    persistState() {
        const state = {};
        Object.keys(this.links).forEach(color => {
            if (Object.keys(this.links[color]).length > 0) {
                state[color] = this.links[color];
            }
        });
        localStorage.setItem('gestima_link_state', JSON.stringify(state));
    },

    // Restore state from URL/localStorage
    restoreState() {
        try {
            const saved = localStorage.getItem('gestima_link_state');
            if (saved) {
                this.links = { ...this.links, ...JSON.parse(saved) };
            }
        } catch (e) {
            console.warn('Failed to restore link state', e);
        }
    }
};
```

### 4. Module Registry (Dostupné typy modulů)

```javascript
// app/static/js/core/module-registry.js

const ModuleRegistry = {
    // Registered module types
    types: {},

    // Register a module factory
    register(type, factory) {
        this.types[type] = {
            factory: factory,
            meta: {
                name: type,
                icon: this.getIcon(type),
                description: this.getDescription(type)
            }
        };
    },

    // Create module instance
    create(type, config) {
        const registration = this.types[type];
        if (!registration) {
            throw new Error(`Unknown module type: ${type}`);
        }
        return registration.factory(config);
    },

    // List available modules (for "Add module" UI)
    listAvailable() {
        return Object.values(this.types).map(t => t.meta);
    },

    // Icons per module type
    getIcon(type) {
        const icons = {
            'parts': '📋',
            'batch-sets': '💰',
            'operations': '🔧',
            'features': '✨',
            'quotes': '📄',
            'customers': '👥',
            'orders': '📦',
            'work-orders': '🏭'
        };
        return icons[type] || '📁';
    },

    getDescription(type) {
        const descriptions = {
            'parts': 'Seznam dílů',
            'batch-sets': 'Sady cen (cenové nabídky)',
            'operations': 'Operace dílu',
            'features': 'Kroky operací',
            'quotes': 'Nabídky pro zákazníky',
            'customers': 'Zákazníci',
            'orders': 'Objednávky',
            'work-orders': 'Výrobní příkazy'
        };
        return descriptions[type] || type;
    }
};
```

### 5. Workspace Controller (Layout management)

```javascript
// app/static/js/core/workspace-controller.js

function workspaceController() {
    return {
        // Layout state
        panels: [],  // Array of panel configs
        activeWorkspace: null,

        // Initialize workspace
        init() {
            LinkManager.restoreState();
            this.loadLayout();
        },

        // Add new panel/module
        addPanel(moduleType, linkColor = null, position = {}) {
            const moduleId = `${moduleType}-${Date.now()}`;

            const panel = {
                id: moduleId,
                moduleType: moduleType,
                linkColor: linkColor,
                position: {
                    x: position.x || 0,
                    y: position.y || 0,
                    width: position.width || 400,
                    height: position.height || 300
                }
            };

            this.panels.push(panel);
            this.saveLayout();
            return panel;
        },

        // Remove panel
        removePanel(panelId) {
            const index = this.panels.findIndex(p => p.id === panelId);
            if (index > -1) {
                // Cleanup module
                const panel = this.panels[index];
                // Module.destroy() called by Alpine x-if removal

                this.panels.splice(index, 1);
                this.saveLayout();
            }
        },

        // Update panel position/size
        updatePanel(panelId, updates) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                Object.assign(panel.position, updates);
                this.saveLayout();
            }
        },

        // Change panel's link color
        changePanelLink(panelId, newColor) {
            const panel = this.panels.find(p => p.id === panelId);
            if (panel) {
                panel.linkColor = newColor;
                this.saveLayout();
                // Module will re-subscribe on next render
            }
        },

        // Save layout to localStorage
        saveLayout() {
            const layout = {
                panels: this.panels,
                timestamp: Date.now()
            };
            localStorage.setItem('gestima_workspace_layout', JSON.stringify(layout));
        },

        // Load layout from localStorage
        loadLayout() {
            try {
                const saved = localStorage.getItem('gestima_workspace_layout');
                if (saved) {
                    const layout = JSON.parse(saved);
                    this.panels = layout.panels || [];
                }
            } catch (e) {
                console.warn('Failed to load workspace layout', e);
                this.panels = [];
            }
        },

        // Reset to default layout
        resetLayout() {
            this.panels = [];
            localStorage.removeItem('gestima_workspace_layout');
        }
    };
}
```

### 6. Multi-Window Support (BroadcastChannel API)

Pro synchronizaci mezi více okny prohlížeče:

```javascript
// app/static/js/core/multi-window-sync.js

const MultiWindowSync = {
    channel: null,
    enabled: false,

    init() {
        if ('BroadcastChannel' in window) {
            this.channel = new BroadcastChannel('gestima-workspace');
            this.enabled = true;

            this.channel.onmessage = (event) => {
                this.handleMessage(event.data);
            };
        }
    },

    // Broadcast link change to other windows
    broadcast(type, payload) {
        if (this.enabled && this.channel) {
            this.channel.postMessage({
                type: type,
                payload: payload,
                source: window.name || 'main',
                timestamp: Date.now()
            });
        }
    },

    // Handle message from other window
    handleMessage(message) {
        if (message.source === (window.name || 'main')) {
            return; // Ignore own messages
        }

        switch (message.type) {
            case 'link-change':
                LinkManager.links[message.payload.color] = message.payload.context;
                // Notify local subscribers
                const subs = LinkManager.subscribers.get(message.payload.color) || [];
                subs.forEach(m => m.onLinkChange(message.payload.context));
                break;

            case 'layout-change':
                // Optional: sync layout across windows
                break;
        }
    }
};

// Integrate with LinkManager
const originalEmit = LinkManager.emit.bind(LinkManager);
LinkManager.emit = function(color, payload) {
    originalEmit(color, payload);
    MultiWindowSync.broadcast('link-change', {
        color: color,
        context: this.links[color]
    });
};
```

---

## UI Design

### Workspace Header

```html
<div class="workspace-header">
    <div class="workspace-title">
        <span>🖥️ Workspace: Cenování</span>
    </div>

    <div class="workspace-actions">
        <!-- Add module dropdown -->
        <div x-data="{ open: false }" class="dropdown">
            <button @click="open = !open">+ Přidat modul</button>
            <div x-show="open" @click.away="open = false" class="dropdown-menu">
                <template x-for="mod in ModuleRegistry.listAvailable()">
                    <button @click="addPanel(mod.name); open = false">
                        <span x-text="mod.icon"></span>
                        <span x-text="mod.description"></span>
                    </button>
                </template>
            </div>
        </div>

        <!-- Link color picker -->
        <div class="link-colors">
            <span>Aktivní link:</span>
            <button class="link-dot red" @click="activeLink = 'red'">🔴</button>
            <button class="link-dot green" @click="activeLink = 'green'">🟢</button>
            <button class="link-dot blue" @click="activeLink = 'blue'">🔵</button>
            <button class="link-dot yellow" @click="activeLink = 'yellow'">🟡</button>
        </div>

        <!-- Save/Load layout -->
        <button @click="saveLayout()">💾 Uložit</button>
        <button @click="resetLayout()">🔄 Reset</button>
    </div>
</div>
```

### Panel Component

```html
<template x-for="panel in panels" :key="panel.id">
    <div class="workspace-panel"
         :style="`
             left: ${panel.position.x}px;
             top: ${panel.position.y}px;
             width: ${panel.position.width}px;
             height: ${panel.position.height}px;
         `"
         @mousedown="startDrag(panel, $event)">

        <!-- Panel header -->
        <div class="panel-header">
            <span class="panel-icon" x-text="ModuleRegistry.getIcon(panel.moduleType)"></span>
            <span class="panel-title" x-text="panel.moduleType"></span>

            <!-- Link indicator -->
            <div class="link-indicator"
                 :class="panel.linkColor"
                 @click="openLinkPicker(panel)">
                <span x-show="panel.linkColor" x-text="getLinkEmoji(panel.linkColor)"></span>
                <span x-show="!panel.linkColor">⚪</span>
            </div>

            <!-- Close button -->
            <button class="panel-close" @click="removePanel(panel.id)">✕</button>
        </div>

        <!-- Panel content (module) -->
        <div class="panel-content"
             x-data="ModuleRegistry.create(panel.moduleType, {
                 moduleId: panel.id,
                 linkColor: panel.linkColor
             })"
             x-init="init()">
            <!-- Module-specific template loaded here -->
        </div>

        <!-- Resize handle -->
        <div class="panel-resize-handle"
             @mousedown.stop="startResize(panel, $event)"></div>
    </div>
</template>
```

---

## Migration Path

### Phase 1: TEĎ (v1.5+)

- ✅ Moduly jako Alpine components v existujících stránkách
- ✅ Žádný workspace UI
- ✅ Připraveno na budoucí integraci

```javascript
// V edit.html - jednoduchá integrace
<div x-data="batchSetsModule({ partId: {{ part_id }} })">
    <!-- UI -->
</div>
```

### Phase 2: BRZY (v2.0)

- Přidat LinkManager (centrální store)
- Propojit moduly přes eventy
- Zachovat existující stránky

```javascript
// V edit.html - s linking
<div x-data="{
    linkContext: { partId: {{ part_id }} },
    ...batchSetsModule({ linkColor: 'red' })
}">
    <!-- UI -->
</div>
```

### Phase 3: BUDOUCNOST (v3.0+)

- Plný Workspace UI
- Drag & resize
- Multi-window sync
- Saved layouts

---

## File Structure

```
app/static/js/
├── core/                          # 🆕 Workspace core
│   ├── module-interface.js        # Base interface
│   ├── module-registry.js         # Module registration
│   ├── link-manager.js            # Link communication
│   ├── workspace-controller.js    # Layout management
│   └── multi-window-sync.js       # BroadcastChannel
│
├── modules/                       # 🆕 Module implementations
│   ├── parts.js                   # Parts list module
│   ├── batch-sets.js              # BatchSets module (ADR-022)
│   ├── operations.js              # Operations module
│   ├── features.js                # Features module
│   ├── quotes.js                  # Quotes module (v2.0)
│   ├── customers.js               # Customers module (v2.0)
│   └── ...
│
└── pages/                         # Page-specific scripts
    ├── part-edit.js               # Orchestrates modules in edit.html
    └── workspace.js               # Full workspace page (v3.0)
```

---

## Workspace-Ready Checklist (Pro každý nový modul)

Při vývoji KAŽDÉHO nového modulu MUSÍ vývojář:

```markdown
## Workspace-Ready Checklist

- [ ] Modul implementuje ModuleInterface
- [ ] Modul má unikátní `moduleType` string
- [ ] Modul přijímá `config.linkColor` a `config.moduleId`
- [ ] Modul implementuje `onLinkChange(context)` pro reaktivitu
- [ ] Modul emituje změny přes `emitToLink(eventType, data)`
- [ ] Modul je registrován v ModuleRegistry
- [ ] Modul má samostatný soubor v `app/static/js/modules/`
- [ ] Modul má definovaný icon a description
- [ ] Modul funguje standalone (bez workspace)
- [ ] Modul funguje v linked context (s workspace)
```

---

## Alternativy

### Option A: iframes

```html
<iframe src="/modules/batch-sets?partId=123"></iframe>
```

**Proč NE:**
- ❌ Pomalé (každý iframe = full page load)
- ❌ Složitá komunikace (postMessage)
- ❌ Nelze sdílet state

### Option B: Web Components

**Proč NE (zatím):**
- ❌ Overkill pro Alpine.js stack
- ❌ Složitější debugging
- ✅ Možná v budoucnu (v4.0+)

### Option C: React/Vue migration

**Proč NE:**
- ❌ Massive refaktoring
- ❌ Ztráta investice do Alpine.js
- ✅ Alpine.js je dostatečný pro tento use case

---

## Reference

- **ADR-022:** BatchSet Model (první workspace-ready modul)
- **ADR-013:** LocalStorage UI Preferences (layout persistence pattern)
- **VISION.md:** Modular architecture, future modules

---

## Implementation Notes

### Large Dataset Handling (2026-01-28)

Pro moduly s 1000+ položkami použít **"Instant First, Complete Later"** pattern:

```javascript
async loadItems() {
    // 1. OKAMŽITĚ: Prvních 50 pro viewport (žádný spinner!)
    const first = await fetch('/api/items?limit=50');
    this.items = first.data;
    this.totalCount = first.total;

    // 2. NA POZADÍ: Zbytek v dávkách
    if (this.totalCount > 50) {
        this.loadRemainingInBackground();
    }
}

async loadRemainingInBackground() {
    let offset = 50;
    while (offset < this.totalCount) {
        await new Promise(resolve => {
            requestIdleCallback(async () => {
                const batch = await fetch(`/api/items?limit=500&offset=${offset}`);
                this.items = [...this.items, ...batch.data];
                resolve();
            });
        });
        offset += 500;
    }
}
```

**Klíčové principy:**
- User NIKDY nevidí spinner (data okamžitě)
- Scrollbar se plynule prodlužuje jak data přibývají
- `requestIdleCallback` = načítá jen když prohlížeč nic nedělá
- Virtualizace (jen 30-50 řádků v DOM) pro plynulý scroll

### Migration Effort Estimate (2026-01-28)

| Fáze | Effort | Popis |
|------|--------|-------|
| Phase 1: Foundation | 3-4 sprinty | LinkManager, Registry, ModuleInterface |
| Phase 2: Extraction | 2-3 sprinty | Moduly do separátních souborů |
| Phase 3: Workspace UI | 4-5 sprintů | Drag/resize, layouts, multi-window |
| **TOTAL** | **9-12 sprintů** | Full workspace implementation |

---

## Changelog

- 2026-01-28: Added implementation notes (batch loading, effort estimate)
- 2026-01-28: Initial design - Workspace Module Architecture
