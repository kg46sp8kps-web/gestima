# GESTIMA Frontend - Vue 3 SPA

**Status:** Phase 1 Day 1-2 COMPLETED (2026-01-29)

## Tech Stack

- **Vue 3.4** - Composition API + `<script setup>`
- **TypeScript** - Strict mode
- **Vite 7.3.1** - Build tool + dev server
- **Vue Router 4** - Client-side routing
- **Pinia** - State management
- **Axios** - HTTP client
- **Vee-validate + Zod** - Form validation
- **Vitest** - Unit testing
- **Playwright** - E2E testing

## Quick Start

```bash
# Install dependencies (already done)
npm install

# Run dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test:unit
npm run test:e2e

# Lint & format
npm run lint
npm run format
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client + endpoints
│   ├── types/            # TypeScript types/interfaces
│   ├── stores/           # Pinia stores (auth, ui, parts, etc.)
│   ├── composables/      # Vue composables (reusable logic)
│   ├── components/
│   │   ├── layout/       # AppHeader, AppSidebar, AppFooter
│   │   ├── ui/           # Toast, Spinner, Modal, etc.
│   │   ├── forms/        # Form components + validation
│   │   └── workspace/    # Workspace-specific components
│   ├── views/
│   │   ├── auth/         # Login, Logout
│   │   ├── dashboard/    # Dashboard view
│   │   ├── parts/        # Parts list, detail
│   │   ├── workspace/    # Workspace modules
│   │   ├── pricing/      # Pricing views
│   │   ├── workCenters/  # Work centers
│   │   ├── admin/        # Admin views
│   │   └── settings/     # Settings
│   ├── assets/
│   │   └── css/          # Preserved CSS from Alpine.js version
│   ├── router/           # Vue Router config
│   ├── App.vue           # Root component
│   └── main.ts           # App entry point
├── vite.config.ts        # Vite config (API proxy)
├── tsconfig.json         # TypeScript config
└── package.json          # Dependencies
```

## API Proxy

Vite dev server proxies `/api` requests to FastAPI backend:

```
http://localhost:5173/api/* → http://localhost:8000/api/*
```

**Make sure FastAPI is running on port 8000:**
```bash
cd /Users/lofas/Documents/__App_Claude/Gestima
python gestima.py run
```

## Development Notes

### CSS Files Preserved

7 CSS files copied from Alpine.js version:
- `base.css` - Base styles
- `components.css` - Component styles
- `forms.css` - Form styles
- `gestima.css` - App-specific styles
- `layout.css` - Layout styles
- `operations.css` - Operations styles
- `variables.css` - CSS variables

These will be refactored to Vue-style scoped CSS gradually.

### Next Steps (Phase 1 Day 3-4)

- [ ] Create `src/api/client.ts` - Axios instance with interceptors
- [ ] Create `src/stores/auth.ts` - Authentication store
- [ ] Create `src/stores/ui.ts` - UI state (toasts, loading)
- [ ] Configure router with auth guards
- [ ] Create basic layout components (Header, Sidebar, Footer)
- [ ] Implement login view
- [ ] Review backend `auth_router.py`

See [docs/VUE-MIGRATION.md](../docs/VUE-MIGRATION.md) for full migration guide.

## Environment

- **Node.js:** v20.20.0
- **Package Manager:** npm v10.8.2
- **Dev Server Port:** 5173
- **Backend API Port:** 8000

## Installed Packages

- 419 packages installed
- 0 vulnerabilities
- All dependencies up-to-date

## IDE Setup

**VS Code** (Recommended):
- [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) - Disable Vetur!
- [TypeScript Vue Plugin](https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin)

**Browser DevTools:**
- [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) (Chrome)
- [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/) (Firefox)

---

**Documentation:** [VUE-MIGRATION.md](../docs/VUE-MIGRATION.md)
**Status:** [STATUS.md](../docs/STATUS.md)
**GESTIMA Version:** 1.7.0 → 2.0.0 (in progress)
