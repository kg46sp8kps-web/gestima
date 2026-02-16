# GESTIMA - Current Status

**Last Updated:** 2026-02-16
**Version:** 2.0.0
**Status:** UI Design System v4.0 Refactoring COMPLETE

---

## UI Design System v4.0 Refactoring (2026-02-16)

Complete UI overhaul to "Minimal Dark" design — black + red + gray only, ghost buttons, monochrome badges.

### Scope

- **design-system.css** — single source of truth for all tokens (colors, spacing, typography, components)
- **CSS consolidation** — 10 CSS files → 5 (deleted forms.css, components.css, variables.css, theme.css, gestima.css)
- **Font sizes** — +2px from original (min 13px `--text-xs`, 11px `--text-2xs` for special cases)
- **Google Fonts** — Space Grotesk (UI) + Space Mono (numbers/codes) added
- **Ghost buttons** — ALL buttons transparent bg + border, brand/danger accent on hover only
- **Icon standardization** — ICON_SIZE tokens (SMALL=14, STANDARD=18, LARGE=22, XLARGE=32, HERO=48)
- **Semantic icon aliases** — MaterialIcon, OperationsIcon, PricingIcon, DrawingIcon in `@/config/icons`
- **Deprecated tokens removed** — `--accent-*` (were mapping to BLUE!) → replaced with `--brand`
- **40+ Vue files** updated, 200+ hardcoded values replaced with DS tokens
- **8 backup files** cleaned up

### Key Design Decisions

| Decision | Choice |
|----------|--------|
| Button style | Ghost only (transparent + border) |
| Focus ring | WHITE `rgba(255,255,255,0.5)` — NOT blue |
| Badges | Monochrome gray with colored DOT — NOT colored backgrounds |
| Icon buttons | 32x32px, default gray, hover white. Only brand + danger accents |
| Form labels | UPPERCASE, `text-xs`, `letter-spacing: 0.06em`, `text-muted` |
| Spacing | Kept existing values (4pt grid, compact for 27" @ 2560x1440) |

---

## Infor Routing Import — Standard Routes (2026-02-16)

Bulk import of Operations from Infor SLJobRoutes (standard routing only, `Type = 'S'`).

### What It Does

- Imports Operations from Infor SLJobRoutes IDO → `operations` table (UPSERT by part_id + seq)
- Groups rows by `DerJobItem` → resolves Part from DB → creates/updates Operations
- WC Mapper: exact match + prefix fallback (e.g., `KOO1` → `KOO` → KOOPERACE WC)
- 19 WC mappings: PS/PSa/PSm/PSv → SAW, SH2/SH2A/SM1/SM3 → Lathes, FV*/FH* → Mills, KOO → KOOPERACE
- Skip rules: CLO*, CADCAM, ObsDate rows excluded from import
- Kooperace: KOO* → `is_coop=True`, `type="coop"`, `operation_time=0`, `manning=100%`

### Performance (210k+ rows)

| Optimization | Detail |
|-------------|--------|
| Batch DB queries | 3 IN queries (Parts, Operations, WC warmup) instead of 210k per-row |
| Batched API calls | Preview: 5000/batch, Execute: 2000/batch + `postWithRetry()` on 429 |
| Virtual scroll | Only ~60 `<tr>` rendered, Set-based selection for O(1) checks |
| Memory | `infor_data = {}` stripped after staging |

### Time Calculations

| Field | Formula | Example |
|-------|---------|---------|
| `operation_time_min` | `60 / DerRunMchHrs` | 60 ks/hod → 1 min/ks |
| `manning_coefficient` | `(DerRunMchHrs / DerRunLbrHrs) × 100` | stroj 100, obsluha 303 → 33% |
| `setup_time_min` | `JshSetupHrs × 60` (fallback: JshSchedHrs) | 0.75h → 45 min |

### Next Steps

- [ ] Import from VP (výrobní příkazy) — different filter, different logic
- [ ] Production records import (actual times from completed jobs)

---

## ADR-044 Phase 2a: FileManager ↔ TimeVision (v1.32.1 - 2026-02-15)

Centralized FileManager (Phase 1) integrated with TimeVision. PDF files now tracked via `file_id` FK instead of string-based `pdf_filename`.

### What It Does

- `TimeVisionEstimation.file_id` FK → `file_records.id` (nullable, SET NULL on delete)
- UPSERT: file_id match preferred over filename match for estimation lookup
- 68 FileRecords created, 79 estimations linked, 73 active FileLinks (max 2 per file)
- Backward compatible: old `pdf_filename`/`pdf_path` columns stay, filename-only requests work

### Preview vs Download

| Endpoint | Auth | Use Case |
|----------|------|----------|
| `GET /api/files/{id}/preview` | **No** (iframe/pdf.js can't send Bearer) | FileManager PDF preview |
| `GET /api/files/{id}/download` | **Yes** | Explicit download action |
| `GET /api/time-vision/drawings/{filename}/pdf` | **No** | TimeVision pdf.js canvas |

---

## Technology Builder Phase 1 (v1.32.0 - 2026-02-15)

Deterministic post-processing layer around AI Vision. Generates complete manufacturing technology plan (3 operations) after AI estimation.

### Architecture

3-layer design (only Layer 2 implemented):
- **Layer 1:** AI Vision (unchanged, OpenAI fine-tuned model)
- **Layer 2:** Technology Builder (new, deterministic) — **Phase 1 DONE**
- **Layer 3:** Series Optimizer (future, batch size / machine selection)

### What It Does

Button "Generovat technologii" creates 3 operations via UPSERT (by seq number):

| OP | Name | Calculation | Source |
|----|------|-------------|--------|
| 10 | Rezani materialu | vyska_rezu_mm / posuv_mm_min | cutting_conditions DB (sawing) |
| 20 | Strojni operace | AI estimated_time_min (unchanged) | TimeVision |
| 100 | Kontrola | setup_time by complexity (10/15/20 min) | deterministic |

### Key Rules

- OP 10 ALWAYS generated (even without material — time=0 + warning)
- No hardcoded fallback coefficients — if not in DB, time=0 + warning
- AI Vision files NOT touched (openai_vision_service, time_vision, prompts)
- User's manual operations (other seq numbers) left untouched by UPSERT

---

_History before v1.32.0 removed in project cleanup 2026-02-16. Available in git history._
